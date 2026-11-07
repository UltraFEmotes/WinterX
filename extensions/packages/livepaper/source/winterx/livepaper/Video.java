package winterx.livepaper;

import android.graphics.Bitmap;
import android.graphics.ImageFormat;
import android.media.Image;
import android.media.MediaCodec;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import java.io.File;
import java.nio.ByteBuffer;

/**
 * Plays a video file silently on a loop, into a Bitmap Spring can draw as its wallpaper.
 *
 * MediaCodec decodes into memory (no Surface, so it works with software decoders and on Mac.APK too); each frame is
 * converted from YUV to RGB at wallpaper size, which is all a wallpaper needs, and handed over double-buffered.
 */
final class Video implements Runnable {
    interface Frames { void frame(); boolean wanted(); }

    static final int WIDTH = 360;                            // decoded width; Spring scales it to the screen

    private final File file;
    private final Frames listener;
    private volatile boolean running = true;
    private final Object swap = new Object();
    // Three frames in rotation: the one shown, the one Spring may still be drawing (or uploading to the GPU), and the next.
    private final Bitmap[] ring = new Bitmap[3];
    private int shown = -1;
    private int[] pixels = new int[0];
    private Thread thread;

    Video(File file, Frames listener) { this.file = file; this.listener = listener; }

    void start() { thread = new Thread(this, "livepaper-video"); thread.setPriority(Thread.MIN_PRIORITY + 1); thread.start(); }

    void stop() {
        running = false;
        if (thread != null) thread.interrupt();
    }

    /** The newest frame, or null before the first one. */
    Bitmap frame() { synchronized (swap) { return shown < 0 ? null : ring[shown]; } }

    /** Where compressed frames come from: LivePaper's own MP4 reader, or Android's extractor for other formats. */
    private interface Source extends AutoCloseable {
        MediaFormat format();
        /** Copy the next frame into buffer; its size, or -1 at the end. */
        int read(ByteBuffer buffer) throws java.io.IOException;
        long time();                                         // of the frame just read, in microseconds
        void rewind();
        @Override void close();
    }

    private static final class Mp4Source implements Source {
        private final Mp4 mp4; private int next; private long time;
        Mp4Source(String path) throws java.io.IOException { mp4 = new Mp4(path); }
        @Override public MediaFormat format() {
            MediaFormat f = MediaFormat.createVideoFormat(mp4.mime, mp4.width, mp4.height);
            if (mp4.csd0 != null) f.setByteBuffer("csd-0", ByteBuffer.wrap(mp4.csd0));
            if (mp4.csd1 != null) f.setByteBuffer("csd-1", ByteBuffer.wrap(mp4.csd1));
            return f;
        }
        @Override public int read(ByteBuffer buffer) throws java.io.IOException {
            if (next >= mp4.count()) return -1;
            byte[] frame = mp4.frame(next);
            time = mp4.timesUs[next++];
            buffer.clear(); buffer.put(frame);
            return frame.length;
        }
        @Override public long time() { return time; }
        @Override public void rewind() { next = 0; }
        @Override public void close() { try { mp4.close(); } catch (java.io.IOException ignored) {} }
    }

    private static final class ExtractorSource implements Source {
        private final MediaExtractor extractor = new MediaExtractor(); private MediaFormat format; private long time;
        ExtractorSource(String path) throws java.io.IOException {
            extractor.setDataSource(path);
            for (int i = 0; i < extractor.getTrackCount(); i++) {
                MediaFormat f = extractor.getTrackFormat(i);
                String mime = f.getString(MediaFormat.KEY_MIME);
                if (mime != null && mime.startsWith("video/")) { extractor.selectTrack(i); format = f; return; }
            }
            extractor.release();
            throw new java.io.IOException("No video track");
        }
        @Override public MediaFormat format() { return format; }
        @Override public int read(ByteBuffer buffer) {
            int size = extractor.readSampleData(buffer, 0);
            time = extractor.getSampleTime();
            if (size >= 0) extractor.advance();
            return size;
        }
        @Override public long time() { return time; }
        @Override public void rewind() { extractor.seekTo(0, MediaExtractor.SEEK_TO_CLOSEST_SYNC); }
        @Override public void close() { extractor.release(); }
    }

    private Source open() throws java.io.IOException {
        try { return new Mp4Source(file.getPath()); }
        catch (java.io.IOException notMp4) { return new ExtractorSource(file.getPath()); }
    }

    @Override public void run() {
        Source source = null;
        MediaCodec codec = null;
        try {
            source = open();
            MediaFormat format = source.format();
            format.setInteger(MediaFormat.KEY_COLOR_FORMAT, 0x7F420888);   // COLOR_FormatYUV420Flexible
            codec = MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME));
            codec.configure(format, null, null, 0);
            codec.start();
            play(source, codec);
        } catch (InterruptedException stopped) {
        } catch (Exception failure) {
            android.util.Log.w("LivePaper", "video playback failed", failure);
        } finally {
            if (codec != null) try { codec.stop(); codec.release(); } catch (RuntimeException ignored) {}
            if (source != null) source.close();
        }
    }

    private void play(Source source, MediaCodec codec) throws Exception {
        MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
        boolean inputDone = false;
        long startNanos = System.nanoTime(), firstUs = -1, pausedNanos = 0;
        while (running) {
            if (!listener.wanted()) {                        // nothing is showing the wallpaper: don't decode
                long since = System.nanoTime();
                while (running && !listener.wanted()) Thread.sleep(150);
                pausedNanos += System.nanoTime() - since;
            }
            if (!inputDone) {
                int in = codec.dequeueInputBuffer(10_000);
                if (in >= 0) {
                    ByteBuffer buffer = codec.getInputBuffer(in);
                    int size = source.read(buffer);
                    if (size < 0) { codec.queueInputBuffer(in, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM); inputDone = true; }
                    else codec.queueInputBuffer(in, 0, size, source.time(), 0);
                }
            }
            int out = codec.dequeueOutputBuffer(info, 10_000);
            if (out < 0) continue;
            if ((info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) {
                codec.releaseOutputBuffer(out, false);
                source.rewind();                                // loop
                codec.flush(); inputDone = false;
                startNanos = System.nanoTime(); firstUs = -1; pausedNanos = 0;
                continue;
            }
            // Keep to the video's own timing.
            if (firstUs < 0) firstUs = info.presentationTimeUs;
            long due = startNanos + pausedNanos + (info.presentationTimeUs - firstUs) * 1000;
            long wait = (due - System.nanoTime()) / 1_000_000;
            if (wait > 0) Thread.sleep(Math.min(wait, 250));
            Image image = codec.getOutputImage(out);
            if (image != null) {
                try { convert(image); } finally { image.close(); }
                listener.frame();
            }
            codec.releaseOutputBuffer(out, false);
        }
    }

    /** YUV 4:2:0 to ARGB at WIDTH pixels wide, sampled nearest-neighbour, then swapped in as the new front frame. */
    private void convert(Image image) {
        android.graphics.Rect crop = image.getCropRect();
        if (image.getPlanes().length == 1) { packed(image, crop); return; }
        if (image.getFormat() != ImageFormat.YUV_420_888) return;
        int srcW = crop.width(), srcH = crop.height();
        int w = Math.min(WIDTH, srcW), h = Math.max(1, Math.round(srcH * (w / (float)srcW)));
        if (pixels.length != w * h) pixels = new int[w * h];
        Image.Plane[] planes = image.getPlanes();
        ByteBuffer y = planes[0].getBuffer(), u = planes[1].getBuffer(), v = planes[2].getBuffer();
        int yRow = planes[0].getRowStride(), yPix = planes[0].getPixelStride();
        int uRow = planes[1].getRowStride(), uPix = planes[1].getPixelStride();
        int vRow = planes[2].getRowStride(), vPix = planes[2].getPixelStride();
        for (int row = 0; row < h; row++) {
            int sy = crop.top + row * srcH / h;
            for (int col = 0; col < w; col++) {
                int sx = crop.left + col * srcW / w;
                int Y = (y.get(sy * yRow + sx * yPix) & 255) - 16;
                int U = (u.get((sy / 2) * uRow + (sx / 2) * uPix) & 255) - 128;
                int V = (v.get((sy / 2) * vRow + (sx / 2) * vPix) & 255) - 128;
                int c = 1192 * Math.max(0, Y);
                int r = clamp((c + 1634 * V) >> 10), g = clamp((c - 833 * V - 400 * U) >> 10), b = clamp((c + 2066 * U) >> 10);
                pixels[row * w + col] = 0xFF000000 | r << 16 | g << 8 | b;
            }
        }
        publish(w, h);
    }

    private void publish(int w, int h) {
        int next = (shown + 1) % ring.length;
        if (ring[next] == null || ring[next].getWidth() != w || ring[next].getHeight() != h) ring[next] = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        ring[next].setPixels(pixels, 0, w, 0, 0, w, h);
        synchronized (swap) { shown = next; }
    }

    /** A frame that's already RGBA or BGRA (one plane of 4-byte pixels), as Mac.APK's decoder gives. */
    private static int formatLogged;
    private void packed(Image image, android.graphics.Rect crop) {
        Image.Plane plane = image.getPlanes()[0];
        if (plane.getPixelStride() != 4) return;
        boolean bgra = image.getFormat() != 1;                // 1 = PixelFormat.RGBA_8888; anything else here is BGRA
        if (formatLogged++ == 0) android.util.Log.i("LivePaper", "decoder frames: format " + image.getFormat() + " " + crop.width() + "x" + crop.height());
        ByteBuffer data = plane.getBuffer(); int rowStride = plane.getRowStride();
        int srcW = crop.width(), srcH = crop.height();
        int w = Math.min(WIDTH, srcW), h = Math.max(1, Math.round(srcH * (w / (float)srcW)));
        if (pixels.length != w * h) pixels = new int[w * h];
        for (int row = 0; row < h; row++) {
            int sy = crop.top + row * srcH / h;
            for (int col = 0; col < w; col++) {
                int i = sy * rowStride + (crop.left + col * srcW / w) * 4;
                int a = data.get(i) & 255, b = data.get(i + 1) & 255, c = data.get(i + 2) & 255;
                pixels[row * w + col] = bgra ? 0xFF000000 | c << 16 | b << 8 | a : 0xFF000000 | a << 16 | b << 8 | c;
            }
        }
        publish(w, h);
    }

    private static int clamp(int value) { return value < 0 ? 0 : value > 255 ? 255 : value; }
}

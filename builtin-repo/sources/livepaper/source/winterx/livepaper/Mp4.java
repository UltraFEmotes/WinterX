package winterx.livepaper;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;

/**
 * Reads the video track of an MP4 / MOV file: where each frame is, how big, when it's shown, and the codec setup.
 *
 * Mac.APK's MediaExtractor only exposes audio tracks, but its MediaCodec decodes H.264 and HEVC. This small reader
 * fills the gap (and is used everywhere, so playback works the same on phones). Frames are returned in Annex B form
 * (00 00 00 01 start codes), the way MediaExtractor hands them to MediaCodec.
 */
final class Mp4 implements AutoCloseable {
    String mime;                                             // video/avc or video/hevc
    int width, height;
    byte[] csd0, csd1;                                       // codec setup: SPS / PPS (H.264), VPS+SPS+PPS (HEVC)
    long[] offsets; int[] sizes; long[] timesUs; boolean[] sync;
    private int lengthSize = 4;                              // bytes in each NAL length prefix
    private final RandomAccessFile file;

    Mp4(String path) throws IOException {
        file = new RandomAccessFile(path, "r");
        try { parse(0, file.length(), 0); } catch (RuntimeException broken) { throw new IOException("Unreadable MP4", broken); }
        if (mime == null || offsets == null) { file.close(); throw new IOException("No H.264 or HEVC video track"); }
    }

    int count() { return sizes.length; }

    /** Frame i with start codes instead of length prefixes. */
    byte[] frame(int i) throws IOException {
        byte[] raw = new byte[sizes[i]];
        file.seek(offsets[i]); file.readFully(raw);
        ByteArrayOutputStream out = new ByteArrayOutputStream(raw.length + 16);
        for (int at = 0; at + lengthSize <= raw.length;) {
            int n = 0;
            for (int k = 0; k < lengthSize; k++) n = n << 8 | (raw[at + k] & 255);
            at += lengthSize;
            if (n <= 0 || at + n > raw.length) break;
            out.write(0); out.write(0); out.write(0); out.write(1);
            out.write(raw, at, n);
            at += n;
        }
        return out.toByteArray();
    }

    @Override public void close() throws IOException { file.close(); }

    // ----- boxes -----

    // Per-track state while walking one trak.
    private boolean video; private long timescale;
    private long[] chunkOffsets; private int[] stszSizes; private int[][] stsc; private long[][] stts; private int[] stss;
    private String trackMime; private int trackW, trackH; private byte[] trackCsd0, trackCsd1; private int trackLength = 4;

    private void parse(long start, long end, int depth) throws IOException {
        long at = start;
        while (at + 8 <= end) {
            file.seek(at);
            long size = file.readInt() & 0xFFFFFFFFL;
            String type = fourcc(file.readInt());
            long header = 8;
            if (size == 1) { size = file.readLong(); header = 16; }
            else if (size == 0) size = end - at;
            if (size < header || at + size > end) return;
            long body = at + header, bodyEnd = at + size;
            switch (type) {
                case "moov": case "mdia": case "minf": case "stbl": case "edts":
                    parse(body, bodyEnd, depth + 1); break;
                case "trak":
                    video = false; timescale = 0; chunkOffsets = null; stszSizes = null; stsc = null; stts = null; stss = null;
                    trackMime = null; trackCsd0 = trackCsd1 = null;
                    parse(body, bodyEnd, depth + 1);
                    if (video && mime == null && trackMime != null && stszSizes != null && chunkOffsets != null && stsc != null && stts != null && timescale > 0) build();
                    break;
                case "hdlr": file.seek(body + 8); video = "vide".equals(fourcc(file.readInt())); break;
                case "mdhd": {
                    file.seek(body); int version = file.readUnsignedByte(); file.skipBytes(3);
                    if (version == 1) { file.skipBytes(16); timescale = file.readInt() & 0xFFFFFFFFL; }
                    else { file.skipBytes(8); timescale = file.readInt() & 0xFFFFFFFFL; }
                    break;
                }
                case "stsd": file.seek(body + 8); parseSampleEntry(body + 8, bodyEnd); break;
                case "stco": { file.seek(body + 4); int n = file.readInt(); chunkOffsets = new long[n]; for (int i = 0; i < n; i++) chunkOffsets[i] = file.readInt() & 0xFFFFFFFFL; break; }
                case "co64": { file.seek(body + 4); int n = file.readInt(); chunkOffsets = new long[n]; for (int i = 0; i < n; i++) chunkOffsets[i] = file.readLong(); break; }
                case "stsz": {
                    file.seek(body + 4); int fixed = file.readInt(), n = file.readInt(); stszSizes = new int[n];
                    for (int i = 0; i < n; i++) stszSizes[i] = fixed != 0 ? fixed : file.readInt();
                    break;
                }
                case "stsc": { file.seek(body + 4); int n = file.readInt(); stsc = new int[n][3]; for (int i = 0; i < n; i++) { stsc[i][0] = file.readInt(); stsc[i][1] = file.readInt(); stsc[i][2] = file.readInt(); } break; }
                case "stts": { file.seek(body + 4); int n = file.readInt(); stts = new long[n][2]; for (int i = 0; i < n; i++) { stts[i][0] = file.readInt() & 0xFFFFFFFFL; stts[i][1] = file.readInt() & 0xFFFFFFFFL; } break; }
                case "stss": { file.seek(body + 4); int n = file.readInt(); stss = new int[n]; for (int i = 0; i < n; i++) stss[i] = file.readInt(); break; }
                default:
            }
            at += size;
        }
    }

    /** avc1 / hvc1 / hev1: dimensions and the codec configuration box. */
    private void parseSampleEntry(long at, long end) throws IOException {
        file.seek(at);
        long size = file.readInt() & 0xFFFFFFFFL;
        String type = fourcc(file.readInt());
        boolean avc = type.equals("avc1") || type.equals("avc3"), hevc = type.equals("hvc1") || type.equals("hev1");
        if (!avc && !hevc) return;
        file.seek(at + 8 + 24); trackW = file.readUnsignedShort(); trackH = file.readUnsignedShort();
        long child = at + 8 + 78, entryEnd = Math.min(end, at + size);
        while (child + 8 <= entryEnd) {
            file.seek(child);
            long boxSize = file.readInt() & 0xFFFFFFFFL; String box = fourcc(file.readInt());
            if (boxSize < 8) return;
            if (avc && box.equals("avcC")) { readAvcC(child + 8); trackMime = "video/avc"; }
            if (hevc && box.equals("hvcC")) { readHvcC(child + 8); trackMime = "video/hevc"; }
            child += boxSize;
        }
    }

    private void readAvcC(long at) throws IOException {
        file.seek(at + 4);
        trackLength = (file.readUnsignedByte() & 3) + 1;
        ByteArrayOutputStream sps = new ByteArrayOutputStream(), pps = new ByteArrayOutputStream();
        int spsCount = file.readUnsignedByte() & 31;
        for (int i = 0; i < spsCount; i++) nal(sps, file.readUnsignedShort());
        int ppsCount = file.readUnsignedByte();
        for (int i = 0; i < ppsCount; i++) nal(pps, file.readUnsignedShort());
        trackCsd0 = sps.toByteArray(); trackCsd1 = pps.toByteArray();
    }

    private void readHvcC(long at) throws IOException {
        file.seek(at + 21);
        trackLength = (file.readUnsignedByte() & 3) + 1;
        int arrays = file.readUnsignedByte();
        ByteArrayOutputStream all = new ByteArrayOutputStream();
        for (int a = 0; a < arrays; a++) {
            file.readUnsignedByte();                         // NAL type
            int count = file.readUnsignedShort();
            for (int i = 0; i < count; i++) nal(all, file.readUnsignedShort());
        }
        trackCsd0 = all.toByteArray(); trackCsd1 = null;
    }

    private void nal(ByteArrayOutputStream out, int length) throws IOException {
        byte[] unit = new byte[length]; file.readFully(unit);
        out.write(0); out.write(0); out.write(0); out.write(1); out.write(unit);
    }

    /** Sample tables to per-frame offsets, sizes and times. */
    private void build() {
        int n = stszSizes.length;
        long[] off = new long[n]; long[] times = new long[n]; boolean[] key = new boolean[n];
        int sample = 0;
        for (int e = 0; e < stsc.length && sample < n; e++) {
            int firstChunk = stsc[e][0] - 1, perChunk = stsc[e][1];
            int lastChunk = e + 1 < stsc.length ? stsc[e + 1][0] - 1 : chunkOffsets.length;
            for (int c = firstChunk; c < lastChunk && sample < n; c++) {
                long pos = chunkOffsets[c];
                for (int k = 0; k < perChunk && sample < n; k++) { off[sample] = pos; pos += stszSizes[sample]; sample++; }
            }
        }
        long t = 0; int s = 0;
        for (long[] run : stts) for (long r = 0; r < run[0] && s < n; r++) { times[s++] = t * 1_000_000 / timescale; t += run[1]; }
        if (stss == null) java.util.Arrays.fill(key, true);
        else for (int i : stss) if (i - 1 >= 0 && i - 1 < n) key[i - 1] = true;
        mime = trackMime; width = trackW; height = trackH; csd0 = trackCsd0; csd1 = trackCsd1; lengthSize = trackLength;
        offsets = off; sizes = stszSizes; timesUs = times; sync = key;
    }

    private static String fourcc(int v) {
        return new String(new char[]{(char)(v >>> 24 & 255), (char)(v >>> 16 & 255), (char)(v >>> 8 & 255), (char)(v & 255)});
    }
}

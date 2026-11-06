package winterx.legacyboot;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Serves the page and the emulator to the WebView on 127.0.0.1 only. A loopback address counts as a secure origin, so
 * WebAssembly, workers and the firmware cache work, and unlike shouldInterceptRequest it works in every WebView,
 * Mac.APK's included. The port is fixed so the cached firmware stays under the same origin between launches.
 */
final class LocalServer {
    static final int[] PORTS = {48107, 48108, 48109};
    private final Engine engine;
    private final ExecutorService workers = Executors.newFixedThreadPool(4);
    private ServerSocket socket;

    LocalServer(Engine engine) { this.engine = engine; }

    Engine engine() { return engine; }

    /** The page's address, starting the server the first time. */
    synchronized String start() throws java.io.IOException {
        if (socket == null) {
            java.io.IOException last = null;
            for (int port : PORTS) {
                try { socket = new ServerSocket(port, 16, InetAddress.getByName("127.0.0.1")); break; }
                catch (java.io.IOException taken) { last = taken; }
            }
            if (socket == null) throw last;
            ServerSocket server = socket;
            Thread accept = new Thread(() -> {
                while (!server.isClosed()) {
                    try { Socket client = server.accept(); workers.execute(() -> answer(client)); }
                    catch (java.io.IOException closed) { return; }
                }
            }, "legacyboot-server");
            accept.setDaemon(true);
            accept.start();
        }
        return "http://127.0.0.1:" + socket.getLocalPort() + "/";
    }

    synchronized void stop() {
        try { if (socket != null) socket.close(); } catch (java.io.IOException ignored) {}
        socket = null;
    }

    private void answer(Socket client) {
        try (Socket connection = client) {
            connection.setSoTimeout(15000);
            BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream(), StandardCharsets.ISO_8859_1));
            String line = reader.readLine();
            if (line == null) return;
            for (String header; (header = reader.readLine()) != null && !header.isEmpty();) {}
            String[] parts = line.split(" ");
            OutputStream out = connection.getOutputStream();
            if (parts.length < 2 || !parts[0].equals("GET")) { send(out, 405, "text/plain", new byte[0]); return; }
            String path = parts[1];
            int query = path.indexOf('?');
            if (query >= 0) path = path.substring(0, query);
            path = path.startsWith("/") ? path.substring(1) : path;
            Engine.Reply reply = engine.reply(path);
            send(out, reply.status, reply.type, reply.body);
        } catch (Exception dropped) {}
    }

    private static void send(OutputStream out, int status, String type, byte[] body) throws java.io.IOException {
        String head = "HTTP/1.1 " + status + (status == 200 ? " OK" : " Error") + "\r\n"
            + "Content-Type: " + type + "\r\nContent-Length: " + body.length + "\r\n"
            + "Cache-Control: no-cache\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n";
        out.write(head.getBytes(StandardCharsets.ISO_8859_1));
        out.write(body);
        out.flush();
    }
}

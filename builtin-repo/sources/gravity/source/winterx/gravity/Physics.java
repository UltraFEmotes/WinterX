package winterx.gravity;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * A small rigid-body box world: a Java port of Box2D-Lite by Erin Catto (zlib licence, box2d.org): oriented box
 * collision with edge clipping, sequential impulses with friction, and warm starting so stacks settle.
 * Units are icon widths; y points down like the screen.
 */
final class Physics {
    static final float ALLOWED_PENETRATION = 0.01f, BIAS = 0.2f, FRICTION = 0.6f;

    static final class Box {
        float x, y, angle, vx, vy, w;              // centre, rotation (radians), velocity, angular velocity
        final float hx, hy, invMass, invI;
        Box(float x, float y, float width, float height, float mass) {
            this.x = x; this.y = y; hx = width / 2; hy = height / 2;
            invMass = mass > 0 ? 1 / mass : 0;
            invI = mass > 0 ? 12 / (mass * (width * width + height * height)) : 0;
        }
        boolean contains(float px, float py) {
            float c = (float)Math.cos(angle), s = (float)Math.sin(angle), dx = px - x, dy = py - y;
            float lx = c * dx + s * dy, ly = -s * dx + c * dy;
            return Math.abs(lx) <= hx && Math.abs(ly) <= hy;
        }
    }

    static final class Contact {
        float px, py, nx, ny, separation, pn, pt, massNormal, massTangent, bias;
    }

    /** Persistent contact set between two boxes, matched frame to frame for warm starting. */
    static final class Arbiter {
        final Box a, b; Contact[] contacts = new Contact[0];
        Arbiter(Box a, Box b) { this.a = a; this.b = b; }
        void update(Contact[] fresh) {
            for (Contact c : fresh) for (Contact old : contacts)
                if (Math.abs(c.px - old.px) + Math.abs(c.py - old.py) < 0.1f) { c.pn = old.pn; c.pt = old.pt; break; }
            contacts = fresh;
        }
    }

    final List<Box> boxes = new ArrayList<>();
    private final Map<Long, Arbiter> arbiters = new HashMap<>();
    float gx = 0, gy = 30;
    int iterations = 12;

    Box add(Box box) { boxes.add(box); return box; }

    void step(float dt) {
        if (dt <= 0) return;
        float invDt = 1 / dt;
        // Broad phase: every dynamic pair (a few dozen icons) and every icon against the walls.
        for (int i = 0; i < boxes.size(); i++) for (int j = i + 1; j < boxes.size(); j++) {
            Box a = boxes.get(i), b = boxes.get(j);
            if (a.invMass == 0 && b.invMass == 0) continue;
            long key = ((long)i << 32) | j;
            Contact[] found = collide(a, b);
            if (found.length > 0) {
                Arbiter arbiter = arbiters.get(key);
                if (arbiter == null) { arbiter = new Arbiter(a, b); arbiters.put(key, arbiter); }
                arbiter.update(found);
            } else arbiters.remove(key);
        }
        for (Box box : boxes) {
            if (box.invMass == 0) continue;
            box.vx += dt * gx; box.vy += dt * gy;
            box.vx *= 0.999f; box.vy *= 0.999f; box.w *= 0.995f;
        }
        for (Arbiter arbiter : arbiters.values()) preStep(arbiter, invDt);
        for (int i = 0; i < iterations; i++) for (Arbiter arbiter : arbiters.values()) applyImpulse(arbiter);
        for (Box box : boxes) {
            box.x += dt * box.vx; box.y += dt * box.vy; box.angle += dt * box.w;
        }
    }

    // ----- solver (Box2D-Lite Arbiter::PreStep / ApplyImpulse) -----

    private static void preStep(Arbiter arbiter, float invDt) {
        Box a = arbiter.a, b = arbiter.b;
        for (Contact c : arbiter.contacts) {
            float r1x = c.px - a.x, r1y = c.py - a.y, r2x = c.px - b.x, r2y = c.py - b.y;
            float rn1 = r1x * c.nx + r1y * c.ny, rn2 = r2x * c.nx + r2y * c.ny;
            float kNormal = a.invMass + b.invMass + a.invI * (r1x * r1x + r1y * r1y - rn1 * rn1) + b.invI * (r2x * r2x + r2y * r2y - rn2 * rn2);
            c.massNormal = 1 / kNormal;
            float tx = c.ny, ty = -c.nx;
            float rt1 = r1x * tx + r1y * ty, rt2 = r2x * tx + r2y * ty;
            float kTangent = a.invMass + b.invMass + a.invI * (r1x * r1x + r1y * r1y - rt1 * rt1) + b.invI * (r2x * r2x + r2y * r2y - rt2 * rt2);
            c.massTangent = 1 / kTangent;
            c.bias = -BIAS * invDt * Math.min(0, c.separation + ALLOWED_PENETRATION);
            float px = c.pn * c.nx + c.pt * tx, py = c.pn * c.ny + c.pt * ty;    // warm start
            a.vx -= a.invMass * px; a.vy -= a.invMass * py; a.w -= a.invI * (r1x * py - r1y * px);
            b.vx += b.invMass * px; b.vy += b.invMass * py; b.w += b.invI * (r2x * py - r2y * px);
        }
    }

    private static void applyImpulse(Arbiter arbiter) {
        Box a = arbiter.a, b = arbiter.b;
        for (Contact c : arbiter.contacts) {
            float r1x = c.px - a.x, r1y = c.py - a.y, r2x = c.px - b.x, r2y = c.py - b.y;
            float dvx = b.vx - b.w * r2y - a.vx + a.w * r1y, dvy = b.vy + b.w * r2x - a.vy - a.w * r1x;
            float vn = dvx * c.nx + dvy * c.ny;
            float dPn = c.massNormal * (-vn + c.bias), old = c.pn;
            c.pn = Math.max(old + dPn, 0); dPn = c.pn - old;
            float px = dPn * c.nx, py = dPn * c.ny;
            a.vx -= a.invMass * px; a.vy -= a.invMass * py; a.w -= a.invI * (r1x * py - r1y * px);
            b.vx += b.invMass * px; b.vy += b.invMass * py; b.w += b.invI * (r2x * py - r2y * px);
            dvx = b.vx - b.w * r2y - a.vx + a.w * r1y; dvy = b.vy + b.w * r2x - a.vy - a.w * r1x;
            float tx = c.ny, ty = -c.nx, vt = dvx * tx + dvy * ty;
            float dPt = c.massTangent * -vt, maxPt = FRICTION * c.pn, oldT = c.pt;
            c.pt = Math.max(-maxPt, Math.min(oldT + dPt, maxPt)); dPt = c.pt - oldT;
            px = dPt * tx; py = dPt * ty;
            a.vx -= a.invMass * px; a.vy -= a.invMass * py; a.w -= a.invI * (r1x * py - r1y * px);
            b.vx += b.invMass * px; b.vy += b.invMass * py; b.w += b.invI * (r2x * py - r2y * px);
        }
    }

    // ----- collision (Box2D-Lite Collide.cpp) -----

    private static float[] rot(Box box) { float c = (float)Math.cos(box.angle), s = (float)Math.sin(box.angle); return new float[]{c, s}; }

    /** Contacts between two oriented boxes; normals point from a to b. */
    static Contact[] collide(Box a, Box b) {
        float[] ra = rot(a), rb = rot(b);
        float ca = ra[0], sa = ra[1], cb = rb[0], sb = rb[1];
        // Columns of the rotation matrices: col1 = (c, s), col2 = (-s, c).
        float dpx = b.x - a.x, dpy = b.y - a.y;
        float dAx = ca * dpx + sa * dpy, dAy = -sa * dpx + ca * dpy;                 // RotA^T * dp
        float dBx = cb * dpx + sb * dpy, dBy = -sb * dpx + cb * dpy;                 // RotB^T * dp
        // C = RotA^T * RotB
        float c11 = ca * cb + sa * sb, c12 = -ca * sb + sa * cb, c21 = -sa * cb + ca * sb, c22 = sa * sb + ca * cb;
        float a11 = Math.abs(c11), a12 = Math.abs(c12), a21 = Math.abs(c21), a22 = Math.abs(c22);
        float faceAx = Math.abs(dAx) - a.hx - (a11 * b.hx + a12 * b.hy), faceAy = Math.abs(dAy) - a.hy - (a21 * b.hx + a22 * b.hy);
        if (faceAx > 0 || faceAy > 0) return new Contact[0];
        float faceBx = Math.abs(dBx) - (a11 * a.hx + a21 * a.hy) - b.hx, faceBy = Math.abs(dBy) - (a12 * a.hx + a22 * a.hy) - b.hy;
        if (faceBx > 0 || faceBy > 0) return new Contact[0];
        int axis = 0; float separation = faceAx;
        float nx = dAx > 0 ? ca : -ca, ny = dAx > 0 ? sa : -sa;
        final float relative = 0.95f, absolute = 0.01f;
        if (faceAy > relative * separation + absolute * a.hy) { axis = 1; separation = faceAy; nx = dAy > 0 ? -sa : sa; ny = dAy > 0 ? ca : -ca; }
        if (faceBx > relative * separation + absolute * b.hx) { axis = 2; separation = faceBx; nx = dBx > 0 ? cb : -cb; ny = dBx > 0 ? sb : -sb; }
        if (faceBy > relative * separation + absolute * b.hy) { axis = 3; separation = faceBy; nx = dBy > 0 ? -sb : sb; ny = dBy > 0 ? cb : -cb; }
        float fnx, fny, front, snx, sny, negSide, posSide;
        float[][] incident;
        switch (axis) {
            case 0: { fnx = nx; fny = ny; front = a.x * fnx + a.y * fny + a.hx; snx = -sa; sny = ca;
                      float side = a.x * snx + a.y * sny; negSide = -side + a.hy; posSide = side + a.hy;
                      incident = incidentEdge(b, cb, sb, fnx, fny); break; }
            case 1: { fnx = nx; fny = ny; front = a.x * fnx + a.y * fny + a.hy; snx = ca; sny = sa;
                      float side = a.x * snx + a.y * sny; negSide = -side + a.hx; posSide = side + a.hx;
                      incident = incidentEdge(b, cb, sb, fnx, fny); break; }
            case 2: { fnx = -nx; fny = -ny; front = b.x * fnx + b.y * fny + b.hx; snx = -sb; sny = cb;
                      float side = b.x * snx + b.y * sny; negSide = -side + b.hy; posSide = side + b.hy;
                      incident = incidentEdge(a, ca, sa, fnx, fny); break; }
            default: { fnx = -nx; fny = -ny; front = b.x * fnx + b.y * fny + b.hy; snx = cb; sny = sb;
                      float side = b.x * snx + b.y * sny; negSide = -side + b.hx; posSide = side + b.hx;
                      incident = incidentEdge(a, ca, sa, fnx, fny); break; }
        }
        float[][] clip1 = clip(incident, -snx, -sny, negSide);
        if (clip1 == null) return new Contact[0];
        float[][] clip2 = clip(clip1, snx, sny, posSide);
        if (clip2 == null) return new Contact[0];
        List<Contact> contacts = new ArrayList<>(2);
        for (float[] point : clip2) {
            float sep = fnx * point[0] + fny * point[1] - front;
            if (sep > 0) continue;
            Contact c = new Contact();
            c.separation = sep; c.nx = nx; c.ny = ny;
            c.px = point[0] - sep * fnx; c.py = point[1] - sep * fny;               // slide onto the reference face
            contacts.add(c);
        }
        return contacts.toArray(new Contact[0]);
    }

    /** The edge of the incident box most anti-parallel to the reference normal, in world space. */
    private static float[][] incidentEdge(Box box, float c, float s, float nx, float ny) {
        float lx = -(c * nx + s * ny), ly = -(-s * nx + c * ny);                     // -(Rot^T * normal)
        float[][] v;
        if (Math.abs(lx) > Math.abs(ly)) v = lx > 0 ? new float[][]{{box.hx, -box.hy}, {box.hx, box.hy}} : new float[][]{{-box.hx, box.hy}, {-box.hx, -box.hy}};
        else v = ly > 0 ? new float[][]{{box.hx, box.hy}, {-box.hx, box.hy}} : new float[][]{{-box.hx, -box.hy}, {box.hx, -box.hy}};
        for (float[] p : v) { float x = p[0], y = p[1]; p[0] = box.x + c * x - s * y; p[1] = box.y + s * x + c * y; }
        return v;
    }

    /** Keep the part of a segment on the inside of a plane (normal · p ≤ offset); null if less than two points remain. */
    private static float[][] clip(float[][] in, float nx, float ny, float offset) {
        float d0 = nx * in[0][0] + ny * in[0][1] - offset, d1 = nx * in[1][0] + ny * in[1][1] - offset;
        List<float[]> out = new ArrayList<>(2);
        if (d0 <= 0) out.add(in[0]);
        if (d1 <= 0) out.add(in[1]);
        if (d0 * d1 < 0) {
            float t = d0 / (d0 - d1);
            out.add(new float[]{in[0][0] + t * (in[1][0] - in[0][0]), in[0][1] + t * (in[1][1] - in[0][1])});
        }
        return out.size() < 2 ? null : out.toArray(new float[0][]);
    }
}

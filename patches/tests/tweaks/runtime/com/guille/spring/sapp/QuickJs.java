package com.guille.spring.sapp;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** JVM lifecycle spy, NOT a substitute for live JNI/QuickJS execution tests. */
public final class QuickJs implements AutoCloseable {
    public interface Host { Object call(int operation, Object[] args); }
    public static final List<QuickJs> CREATED = Collections.synchronizedList(new ArrayList<QuickJs>());
    public final String owner = Thread.currentThread().getName();
    public final Host host;
    public volatile boolean closed, ranJobs;
    public volatile String filename;
    public volatile String event;
    private long deadline;
    public static QuickJs winterxCreate(ArrayList names, C0.a host) { return new QuickJs(host); }
    private QuickJs(Host host) { this.host = host; CREATED.add(this); }
    private void thread() {
        if (!owner.equals(Thread.currentThread().getName())) throw new AssertionError("QuickJS crossed threads");
    }
    public void t(long ms) { thread(); deadline = ms; }
    public void u(String script, String name) {
        thread();
        if (deadline <= 0) throw new AssertionError("Evaluation lacks deadline");
        if (name.equals("winterx-bootstrap.js")) return;
        filename = name;
        if (script.contains("TEST_THROW")) throw new IllegalArgumentException("simulated JS failure");
        if (script.contains("TEST_STORAGE")) {
            host.call(2, new Object[]{"{\"count\":3}"});
            host.call(4, new Object[]{"example.txt", "private data"});
            if (!"private data".equals(host.call(3, new Object[]{"example.txt"}))) throw new AssertionError("Host data mismatch");
        }
    }
    public void j(String name, Object... args) {
        thread(); if (deadline <= 0) throw new AssertionError("Event lacks deadline"); event = name;
    }
    public void v() { thread(); if (deadline <= 0) throw new AssertionError("Jobs lack deadline"); ranJobs = true; }
    public void close() { thread(); closed = true; }
}

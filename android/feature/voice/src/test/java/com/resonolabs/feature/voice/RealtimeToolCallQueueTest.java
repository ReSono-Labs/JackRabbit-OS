package com.resonolabs.feature.voice;

import static org.junit.Assert.assertEquals;

import java.util.ArrayList;
import java.util.List;
import org.junit.Test;

public final class RealtimeToolCallQueueTest {
    @Test public void lateCompletionFromClosedSessionCannotStartAnotherCurrentTool() {
        RealtimeToolCallQueue queue = new RealtimeToolCallQueue();
        List<String> started = new ArrayList<>();
        List<RealtimeToolCallQueue.Completion> completions = new ArrayList<>();
        queue.reset();
        queue.enqueue(completion -> { started.add("old"); completions.add(completion); });
        queue.close();
        queue.reset();
        queue.enqueue(completion -> { started.add("current-a"); completions.add(completion); });
        queue.enqueue(completion -> { started.add("current-b"); completions.add(completion); });

        completions.get(0).complete();
        assertEquals(List.of("old", "current-a"), started);
        completions.get(1).complete();
        assertEquals(List.of("old", "current-a", "current-b"), started);
    }

    @Test public void resetAloneInvalidatesPreviouslyIssuedCompletions() {
        RealtimeToolCallQueue queue = new RealtimeToolCallQueue();
        List<String> started = new ArrayList<>();
        List<RealtimeToolCallQueue.Completion> completions = new ArrayList<>();
        queue.reset();
        queue.enqueue(completions::add);
        queue.reset();
        queue.enqueue(completion -> { started.add("current-a"); completions.add(completion); });
        queue.enqueue(completion -> started.add("current-b"));
        completions.get(0).complete();
        assertEquals(List.of("current-a"), started);
        completions.get(1).complete();
        assertEquals(List.of("current-a", "current-b"), started);
    }

    @Test public void duplicateCompletionDoesNotReleaseTheNextRunningTool() {
        RealtimeToolCallQueue queue = new RealtimeToolCallQueue();
        List<Integer> started = new ArrayList<>();
        List<RealtimeToolCallQueue.Completion> completions = new ArrayList<>();
        queue.reset();
        for (int i = 0; i < 3; i++) {
            final int id = i;
            queue.enqueue(completion -> { started.add(id); completions.add(completion); });
        }
        completions.get(0).complete();
        completions.get(0).complete();
        assertEquals(List.of(0, 1), started);
        completions.get(1).complete();
        assertEquals(List.of(0, 1, 2), started);
    }

    @Test public void oldInvocationExceptionCannotReleaseANewSessionTool() {
        RealtimeToolCallQueue queue = new RealtimeToolCallQueue();
        List<String> started = new ArrayList<>();
        queue.reset();
        queue.enqueue(completion -> {
            queue.reset();
            queue.enqueue(current -> started.add("current-a"));
            queue.enqueue(current -> started.add("current-b"));
            throw new IllegalStateException("Old invocation failed after reset");
        });
        assertEquals(List.of("current-a"), started);
    }

    @Test public void exceptionAfterCompletionCannotReleaseItsSuccessor() {
        RealtimeToolCallQueue queue = new RealtimeToolCallQueue();
        List<String> started = new ArrayList<>();
        queue.reset();
        queue.enqueue(completion -> {
            queue.enqueue(current -> started.add("next-a"));
            queue.enqueue(current -> started.add("next-b"));
            completion.complete();
            throw new IllegalStateException("Invocation failed after completing");
        });
        assertEquals(List.of("next-a"), started);
    }
}

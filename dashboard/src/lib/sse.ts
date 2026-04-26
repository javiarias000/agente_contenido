"use client";

import { useEffect, useRef, useState } from "react";
import type { PipelineEvent } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE || "/api-proxy";

export type RunStatus = "idle" | "running" | "paused" | "completed" | "failed";

export function useSSE(runId: string | null) {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [status, setStatus] = useState<RunStatus>("idle");
  const [pausedEvent, setPausedEvent] = useState<PipelineEvent | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) return;
    setEvents([]);
    setStatus("running");
    setPausedEvent(null);

    const es = new EventSource(`${BASE}/api/pipelines/sse/${runId}`);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const event: PipelineEvent = JSON.parse(e.data);
        if (event.event_type === "heartbeat") return;
        setEvents((prev) => [...prev, event]);

        if (event.event_type === "step_paused") {
          setStatus("paused");
          setPausedEvent(event);
        } else if (event.event_type === "pipeline_complete") {
          setStatus("completed");
          setPausedEvent(null);
          es.close();
        } else if (event.event_type === "pipeline_failed") {
          setStatus("failed");
          es.close();
        } else if (event.event_type !== "heartbeat") {
          setStatus("running");
        }
      } catch (_) {}
    };

    es.onerror = () => {
      setStatus((s) => (s === "running" ? "failed" : s));
      es.close();
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [runId]);

  const clearPause = () => setPausedEvent(null);

  return { events, status, pausedEvent, clearPause };
}

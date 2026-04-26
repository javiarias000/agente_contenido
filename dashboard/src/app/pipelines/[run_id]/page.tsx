"use client";

import { use } from "react";
import { useSSE } from "@/lib/sse";
import PipelineProgress from "@/components/PipelineProgress";
import FeedbackModal from "@/components/FeedbackModal";

export default function RunMonitorPage({ params }: { params: Promise<{ run_id: string }> }) {
  const { run_id } = use(params);
  const { events, status, pausedEvent, clearPause } = useSSE(run_id);

  const lastLog = [...events].reverse().find(e => ["progress", "log", "step_start"].includes(e.event_type));

  return (
    <div className="p-8 space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Monitor de Pipeline</h1>
          <p className="text-gray-400 text-xs mt-1 font-mono">{run_id}</p>
        </div>
        <span className={`text-sm px-3 py-1 rounded-full font-medium ${
          status === "completed" ? "bg-green-100 text-green-700" :
          status === "failed" ? "bg-red-100 text-red-700" :
          status === "paused" ? "bg-yellow-100 text-yellow-700" :
          "bg-blue-100 text-blue-700"
        }`}>
          {status}
        </span>
      </div>

      {/* Current step */}
      {lastLog && status === "running" && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
          <p className="text-sm text-blue-800">{lastLog.message}</p>
        </div>
      )}

      {/* Progress */}
      <div className="bg-white border rounded-xl p-6">
        <h2 className="font-semibold mb-4">Pasos</h2>
        <PipelineProgress events={events} status={status} />
      </div>

      {/* Event log */}
      <div className="bg-white border rounded-xl p-6">
        <h2 className="font-semibold mb-3">Log de eventos</h2>
        <div className="space-y-1.5 max-h-64 overflow-y-auto">
          {events.length === 0 ? (
            <p className="text-sm text-gray-400">Esperando eventos...</p>
          ) : (
            [...events].reverse().map((ev, i) => (
              <div key={i} className="flex gap-2 text-xs">
                <span className="text-gray-300 shrink-0">
                  {new Date(ev.timestamp).toLocaleTimeString("es")}
                </span>
                <span className={`shrink-0 font-medium ${
                  ev.event_type === "step_complete" ? "text-green-600" :
                  ev.event_type === "step_start" ? "text-blue-600" :
                  ev.event_type === "pipeline_failed" || ev.event_type === "step_error" ? "text-red-600" :
                  ev.event_type === "step_paused" ? "text-yellow-600" :
                  "text-gray-400"
                }`}>
                  [{ev.event_type}]
                </span>
                <span className="text-gray-600 truncate">{ev.message}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Feedback modal */}
      {pausedEvent && (
        <FeedbackModal
          runId={run_id}
          event={pausedEvent}
          onClose={clearPause}
        />
      )}
    </div>
  );
}

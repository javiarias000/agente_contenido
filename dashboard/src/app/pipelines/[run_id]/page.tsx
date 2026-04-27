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
    <div className="p-8 space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Monitor de Pipeline</h1>
          <p className="text-gray-500 text-xs mt-2 font-mono bg-gray-50 inline-block px-3 py-1 rounded-md">{run_id.slice(0, 8)}...</p>
        </div>
        <span className={`text-sm px-3 py-1.5 rounded-full font-medium ${
          status === "completed" ? "bg-green-100 text-green-700" :
          status === "failed" ? "bg-red-100 text-red-700" :
          status === "paused" ? "bg-amber-100 text-amber-700" :
          "bg-blue-100 text-blue-700"
        }`}>
          {status}
        </span>
      </div>

      {lastLog && status === "running" && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3.5">
          <p className="text-sm text-blue-900 font-medium">{lastLog.message}</p>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <h2 className="font-semibold text-slate-900 mb-4">Pasos</h2>
        <PipelineProgress events={events} status={status} />
      </div>

      <div className="bg-slate-50 border border-gray-200 rounded-xl p-6">
        <h2 className="font-semibold text-slate-900 mb-3">Log de eventos</h2>
        <div className="space-y-1 max-h-80 overflow-y-auto font-mono text-xs">
          {events.length === 0 ? (
            <p className="text-gray-500">Esperando eventos...</p>
          ) : (
            [...events].reverse().map((ev, i) => (
              <div key={i} className="flex gap-2 text-gray-700 hover:bg-white px-2 py-1 rounded transition-colors">
                <span className="text-gray-400 shrink-0 min-w-fit">
                  {new Date(ev.timestamp).toLocaleTimeString("es")}
                </span>
                <span className={`shrink-0 font-medium min-w-fit ${
                  ev.event_type === "step_complete" ? "text-green-600" :
                  ev.event_type === "step_start" ? "text-blue-600" :
                  ev.event_type === "pipeline_failed" || ev.event_type === "step_error" ? "text-red-600" :
                  ev.event_type === "step_paused" ? "text-amber-600" :
                  "text-gray-400"
                }`}>
                  {ev.event_type}
                </span>
                <span className="text-gray-600 truncate">{ev.message}</span>
              </div>
            ))
          )}
        </div>
      </div>

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

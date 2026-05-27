"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useSSE } from "@/lib/sse";
import { api } from "@/lib/api";
import PipelineProgress from "@/components/PipelineProgress";
import FeedbackModal from "@/components/FeedbackModal";
import { Wand2, Download, ExternalLink, ArrowLeft, CheckCircle2, XCircle, Loader2, Pause } from "lucide-react";
import { cn } from "@/lib/utils";

export default function RunMonitorPage({ params }: { params: Promise<{ run_id: string }> }) {
  const { run_id } = use(params);
  const { events, status, pausedEvent, clearPause } = useSSE(run_id);
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);

  const lastLog = [...events].reverse().find(e =>
    ["progress", "log", "step_start"].includes(e.event_type)
  );

  // Fetch outputs when completed
  useEffect(() => {
    if (status !== "completed") return;
    api.getRunOutputs(run_id)
      .then((outputs) => {
        const vid = outputs.find((o: { asset_type: string; id: number }) => o.asset_type === "video");
        if (vid) setFinalVideoUrl(api.getFileUrl(vid.id));
      })
      .catch(() => {});
  }, [status, run_id]);

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Link href="/studio" className="mt-1 p-1.5 rounded-lg hover:bg-slate-100 transition-colors text-slate-500">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Monitor de Pipeline</h1>
            <p className="text-xs text-gray-400 font-mono mt-1">{run_id}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={cn(
            "flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full font-medium",
            status === "completed" ? "bg-green-100 text-green-700" :
            status === "failed"    ? "bg-red-100 text-red-700"     :
            status === "paused"    ? "bg-amber-100 text-amber-700" :
                                     "bg-blue-100 text-blue-700"
          )}>
            {status === "running"   && <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />}
            {status === "completed" && <CheckCircle2 className="h-3.5 w-3.5" />}
            {status === "failed"    && <XCircle      className="h-3.5 w-3.5" />}
            {status === "paused"    && <Pause        className="h-3.5 w-3.5" />}
            {status === "running"   && <Loader2      className="h-3.5 w-3.5 animate-spin" />}
            {status}
          </span>

          <Link href="/studio" className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-violet-200 text-violet-700 hover:bg-violet-50 transition-all font-medium">
            <Wand2 className="h-3.5 w-3.5" />
            Crear otro en Studio
          </Link>
        </div>
      </div>

      {/* ── Live status message ── */}
      {lastLog && status === "running" && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 text-blue-600 animate-spin shrink-0" />
            <p className="text-sm text-blue-900 font-medium">{lastLog.message}</p>
          </div>
        </div>
      )}

      {/* ── Final video player ── */}
      {status === "completed" && finalVideoUrl && (
        <div className="rounded-xl overflow-hidden border border-slate-200 bg-black">
          <video src={finalVideoUrl} controls autoPlay className="w-full max-h-[500px] object-contain" />
          <div className="bg-slate-900 px-4 py-3 flex items-center gap-3">
            <a href={finalVideoUrl} download
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-sm font-semibold transition-all">
              <Download className="h-4 w-4" />
              Descargar video
            </a>
            <Link href="/outputs"
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm font-medium transition-all">
              <ExternalLink className="h-4 w-4" />
              Ver en Outputs
            </Link>
          </div>
        </div>
      )}

      {/* ── Steps ── */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="font-semibold text-slate-900 mb-4">Pasos del pipeline</h2>
        <PipelineProgress events={events} status={status} />
      </div>

      {/* ── Event log ── */}
      <div className="bg-slate-900 rounded-xl p-5">
        <h2 className="font-mono text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Log de eventos</h2>
        <div className="space-y-1 max-h-64 overflow-y-auto font-mono text-xs">
          {events.length === 0 ? (
            <p className="text-slate-500 flex items-center gap-2">
              <Loader2 className="h-3 w-3 animate-spin" /> Esperando eventos…
            </p>
          ) : (
            [...events].reverse().map((ev, i) => (
              <div key={i} className="flex gap-3 hover:bg-slate-800 px-2 py-1 rounded transition-colors">
                <span className="text-slate-600 shrink-0 min-w-[60px]">
                  {new Date(ev.timestamp).toLocaleTimeString("es")}
                </span>
                <span className={cn("shrink-0 min-w-[140px]",
                  ev.event_type === "step_complete"  ? "text-green-400" :
                  ev.event_type === "step_start"     ? "text-blue-400"  :
                  ev.event_type.includes("error") || ev.event_type.includes("failed") ? "text-red-400" :
                  ev.event_type === "step_paused"    ? "text-amber-400" : "text-slate-500"
                )}>
                  {ev.event_type}
                </span>
                <span className="text-slate-400 truncate">{ev.message}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {pausedEvent && (
        <FeedbackModal runId={run_id} event={pausedEvent} onClose={clearPause} />
      )}
    </div>
  );
}

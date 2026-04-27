"use client";

import { CheckCircle, Circle, Loader2, XCircle, PauseCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PipelineEvent } from "@/lib/types";

interface PipelineProgressProps {
  events: PipelineEvent[];
  status: string;
}

interface StepState {
  name: string;
  status: "pending" | "running" | "completed" | "failed" | "paused";
  message?: string;
}

const STEP_LABELS: Record<string, string> = {
  brand_load: "Cargar Marca",
  script_generate: "Generar Guión",
  image_generate: "Generar Imágenes",
  voice_generate: "Generar Voz",
  video_assemble: "Ensamblar Video",
  subtitle_burn: "Subtítulos",
  generate_ads: "Generar Anuncios",
  lip_sync: "Lip-sync",
};

export default function PipelineProgress({ events, status }: PipelineProgressProps) {
  const stepMap = new Map<string, StepState>();

  for (const ev of events) {
    if (!ev.step_name) continue;
    const name = ev.step_name;
    if (ev.event_type === "step_start") {
      stepMap.set(name, { name, status: "running", message: ev.message });
    } else if (ev.event_type === "step_complete") {
      stepMap.set(name, { name, status: "completed", message: ev.message });
    } else if (ev.event_type === "step_error") {
      stepMap.set(name, { name, status: "failed", message: ev.message });
    } else if (ev.event_type === "step_paused") {
      stepMap.set(name, { name, status: "paused", message: ev.message });
    }
  }

  const steps = Array.from(stepMap.values());

  if (steps.length === 0 && status === "idle") {
    return (
      <p className="text-sm text-gray-500">El pipeline aún no ha iniciado.</p>
    );
  }

  return (
    <div className="space-y-4">
      {steps.map((step, i) => (
        <div key={step.name} className="flex items-start gap-3">
          <div className="mt-1 flex flex-col items-center">
            {step.status === "completed" && <CheckCircle className="h-5 w-5 text-green-500" />}
            {step.status === "running" && <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />}
            {step.status === "failed" && <XCircle className="h-5 w-5 text-red-500" />}
            {step.status === "paused" && <PauseCircle className="h-5 w-5 text-amber-500" />}
            {step.status === "pending" && <Circle className="h-5 w-5 text-gray-300" />}
            {i < steps.length - 1 && <div className="w-0.5 h-3 bg-gray-200 my-1" />}
          </div>
          <div className="flex-1 min-w-0 pt-0.5">
            <p className={cn("text-sm font-medium", {
              "text-green-700": step.status === "completed",
              "text-blue-700": step.status === "running",
              "text-red-700": step.status === "failed",
              "text-amber-700": step.status === "paused",
              "text-gray-400": step.status === "pending",
            })}>
              {STEP_LABELS[step.name] || step.name}
            </p>
            {step.message && (
              <p className="text-xs text-gray-500 truncate">{step.message}</p>
            )}
          </div>
        </div>
      ))}
      {status === "completed" && (
        <div className="mt-4 p-3 rounded-lg bg-green-50 border border-green-200">
          <p className="text-sm text-green-800 font-medium">Pipeline completado exitosamente</p>
        </div>
      )}
      {status === "failed" && (
        <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200">
          <p className="text-sm text-red-800 font-medium">El pipeline falló</p>
        </div>
      )}
    </div>
  );
}

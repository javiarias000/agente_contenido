"use client";

import Link from "next/link";
import useSWR from "swr";
import { api } from "@/lib/api";
import {
  Building2, CheckCircle2, Activity, Zap, Search,
  Wand2, Film, Sparkles, ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  pending:   "bg-gray-100 text-gray-600",
  running:   "bg-blue-100 text-blue-700",
  paused:    "bg-amber-100 text-amber-700",
  completed: "bg-green-100 text-green-700",
  failed:    "bg-red-100 text-red-700",
};

const PIPELINE_ICONS: Record<string, typeof Film> = {
  hyperframes: Sparkles,
  ugc:         Film,
  static_ads:  Zap,
  avatar_reel: Zap,
  carousel:    Zap,
};

export default function Home() {
  const { data: brands } = useSWR("brands", api.listBrands, { refreshInterval: 10000 });
  const { data: runs   } = useSWR("runs",   api.listRuns,   { refreshInterval: 5000  });

  const recentRuns     = runs?.slice(0, 8) || [];
  const completedRuns  = runs?.filter((r: { status: string }) => r.status === "completed").length || 0;
  const runningNow     = runs?.filter((r: { status: string }) => r.status === "running").length   || 0;
  const studioRuns     = runs?.filter((r: { pipeline_type: string }) =>
    ["hyperframes", "ugc"].includes(r.pipeline_type)
  ).length || 0;

  return (
    <div className="p-8 space-y-8 max-w-6xl">
      {/* ── Title ── */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1.5">Centro de control del Motor de Contenido IA</p>
      </div>

      {/* ── Stats ── */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-medium">Marcas</p>
            <Building2 className="h-4 w-4 text-blue-600" />
          </div>
          <p className="text-4xl font-bold text-slate-900">{brands?.length || 0}</p>
          <p className="text-xs text-gray-500">Perfiles analizados</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-medium">Completados</p>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </div>
          <p className="text-4xl font-bold text-slate-900">{completedRuns}</p>
          <p className="text-xs text-gray-500">Pipelines finalizados</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-medium">En ejecución</p>
            <Activity className="h-4 w-4 text-blue-600" />
          </div>
          <p className="text-4xl font-bold text-slate-900">{runningNow}</p>
          <p className="text-xs text-gray-500">Procesos activos {runningNow > 0 && <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse ml-1" />}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-medium">Videos Studio</p>
            <Sparkles className="h-4 w-4 text-violet-600" />
          </div>
          <p className="text-4xl font-bold text-slate-900">{studioRuns}</p>
          <p className="text-xs text-gray-500">HyperFrames + UGC</p>
        </div>
      </div>

      {/* ── Quick actions ── */}
      <div className="grid grid-cols-3 gap-4">
        {/* Studio — featured */}
        <Link href="/studio"
          className="col-span-1 bg-gradient-to-br from-violet-600 to-violet-800 text-white rounded-xl p-6 block hover:shadow-xl hover:-translate-y-0.5 transition-all space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
              <Wand2 className="h-5 w-5 text-white" />
            </div>
            <ArrowRight className="h-4 w-4 text-white/60" />
          </div>
          <div>
            <h3 className="font-bold text-xl">Video Studio</h3>
            <p className="text-violet-200 text-sm mt-1">IA + HyperFrames · 8 plantillas profesionales · Chat asistido</p>
          </div>
        </Link>

        <Link href="/pipelines/run"
          className="bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-xl p-6 block hover:shadow-lg hover:-translate-y-0.5 transition-all space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <ArrowRight className="h-4 w-4 text-white/60" />
          </div>
          <div>
            <h3 className="font-bold text-lg">Pipeline avanzado</h3>
            <p className="text-blue-200 text-sm mt-1">Control completo de todos los parámetros</p>
          </div>
        </Link>

        <Link href="/brands"
          className="bg-white border border-gray-200 text-slate-900 rounded-xl p-6 block hover:shadow-md hover:-translate-y-0.5 transition-all space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
              <Search className="h-5 w-5 text-blue-600" />
            </div>
            <ArrowRight className="h-4 w-4 text-slate-300" />
          </div>
          <div>
            <h3 className="font-bold text-lg">Analizar Marca</h3>
            <p className="text-gray-500 text-sm mt-1">Extrae perfil visual y tono de cualquier URL</p>
          </div>
        </Link>
      </div>

      {/* ── Recent runs ── */}
      {recentRuns.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-slate-900">Ejecuciones Recientes</h2>
            <Link href="/pipelines" className="text-xs text-blue-600 hover:text-blue-800 font-medium">Ver todas →</Link>
          </div>
          <div className="space-y-2">
            {recentRuns.map((run: { run_id: string; pipeline_type: string; status: string; steps_completed: number; steps_total: number | null; created_at: string }) => {
              const Icon = PIPELINE_ICONS[run.pipeline_type] || Zap;
              const isStudio = ["hyperframes", "ugc"].includes(run.pipeline_type);
              return (
                <Link key={run.run_id} href={`/pipelines/${run.run_id}`}
                  className="bg-white border border-gray-200 rounded-xl px-5 py-4 flex items-center justify-between hover:border-blue-300 hover:shadow-sm transition-all group"
                >
                  <div className="flex items-center gap-3">
                    <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center",
                      isStudio ? "bg-violet-100" : "bg-blue-50"
                    )}>
                      <Icon className={cn("h-4 w-4", isStudio ? "text-violet-600" : "text-blue-600")} />
                    </div>
                    <div>
                      <p className="font-medium text-sm capitalize text-slate-900">
                        {run.pipeline_type.replace(/_/g, " ")}
                        {isStudio && <span className="ml-2 text-xs text-violet-500 font-semibold">STUDIO</span>}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">{new Date(run.created_at).toLocaleString("es")}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {run.steps_total && (
                      <p className="text-xs text-gray-400">{run.steps_completed}/{run.steps_total} pasos</p>
                    )}
                    <span className={cn("text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1", STATUS_COLORS[run.status] || "bg-gray-100 text-gray-600")}>
                      {run.status === "running" && <span className="inline-block h-1.5 w-1.5 rounded-full bg-current animate-pulse" />}
                      {run.status}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Empty state */}
      {recentRuns.length === 0 && brands?.length === 0 && (
        <div className="text-center py-16 space-y-4">
          <div className="w-16 h-16 bg-violet-100 rounded-2xl flex items-center justify-center mx-auto">
            <Wand2 className="h-8 w-8 text-violet-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-800">Empieza creando una marca</h3>
            <p className="text-slate-500 text-sm mt-1">Después podrás generar videos profesionales desde el Studio</p>
          </div>
          <div className="flex items-center justify-center gap-3">
            <Link href="/brands/new" className="px-5 py-2.5 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 transition-all">
              Crear marca
            </Link>
            <Link href="/studio" className="px-5 py-2.5 bg-violet-600 text-white rounded-xl font-semibold text-sm hover:bg-violet-700 transition-all">
              Abrir Studio
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

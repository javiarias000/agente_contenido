"use client";

import Link from "next/link";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Building2, CheckCircle2, Activity, Zap, Search } from "lucide-react";

const statusColors: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  running: "bg-blue-100 text-blue-700",
  paused: "bg-amber-100 text-amber-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function Home() {
  const { data: brands } = useSWR("brands", api.listBrands, { refreshInterval: 10000 });
  const { data: runs } = useSWR("runs", api.listRuns, { refreshInterval: 5000 });

  const recentRuns = runs?.slice(0, 8) || [];
  const completedToday = runs?.filter(r => r.status === "completed").length || 0;
  const runningNow = runs?.filter(r => r.status === "running").length || 0;

  return (
    <div className="p-8 space-y-8 max-w-6xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1.5">Centro de control del Motor de Contenido IA</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-medium">Marcas</p>
            <Building2 className="h-4 w-4 text-blue-600" />
          </div>
          <p className="text-4xl font-bold text-slate-900">{brands?.length || 0}</p>
          <p className="text-xs text-gray-500">Perfiles analizados</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-medium">Completados</p>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </div>
          <p className="text-4xl font-bold text-slate-900">{completedToday}</p>
          <p className="text-xs text-gray-500">Pipelines finalizados</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-medium">En ejecución</p>
            <Activity className="h-4 w-4 text-blue-600" />
          </div>
          <p className="text-4xl font-bold text-slate-900">{runningNow}</p>
          <p className="text-xs text-gray-500">Procesos activos</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Link href="/pipelines"
          className="bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-xl p-6 block hover:shadow-lg hover:-translate-y-0.5 transition-all space-y-2"
        >
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            <h3 className="font-bold text-lg">Nuevo Pipeline</h3>
          </div>
          <p className="text-blue-100 text-sm">Genera UGC, Ads, Avatar Reel o Carrusel</p>
        </Link>

        <Link href="/brands"
          className="bg-white border border-gray-200 text-slate-900 rounded-xl p-6 block hover:shadow-md hover:-translate-y-0.5 transition-all space-y-2"
        >
          <div className="flex items-center gap-2">
            <Search className="h-5 w-5 text-blue-600" />
            <h3 className="font-bold text-lg">Analizar Marca</h3>
          </div>
          <p className="text-gray-600 text-sm">Extrae perfil visual y tono de cualquier URL</p>
        </Link>
      </div>

      {recentRuns.length > 0 && (
        <div>
          <h2 className="font-semibold text-slate-900 mb-4">Ejecuciones Recientes</h2>
          <div className="space-y-2">
            {recentRuns.map((run) => (
              <Link key={run.run_id} href={`/pipelines/${run.run_id}`}
                className="bg-white border border-gray-200 rounded-xl px-5 py-4 flex items-center justify-between hover:border-blue-300 hover:shadow-sm transition-all"
              >
                <div>
                  <p className="font-medium text-sm capitalize text-slate-900">{run.pipeline_type.replace("_", " ")}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{new Date(run.created_at).toLocaleString("es")}</p>
                </div>
                <div className="flex items-center gap-3">
                  {run.steps_total && (
                    <p className="text-xs text-gray-500">{run.steps_completed}/{run.steps_total} pasos</p>
                  )}
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${statusColors[run.status] || "bg-gray-100 text-gray-600"}`}>
                    {run.status === "running" && <span className="inline-block h-1.5 w-1.5 rounded-full bg-current mr-1.5 animate-pulse" />}
                    {run.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import Link from "next/link";
import useSWR from "swr";
import { api } from "@/lib/api";

const statusColors: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  running: "bg-blue-100 text-blue-700",
  paused: "bg-yellow-100 text-yellow-700",
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
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Centro de control del Motor de Contenido IA</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border p-5">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Marcas</p>
          <p className="text-3xl font-bold mt-1">{brands?.length || 0}</p>
        </div>
        <div className="bg-white rounded-xl border p-5">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Completados</p>
          <p className="text-3xl font-bold mt-1 text-green-600">{completedToday}</p>
        </div>
        <div className="bg-white rounded-xl border p-5">
          <p className="text-xs text-gray-400 uppercase tracking-wide">En ejecución</p>
          <p className="text-3xl font-bold mt-1 text-blue-600">{runningNow}</p>
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-4">
        <Link
          href="/pipelines"
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl p-6 block transition-colors"
        >
          <h3 className="font-bold text-lg">Nuevo Pipeline</h3>
          <p className="text-blue-100 text-sm mt-1">Genera UGC, Ads, Avatar Reel o Carrusel</p>
        </Link>
        <Link
          href="/brands"
          className="bg-white hover:bg-gray-50 border rounded-xl p-6 block transition-colors"
        >
          <h3 className="font-bold text-lg">Analizar Marca</h3>
          <p className="text-gray-500 text-sm mt-1">Extrae perfil visual y tono de cualquier URL</p>
        </Link>
      </div>

      {/* Recent runs */}
      <div>
        <h2 className="font-semibold mb-3">Ejecuciones Recientes</h2>
        {recentRuns.length === 0 ? (
          <div className="bg-white rounded-xl border p-6 text-center text-gray-400 text-sm">
            No hay ejecuciones aún. Crea tu primer pipeline.
          </div>
        ) : (
          <div className="space-y-2">
            {recentRuns.map((run) => (
              <Link
                key={run.run_id}
                href={`/pipelines/${run.run_id}`}
                className="bg-white border rounded-xl p-4 flex items-center justify-between hover:border-blue-300 transition-colors"
              >
                <div>
                  <p className="font-medium text-sm capitalize">{run.pipeline_type.replace("_", " ")}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(run.created_at).toLocaleString("es")}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {run.steps_total && (
                    <p className="text-xs text-gray-400">
                      {run.steps_completed}/{run.steps_total} pasos
                    </p>
                  )}
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${statusColors[run.status] || "bg-gray-100 text-gray-600"}`}>
                    {run.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

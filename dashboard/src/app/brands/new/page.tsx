"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import PipelineProgress from "@/components/PipelineProgress";

export default function NewBrandPage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const { events, status } = useSSE(runId);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url) return;
    setLoading(true);
    try {
      const res = await api.analyzeBrand(url, name, false);
      setRunId(res.run_id);
    } catch (err) {
      alert("Error iniciando análisis");
    } finally {
      setLoading(false);
    }
  }

  if (status === "completed") {
    const slugEvent = events.find(e => e.data?.brand_slug);
    const slug = slugEvent?.data?.brand_slug as string | undefined;
    return (
      <div className="p-8 max-w-lg">
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 space-y-3">
          <p className="font-semibold text-green-800">¡Marca analizada!</p>
          {slug && (
            <button
              onClick={() => router.push(`/brands/${slug}`)}
              className="bg-green-600 text-white rounded-lg px-4 py-2 text-sm"
            >
              Ver perfil de {slug}
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Analizar Marca</h1>
        <p className="text-gray-500 text-sm mt-1">Extrae perfil visual, tono y audiencia de una URL</p>
      </div>

      {!runId ? (
        <form onSubmit={handleSubmit} className="space-y-4 bg-white border rounded-xl p-6">
          <div>
            <label className="text-sm font-medium block mb-1">URL del sitio web *</label>
            <input
              type="url"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://miempresa.com"
              required
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-1">Nombre de la marca (opcional)</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Mi Empresa"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2.5 text-sm font-medium disabled:opacity-50"
          >
            {loading ? "Iniciando..." : "Analizar marca"}
          </button>
        </form>
      ) : (
        <div className="bg-white border rounded-xl p-6">
          <h2 className="font-semibold mb-4">Analizando marca...</h2>
          <PipelineProgress events={events} status={status} />
        </div>
      )}
    </div>
  );
}

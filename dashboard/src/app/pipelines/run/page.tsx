"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
import { api } from "@/lib/api";

function RunPipelineForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const defaultType = searchParams.get("type") || "ugc";

  const [form, setForm] = useState({
    pipeline_type: defaultType,
    brand_slug: "",
    mode: "interactive",
    platform: "tiktok",
    angle_type: "sales",
    target_duration: 60,
    character_description: "",
    competitor_name: "",
    custom_hook: "",
    voice_id: "",
    num_ads: 10,
    topic: "",
    num_slides: 6,
    news_url: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { data: brands } = useSWR("brands", api.listBrands);

  const update = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    let value: any = e.target.value;
    if (["target_duration", "num_ads", "num_slides"].includes(k)) {
      value = parseInt(value, 10) || 0;
    }
    setForm(f => ({ ...f, [k]: value }));
  };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!form.brand_slug) {
      setError("Selecciona una marca para continuar");
      return;
    }
    setLoading(true);
    try {
      const res = await api.runPipeline(form);
      router.push(`/pipelines/${res.run_id}`);
    } catch (err: any) {
      setError(err.message || "Error al ejecutar el pipeline");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Configurar Pipeline</h1>
        <p className="text-gray-500 text-sm mt-1">Define los parámetros antes de ejecutar</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white border rounded-xl p-6 space-y-4">
        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}
        <div>
          <label className="text-sm font-medium block mb-1">Tipo de Pipeline</label>
          <select value={form.pipeline_type} onChange={update("pipeline_type")} className="w-full border rounded-lg px-3 py-2 text-sm">
            <option value="ugc">UGC Pipeline</option>
            <option value="static_ads">Static Ads</option>
            <option value="avatar_reel">Avatar Reel</option>
            <option value="carousel">Carousel</option>
          </select>
        </div>

        <div>
          <label className="text-sm font-medium block mb-1">Marca *</label>
          <select value={form.brand_slug} onChange={update("brand_slug")} className="w-full border rounded-lg px-3 py-2 text-sm" required>
            <option value="">Selecciona una marca</option>
            {brands?.map((b: any) => (
              <option key={b.slug} value={b.slug}>{b.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-sm font-medium block mb-1">Modo</label>
          <select value={form.mode} onChange={update("mode")} className="w-full border rounded-lg px-3 py-2 text-sm">
            <option value="interactive">Interactivo (revisión en cada paso)</option>
            <option value="headless">Headless (automático sin paradas)</option>
          </select>
        </div>

        {(form.pipeline_type === "ugc" || form.pipeline_type === "avatar_reel") && (
          <>
            <div>
              <label className="text-sm font-medium block mb-1">Plataforma</label>
              <select value={form.platform} onChange={update("platform")} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="tiktok">TikTok</option>
                <option value="instagram_reel">Instagram Reel</option>
                <option value="youtube_short">YouTube Short</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Ángulo de contenido</label>
              <select value={form.angle_type} onChange={update("angle_type")} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="sales">Ventas / UGC</option>
                <option value="educational">Educativo</option>
                <option value="competitor">Comparación con competidor</option>
                <option value="trending">Tendencia / Noticia</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Duración objetivo (seg)</label>
              <input type="number" value={form.target_duration} onChange={update("target_duration")} min={15} max={90} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            {form.angle_type === "competitor" && (
              <div>
                <label className="text-sm font-medium block mb-1">Nombre del competidor</label>
                <input type="text" value={form.competitor_name} onChange={update("competitor_name")} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Ej: Amazon" />
              </div>
            )}
            <div>
              <label className="text-sm font-medium block mb-1">Descripción del personaje (opcional)</label>
              <input type="text" value={form.character_description} onChange={update("character_description")} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Ej: Mujer de 25 años, energética" />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Hook personalizado (opcional)</label>
              <input type="text" value={form.custom_hook} onChange={update("custom_hook")} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Ej: ¿Sabías que...?" />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">ID de voz (opcional)</label>
              <input type="text" value={form.voice_id} onChange={update("voice_id")} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Ej: rachel" />
            </div>
            {form.pipeline_type === "avatar_reel" && (
              <div>
                <label className="text-sm font-medium block mb-1">URL de noticia (opcional)</label>
                <input type="url" value={form.news_url} onChange={update("news_url")} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Ej: https://example.com/news" />
              </div>
            )}
          </>
        )}

        {form.pipeline_type === "static_ads" && (
          <div>
            <label className="text-sm font-medium block mb-1">Número de anuncios</label>
            <input type="number" value={form.num_ads} onChange={update("num_ads")} min={1} max={40} className="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
        )}

        {form.pipeline_type === "carousel" && (
          <>
            <div>
              <label className="text-sm font-medium block mb-1">Tema del carrusel</label>
              <input type="text" value={form.topic} onChange={update("topic")} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Ej: 5 tips de productividad" />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Número de slides</label>
              <input type="number" value={form.num_slides} onChange={update("num_slides")} min={3} max={12} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Hook personalizado (opcional)</label>
              <input type="text" value={form.custom_hook} onChange={update("custom_hook")} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Ej: Descubre..." />
            </div>
          </>
        )}

        <button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2.5 text-sm font-medium disabled:opacity-50">
          {loading ? "Iniciando..." : "Ejecutar Pipeline"}
        </button>
      </form>
    </div>
  );
}

export default function RunPage() {
  return (
    <Suspense fallback={<div className="p-8 text-gray-400">Cargando...</div>}>
      <RunPipelineForm />
    </Suspense>
  );
}

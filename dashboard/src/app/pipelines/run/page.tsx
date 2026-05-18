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
    user_photo_path: "",
    num_ads: 10,
    topic: "",
    num_slides: 6,
    news_url: "",
    visual_style: "swiss_pulse",
    transition_style: "crossfade",
    motion_intensity: "medium",
    text_animation: "slide",
    creative_brief: "",
  });
  const [loading, setLoading] = useState(false);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoLoading, setPhotoLoading] = useState(false);
  const [error, setError] = useState("");
  const { data: brands } = useSWR("brands", api.listBrands);

  const update = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    let value: any = e.target.value;
    if (["target_duration", "num_ads", "num_slides"].includes(k)) {
      value = parseInt(value, 10) || 0;
    }
    setForm(f => ({ ...f, [k]: value }));
  };

  async function handlePhotoUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setPhotoFile(file);
    setPhotoLoading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/uploads/photo", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Error al subir foto");
      }

      const data = await response.json();
      setForm(f => ({ ...f, user_photo_path: data.photo_path }));
    } catch (err: any) {
      setError(err.message || "Error al subir la foto");
      setPhotoFile(null);
    } finally {
      setPhotoLoading(false);
    }
  }

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
            <option value="hyperframes">HyperFrames Video</option>
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
            {form.pipeline_type === "ugc" && (
              <div>
                <label className="text-sm font-medium block mb-1">Foto del producto (opcional)</label>
                <div className="flex items-center gap-3">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handlePhotoUpload}
                    disabled={photoLoading}
                    className="flex-1 border rounded-lg px-3 py-2 text-sm file:mr-2 file:px-3 file:py-1.5 file:rounded file:border-0 file:text-xs file:font-medium file:bg-blue-50 file:text-blue-700"
                  />
                  {photoLoading && <span className="text-xs text-gray-400">Cargando...</span>}
                </div>
                {photoFile && !photoLoading && (
                  <p className="text-xs text-green-600 mt-1">✓ Foto cargada: {photoFile.name}</p>
                )}
              </div>
            )}
            {form.pipeline_type === "avatar_reel" && (
              <div>
                <label className="text-sm font-medium block mb-1">URL de noticia (opcional)</label>
                <input type="url" value={form.news_url} onChange={update("news_url")} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Ej: https://example.com/news" />
              </div>
            )}
            <hr className="border-gray-100" />
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Efectos y movimiento</p>
            <div>
              <label className="text-sm font-medium block mb-1">Transición entre escenas</label>
              <select value={form.transition_style} onChange={update("transition_style")} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="crossfade">Crossfade — fundido negro</option>
                <option value="flash">Flash — destello blanco</option>
                <option value="zoom_punch">Zoom Punch — impacto cinético</option>
                <option value="wipe_left">Wipe Left — deslizamiento</option>
                <option value="glitch">Glitch — distorsión digital</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Intensidad de movimiento (Ken Burns)</label>
              <select value={form.motion_intensity} onChange={update("motion_intensity")} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="calm">Calm — suave, elegante (3%)</option>
                <option value="medium">Medium — equilibrado (8%)</option>
                <option value="energetic">Energetic — dinámico, fuerte (16%)</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Brief creativo del cliente (opcional)</label>
              <textarea
                value={form.creative_brief}
                onChange={update("creative_brief")}
                rows={2}
                className="w-full border rounded-lg px-3 py-2 text-sm resize-none"
                placeholder="Ej: Quiero mucho movimiento, estilo Instagram fitness, colores vibrantes..."
              />
            </div>
          </>
        )}

        {form.pipeline_type === "hyperframes" && (
          <>
            <div>
              <label className="text-sm font-medium block mb-1">Plataforma</label>
              <select value={form.platform} onChange={update("platform")} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="tiktok">TikTok (9:16)</option>
                <option value="instagram_reel">Instagram Reel (9:16)</option>
                <option value="youtube_short">YouTube Short (9:16)</option>
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
              <label className="text-sm font-medium block mb-1">Estilo visual</label>
              <select value={form.visual_style} onChange={update("visual_style")} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="swiss_pulse">Swiss Pulse — limpio, SaaS, tech</option>
                <option value="maximalist_type">Maximalist Type — potente, kinético, redes</option>
                <option value="data_drift">Data Drift — futurista, IA/ML, neon</option>
                <option value="soft_signal">Soft Signal — íntimo, wellness, lifestyle</option>
                <option value="velvet_standard">Velvet Standard — premium, lujo, atemporal</option>
                <option value="shadow_cut">Shadow Cut — oscuro, cinemático, editorial</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Duración objetivo (seg)</label>
              <input type="number" value={form.target_duration} onChange={update("target_duration")} min={15} max={90} className="w-full border rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Hook personalizado (opcional)</label>
              <input type="text" value={form.custom_hook} onChange={update("custom_hook")} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Ej: ¿Sabías que...?" />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">ID de voz (opcional)</label>
              <input type="text" value={form.voice_id} onChange={update("voice_id")} className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Ej: rachel" />
            </div>
            <hr className="border-gray-100" />
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Efectos y transiciones</p>
            <div>
              <label className="text-sm font-medium block mb-1">Transición entre escenas</label>
              <select value={form.transition_style} onChange={update("transition_style")} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="crossfade">Crossfade — fundido suave</option>
                <option value="flash">Flash — destello blanco</option>
                <option value="zoom_punch">Zoom Punch — impacto cinético</option>
                <option value="wipe_left">Wipe Left — deslizamiento</option>
                <option value="glitch">Glitch — distorsión digital</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Intensidad de movimiento</label>
              <select value={form.motion_intensity} onChange={update("motion_intensity")} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="calm">Calm — suave, elegante</option>
                <option value="medium">Medium — equilibrado</option>
                <option value="energetic">Energetic — dinámico, impactante</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Animación de texto</label>
              <select value={form.text_animation} onChange={update("text_animation")} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="slide">Slide — entrada desde abajo</option>
                <option value="scale">Scale — aparece ampliándose</option>
                <option value="split">Split — palabras desde lados opuestos</option>
                <option value="typewriter">Typewriter — aparece letra a letra</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Brief creativo del cliente (opcional)</label>
              <textarea
                value={form.creative_brief}
                onChange={update("creative_brief")}
                rows={3}
                className="w-full border rounded-lg px-3 py-2 text-sm resize-none"
                placeholder="Ej: El cliente quiere efectos glitch en los titulares y un ritmo muy rápido tipo reels de moda..."
              />
            </div>
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

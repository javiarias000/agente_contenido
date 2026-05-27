"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import type { PipelineEvent } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Sparkles, Film, Zap, Heart, Minimize2, TrendingUp, Star,
  Clapperboard, Code2, CheckCircle2, XCircle, Loader2, Download,
  ExternalLink, ArrowLeft, Play, Camera, Video, Pause, Check, RotateCcw,
} from "lucide-react";

// ── Paths ─────────────────────────────────────────────────────────────────────
// Preview URLs (browser) — served via Next.js proxy → FastAPI static files
const PV = "/api-proxy/outputs/uploads";
// Backend absolute paths (inside Docker container)
const CP = "./outputs/uploads";

// ── Example definitions ───────────────────────────────────────────────────────

const HF_EXAMPLES = [
  {
    id: "hf-minimalista",
    label: "Minimalista",
    tag: "CLEAN",
    icon: Minimize2,
    gradient: "from-slate-800 to-slate-600",
    accent: "#e2e8f0",
    preview: `${PV}/customers.jpg`,
    pipeline: "hyperframes",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "hyperframes",
      platform: "instagram",
      angle_type: "sales",
      target_duration: 45,
      visual_style: "swiss_pulse",
      transition_style: "crossfade",
      motion_intensity: "calm",
      text_animation: "slide",
      creative_brief:
        "Mi Idea — estudio de corte láser en Colombia. Video minimalista y elegante: muestra la precisión del servicio, tipografía limpia, espacio en blanco. Transmite excelencia artesanal con un mínimo de elementos.",
    },
  },
  {
    id: "hf-marketero",
    label: "Marketero",
    tag: "SALES",
    icon: TrendingUp,
    gradient: "from-orange-600 to-red-500",
    accent: "#fed7aa",
    preview: `${PV}/customers2.jpg`,
    pipeline: "hyperframes",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "hyperframes",
      platform: "tiktok",
      angle_type: "sales",
      target_duration: 30,
      visual_style: "maximalist_type",
      transition_style: "flash",
      motion_intensity: "energetic",
      text_animation: "scale",
      creative_brief:
        "Mi Idea — corte láser personalizado. Video de ventas agresivo: beneficios en 3 segundos, precios competitivos, CTA urgente. ¡Pide tu diseño hoy! Material de alta calidad, entrega rápida.",
    },
  },
  {
    id: "hf-simple",
    label: "Simple",
    tag: "CLEAR",
    icon: Film,
    gradient: "from-blue-600 to-blue-400",
    accent: "#bfdbfe",
    preview: `${PV}/customers.jpg`,
    pipeline: "hyperframes",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "hyperframes",
      platform: "instagram",
      angle_type: "educational",
      target_duration: 45,
      visual_style: "soft_signal",
      transition_style: "crossfade",
      motion_intensity: "calm",
      text_animation: "slide",
      creative_brief:
        "Mi Idea — explicar qué es el corte láser de forma simple. ¿Tienes una idea? Nosotros la hacemos realidad. Proceso en 3 pasos: diseño, corte, entrega. Directo y fácil de entender.",
    },
  },
  {
    id: "hf-emocionante",
    label: "Emocionante",
    tag: "ENERGY",
    icon: Zap,
    gradient: "from-purple-700 to-pink-500",
    accent: "#f0abfc",
    preview: `${PV}/mi-idea-product1.jpg`,
    pipeline: "hyperframes",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "hyperframes",
      platform: "tiktok",
      angle_type: "trending",
      target_duration: 30,
      visual_style: "shadow_cut",
      transition_style: "glitch",
      motion_intensity: "energetic",
      text_animation: "split",
      creative_brief:
        "Mi Idea — energía total. Corte láser en acción, chispas, precisión máxima. Para creadores que no se conforman con lo ordinario. Alta intensidad, impacto visual, ritmo fast-cut.",
    },
  },
  {
    id: "hf-elegante",
    label: "Elegante",
    tag: "LUXURY",
    icon: Star,
    gradient: "from-amber-800 to-yellow-600",
    accent: "#fde68a",
    preview: `${PV}/customers2.jpg`,
    pipeline: "hyperframes",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "hyperframes",
      platform: "instagram",
      angle_type: "sales",
      target_duration: 60,
      visual_style: "velvet_standard",
      transition_style: "wipe_left",
      motion_intensity: "medium",
      text_animation: "split",
      creative_brief:
        "Mi Idea — la elegancia del corte láser de precisión. Para quienes valoran la calidad por encima de todo. Diseños únicos, materiales premium, atención al detalle que se nota.",
    },
  },
  {
    id: "hf-cinematografico",
    label: "Cinematográfico",
    tag: "CINEMA",
    icon: Clapperboard,
    gradient: "from-gray-900 to-gray-600",
    accent: "#d1d5db",
    preview: `${PV}/mi-idea-product2.jpg`,
    pipeline: "hyperframes",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "hyperframes",
      platform: "instagram",
      angle_type: "educational",
      target_duration: 60,
      visual_style: "shadow_cut",
      transition_style: "crossfade",
      motion_intensity: "medium",
      text_animation: "typewriter",
      creative_brief:
        "Mi Idea — la historia de un taller donde las ideas toman forma. Narrativa cinematográfica: de la idea al producto terminado. Cada corte cuenta una historia de dedicación y pasión.",
    },
  },
  {
    id: "hf-futurista",
    label: "Futurista",
    tag: "TECH",
    icon: Code2,
    gradient: "from-cyan-900 to-blue-700",
    accent: "#67e8f9",
    preview: `${PV}/customers.jpg`,
    pipeline: "hyperframes",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "hyperframes",
      platform: "linkedin",
      angle_type: "educational",
      target_duration: 45,
      visual_style: "data_drift",
      transition_style: "glitch",
      motion_intensity: "energetic",
      text_animation: "typewriter",
      creative_brief:
        "Mi Idea — tecnología láser de precisión milimétrica. Datos, exactitud, innovación. El futuro de la manufactura personalizada ya está aquí. Para ingenieros, diseñadores y makers.",
    },
  },
  {
    id: "hf-emocional",
    label: "Emocional",
    tag: "STORY",
    icon: Heart,
    gradient: "from-rose-700 to-pink-500",
    accent: "#fecdd3",
    preview: `${PV}/mi-idea-product1.jpg`,
    pipeline: "hyperframes",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "hyperframes",
      platform: "instagram",
      angle_type: "educational",
      target_duration: 60,
      visual_style: "soft_signal",
      transition_style: "crossfade",
      motion_intensity: "calm",
      text_animation: "typewriter",
      creative_brief:
        "Mi Idea — detrás de cada pieza hay una historia. Conectamos emprendedores con sus sueños a través del diseño. Cada cliente que confía en nosotros nos inspira a crear mejor.",
    },
  },
] as const;

const UGC_EXAMPLES = [
  {
    id: "ugc-clientes-ventas",
    label: "Clientes — Ventas",
    tag: "UGC",
    desc: "Foto de clientes como hook de ventas",
    preview: `${PV}/customers.jpg`,
    photoPath: `${CP}/customers.jpg`,
    angleLabel: "Ventas directas",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "ugc",
      platform: "tiktok",
      angle_type: "sales",
      target_duration: 60,
      visual_style: "shadow_cut",
      transition_style: "crossfade",
      motion_intensity: "medium",
      text_animation: "slide",
      user_photo_path: `${CP}/customers.jpg`,
      creative_brief:
        "Video de ventas con foto de clientes satisfechos. Testimonial implícito, mostrando el resultado final del servicio de corte láser Mi Idea.",
    },
  },
  {
    id: "ugc-producto-educacional",
    label: "Producto — Educacional",
    tag: "UGC",
    desc: "Foto de producto para explicar el proceso",
    preview: `${PV}/mi-idea-product1.jpg`,
    photoPath: `${CP}/mi-idea-product1.jpg`,
    angleLabel: "Educacional",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "ugc",
      platform: "instagram",
      angle_type: "educational",
      target_duration: 60,
      visual_style: "swiss_pulse",
      transition_style: "crossfade",
      motion_intensity: "calm",
      text_animation: "slide",
      user_photo_path: `${CP}/mi-idea-product1.jpg`,
      creative_brief:
        "Video educacional mostrando el producto terminado de corte láser. Explicar el proceso, materiales usados, aplicaciones posibles.",
    },
  },
  {
    id: "ugc-producto2-trending",
    label: "Producto — Trending",
    tag: "UGC",
    desc: "Segundo producto para contenido viral",
    preview: `${PV}/mi-idea-product2.jpg`,
    photoPath: `${CP}/mi-idea-product2.jpg`,
    angleLabel: "Trending",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "ugc",
      platform: "tiktok",
      angle_type: "trending",
      target_duration: 30,
      visual_style: "maximalist_type",
      transition_style: "flash",
      motion_intensity: "energetic",
      text_animation: "scale",
      user_photo_path: `${CP}/mi-idea-product2.jpg`,
      creative_brief:
        "Reel trending con producto de corte láser. Hook en los primeros 2 segundos. Estilo viral, ritmo dinámico, must-have para makers.",
    },
  },
  {
    id: "ugc-clientes2-competencia",
    label: "Clientes — ¿Por qué nosotros?",
    tag: "UGC",
    desc: "Diferenciación vs competencia",
    preview: `${PV}/customers2.jpg`,
    photoPath: `${CP}/customers2.jpg`,
    angleLabel: "Diferenciación",
    config: {
      brand_slug: "mi-idea",
      pipeline_type: "ugc",
      platform: "instagram",
      angle_type: "competitor",
      target_duration: 60,
      visual_style: "soft_signal",
      transition_style: "wipe_left",
      motion_intensity: "medium",
      text_animation: "typewriter",
      user_photo_path: `${CP}/customers2.jpg`,
      creative_brief:
        "Video de diferenciación: ¿Por qué elegir Mi Idea? Calidad superior, tiempo de entrega, personalización total, atención al cliente. Somos la opción premium en corte láser.",
    },
  },
] as const;

// ── Step labels ───────────────────────────────────────────────────────────────

const STEP_LABELS: Record<string, string> = {
  brand_load:          "Cargar marca",
  script_generate:     "Generar guión",
  image_generate:      "Generar imágenes",
  image_enhance:       "Mejorar imágenes",
  photo_analyze:       "Analizar foto",
  voice_generate:      "Generar voz",
  video_generate:      "Generar video (Kling)",
  whisper_transcribe:  "Transcribir audio",
  hyperframes_compose: "Componer animación",
  hyperframes_render:  "Renderizar video",
  subtitle_generate:   "Generar subtítulos",
  video_assemble:      "Ensamblar video",
  subtitle_burn:       "Quemar subtítulos",
};

// ── Generation panel (reused from Studio) ────────────────────────────────────

function buildStepList(events: PipelineEvent[]) {
  const map = new Map<string, { name: string; status: string; message: string }>();
  for (const ev of events) {
    if (!ev.step_name) continue;
    const n = ev.step_name;
    if (ev.event_type === "step_start")    map.set(n, { name: n, status: "running",   message: ev.message });
    if (ev.event_type === "step_complete") map.set(n, { name: n, status: "completed", message: ev.message });
    if (ev.event_type === "step_error")    map.set(n, { name: n, status: "failed",    message: ev.message });
    if (ev.event_type === "step_paused")   map.set(n, { name: n, status: "paused",    message: ev.message });
  }
  return Array.from(map.values());
}

// ── Main component ────────────────────────────────────────────────────────────

export default function GalleryPage() {
  const [runId, setRunId]           = useState<string | null>(null);
  const [activeId, setActiveId]     = useState<string | null>(null);
  const [activeLabel, setActiveLabel] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError]     = useState("");
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);
  const panelRef                    = useRef<HTMLDivElement>(null);

  const { events, status } = useSSE(runId);

  // Fetch video when pipeline completes
  useEffect(() => {
    if (status !== "completed" || !runId) return;
    api.getRunOutputs(runId)
      .then((outputs) => {
        const vid = outputs.find((o: { asset_type: string; id: number }) => o.asset_type === "video");
        if (vid) setFinalVideoUrl(api.getFileUrl(vid.id));
      })
      .catch(() => {});
  }, [status, runId]);

  // Scroll to panel when generation starts
  useEffect(() => {
    if (runId) {
      setTimeout(() => panelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    }
  }, [runId]);

  async function handleGenerate(id: string, label: string, config: Record<string, unknown>) {
    if (generating) return;
    setGenerating(true);
    setGenError("");
    setFinalVideoUrl(null);
    setActiveId(id);
    setActiveLabel(label);
    setRunId(null);

    try {
      const res = await api.runPipeline({ ...config, mode: "headless" });
      setRunId(res.run_id);
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Error al lanzar el pipeline");
    } finally {
      setGenerating(false);
    }
  }

  function handleReset() {
    setRunId(null);
    setActiveId(null);
    setFinalVideoUrl(null);
    setGenError("");
  }

  const steps = buildStepList(events);
  const lastProgress = [...events].reverse().find(e => ["progress", "log"].includes(e.event_type));
  const isActive = !!runId;

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="p-6 space-y-10 max-w-7xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link href="/" className="text-slate-400 hover:text-slate-600 transition-colors">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <h1 className="text-3xl font-bold text-slate-900">Galería de Ejemplos</h1>
          </div>
          <p className="text-slate-500 text-sm">
            Genera videos profesionales con los assets reales de <span className="font-semibold text-orange-600">Mi Idea</span> — corte láser y diseño.
            Un clic para lanzar cada pipeline.
          </p>
        </div>
        <Link href="/studio"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-sm font-semibold transition-all">
          <Sparkles className="h-4 w-4" />
          Video Studio
        </Link>
      </div>

      {/* ── SECTION 1 — HyperFrames templates ── */}
      <section>
        <div className="flex items-center gap-3 mb-5">
          <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center shrink-0">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">HyperFrames — 8 plantillas</h2>
            <p className="text-xs text-slate-500">Animación GSAP + HTML renderizado por Puppeteer · máxima calidad visual</p>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4">
          {HF_EXAMPLES.map((ex) => {
            const Icon = ex.icon;
            const isThisActive = activeId === ex.id && isActive;
            return (
              <div key={ex.id}
                className={cn("rounded-2xl overflow-hidden border transition-all",
                  isThisActive ? "ring-2 ring-violet-500 shadow-xl" : "ring-1 ring-slate-200 hover:shadow-md"
                )}
              >
                {/* Gradient header with photo */}
                <div className={cn("relative h-36 bg-gradient-to-br", ex.gradient)}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={ex.preview} alt={ex.label}
                    className="absolute inset-0 w-full h-full object-cover opacity-30 mix-blend-luminosity" />
                  <div className="absolute inset-0 flex flex-col justify-between p-3">
                    <div className="flex items-start justify-between">
                      <span className="text-xs font-bold font-mono tracking-widest text-white/70">{ex.tag}</span>
                      {isThisActive && (
                        <span className="flex items-center gap-1 bg-violet-600 text-white text-xs px-2 py-0.5 rounded-full font-semibold">
                          <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                          generando
                        </span>
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5 mb-1">
                        <Icon className="h-4 w-4 text-white" />
                        <p className="text-base font-bold text-white">{ex.label}</p>
                      </div>
                      <p className="text-xs text-white/60">{ex.config.visual_style} · {ex.config.motion_intensity}</p>
                    </div>
                  </div>
                </div>

                {/* Card body */}
                <div className="bg-white p-3 space-y-2.5">
                  {/* Params chips */}
                  <div className="flex flex-wrap gap-1">
                    {[ex.config.transition_style, ex.config.text_animation, `${ex.config.target_duration}s`].map(v => (
                      <span key={v} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">{v}</span>
                    ))}
                    <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full">mi-idea</span>
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleGenerate(ex.id, ex.label, ex.config)}
                      disabled={generating || isThisActive}
                      className={cn(
                        "flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-bold transition-all",
                        isThisActive
                          ? "bg-violet-100 text-violet-600 cursor-default"
                          : generating
                          ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                          : "bg-violet-600 hover:bg-violet-700 text-white"
                      )}
                    >
                      {isThisActive
                        ? <><Loader2 className="h-3 w-3 animate-spin" /> Generando…</>
                        : <><Play className="h-3 w-3" /> Generar</>
                      }
                    </button>
                    <Link
                      href={`/studio?template=${ex.id}`}
                      className="px-2.5 py-2 rounded-lg border border-slate-200 text-slate-500 hover:border-violet-300 hover:text-violet-600 transition-all"
                      title="Personalizar en Studio"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── SECTION 2 — UGC con foto ── */}
      <section>
        <div className="flex items-center gap-3 mb-5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shrink-0">
            <Camera className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">UGC con foto real — 4 ángulos</h2>
            <p className="text-xs text-slate-500">Foto existente → Kling animation → voz TTS → video con subtítulos</p>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4">
          {UGC_EXAMPLES.map((ex) => {
            const isThisActive = activeId === ex.id && isActive;
            return (
              <div key={ex.id}
                className={cn("rounded-2xl overflow-hidden border transition-all",
                  isThisActive ? "ring-2 ring-blue-500 shadow-xl" : "ring-1 ring-slate-200 hover:shadow-md"
                )}
              >
                {/* Photo header */}
                <div className="relative h-40 bg-slate-200 overflow-hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={ex.preview} alt={ex.label}
                    className="w-full h-full object-cover" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                  <div className="absolute bottom-0 left-0 right-0 p-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-bold text-white leading-tight">{ex.label}</p>
                      {isThisActive && (
                        <span className="flex items-center gap-1 bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full font-semibold">
                          <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                          generando
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-white/70 mt-0.5">{ex.desc}</p>
                  </div>
                  <div className="absolute top-2 right-2">
                    <span className="text-xs font-bold bg-blue-600 text-white px-2 py-0.5 rounded-full">{ex.tag}</span>
                  </div>
                </div>

                {/* Card body */}
                <div className="bg-white p-3 space-y-2.5">
                  <div className="flex flex-wrap gap-1">
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{ex.angleLabel}</span>
                    <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">{ex.config.platform}</span>
                    <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">{ex.config.target_duration}s</span>
                    <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full">mi-idea</span>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => handleGenerate(ex.id, ex.label, ex.config)}
                      disabled={generating || isThisActive}
                      className={cn(
                        "flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-bold transition-all",
                        isThisActive
                          ? "bg-blue-100 text-blue-600 cursor-default"
                          : generating
                          ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                          : "bg-blue-600 hover:bg-blue-700 text-white"
                      )}
                    >
                      {isThisActive
                        ? <><Loader2 className="h-3 w-3 animate-spin" /> Generando…</>
                        : <><Camera className="h-3 w-3" /> Generar UGC</>
                      }
                    </button>
                    <Link href="/studio"
                      className="px-2.5 py-2 rounded-lg border border-slate-200 text-slate-500 hover:border-blue-300 hover:text-blue-600 transition-all"
                      title="Ir a Studio">
                      <Video className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Generation panel ── */}
      {(isActive || genError) && (
        <div ref={panelRef} className="space-y-4">
          <div className="h-px bg-slate-200" />
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">
              Generando: <span className="text-violet-600">{activeLabel}</span>
            </h2>
            <button onClick={handleReset}
              className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors">
              <RotateCcw className="h-3.5 w-3.5" />
              Resetear
            </button>
          </div>

          {genError && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
              {genError}
            </div>
          )}

          {isActive && (
            <div className="grid grid-cols-2 gap-4">
              {/* Left: step progress */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
                {/* Status banner */}
                <div className={cn("flex items-center gap-3 p-3 rounded-xl",
                  status === "running"   ? "bg-blue-50 border border-blue-200"   :
                  status === "completed" ? "bg-green-50 border border-green-200" :
                  status === "failed"    ? "bg-red-50 border border-red-200"     :
                                           "bg-amber-50 border border-amber-200"
                )}>
                  <div className={cn("w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                    status === "running"   ? "bg-blue-500"   :
                    status === "completed" ? "bg-green-500"  :
                    status === "failed"    ? "bg-red-500"    : "bg-amber-500"
                  )}>
                    {status === "running"   && <Loader2      className="h-4 w-4 text-white animate-spin" />}
                    {status === "completed" && <CheckCircle2 className="h-4 w-4 text-white" />}
                    {status === "paused"    && <Pause        className="h-4 w-4 text-white" />}
                    {status === "failed"    && <XCircle      className="h-4 w-4 text-white" />}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800">
                      {status === "running"   && "Generando…"}
                      {status === "completed" && "¡Completado!"}
                      {status === "paused"    && "En pausa"}
                      {status === "failed"    && "Error"}
                    </p>
                    {lastProgress && status === "running" && (
                      <p className="text-xs text-slate-500 truncate">{lastProgress.message}</p>
                    )}
                    <p className="text-xs text-slate-400 font-mono">{runId?.slice(0, 16)}…</p>
                  </div>
                </div>

                {/* Steps */}
                {steps.length === 0
                  ? <p className="text-sm text-slate-400 flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Iniciando pipeline…</p>
                  : <div className="space-y-2.5">
                      {steps.map((step, i) => (
                        <div key={step.name} className="flex items-start gap-2.5">
                          <div className="flex flex-col items-center shrink-0">
                            <div className={cn("w-6 h-6 rounded-full flex items-center justify-center",
                              step.status === "completed" ? "bg-green-100" :
                              step.status === "running"   ? "bg-blue-100"  :
                              step.status === "failed"    ? "bg-red-100"   : "bg-slate-100"
                            )}>
                              {step.status === "completed" && <Check   className="h-3 w-3 text-green-600" />}
                              {step.status === "running"   && <Loader2 className="h-3 w-3 text-blue-600 animate-spin" />}
                              {step.status === "failed"    && <XCircle className="h-3 w-3 text-red-600" />}
                            </div>
                            {i < steps.length - 1 && <div className={cn("w-px h-3 mt-1", step.status === "completed" ? "bg-green-200" : "bg-slate-100")} />}
                          </div>
                          <div className="flex-1 min-w-0 pt-0.5">
                            <p className={cn("text-xs font-semibold",
                              step.status === "completed" ? "text-green-700" :
                              step.status === "running"   ? "text-blue-700"  :
                              step.status === "failed"    ? "text-red-700"   : "text-slate-400"
                            )}>
                              {STEP_LABELS[step.name] || step.name}
                            </p>
                            {step.message && <p className="text-xs text-slate-400 truncate">{step.message}</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                }

                {/* Actions */}
                {status === "completed" && (
                  <div className="flex gap-2 pt-1">
                    <Link href={`/pipelines/${runId}`}
                      className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-all">
                      <ExternalLink className="h-3 w-3" /> Monitor
                    </Link>
                    <Link href="/outputs"
                      className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-all">
                      <ExternalLink className="h-3 w-3" /> Outputs
                    </Link>
                  </div>
                )}
              </div>

              {/* Right: video player or event log */}
              {status === "completed" && finalVideoUrl ? (
                <div className="rounded-xl overflow-hidden border border-slate-200 bg-black flex flex-col">
                  <video src={finalVideoUrl} controls autoPlay className="flex-1 object-contain max-h-72" />
                  <div className="bg-slate-900 px-3 py-2 flex items-center gap-2">
                    <a href={finalVideoUrl} download
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-xs font-bold transition-all">
                      <Download className="h-3.5 w-3.5" /> Descargar
                    </a>
                    <p className="text-xs text-slate-500 font-mono truncate">{runId?.slice(0, 12)}…</p>
                  </div>
                </div>
              ) : (
                <div className="bg-slate-900 rounded-xl p-4">
                  <p className="text-xs font-mono text-slate-500 uppercase tracking-wide mb-3">Log en vivo</p>
                  <div className="space-y-1 max-h-60 overflow-y-auto">
                    {events.length === 0
                      ? <p className="text-slate-500 text-xs">Esperando eventos…</p>
                      : [...events].reverse().slice(0, 20).map((ev, i) => (
                          <div key={i} className="flex gap-2 text-xs font-mono">
                            <span className="text-slate-600 shrink-0">{new Date(ev.timestamp).toLocaleTimeString("es")}</span>
                            <span className={cn("shrink-0",
                              ev.event_type === "step_complete" ? "text-green-400" :
                              ev.event_type === "step_start"    ? "text-blue-400"  :
                              ev.event_type.includes("error") || ev.event_type.includes("failed") ? "text-red-400" : "text-slate-500"
                            )}>{ev.event_type}</span>
                            <span className="text-slate-400 truncate">{ev.message}</span>
                          </div>
                        ))
                    }
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

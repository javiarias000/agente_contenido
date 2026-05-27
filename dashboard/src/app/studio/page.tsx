"use client";

import React, { useState, useRef, useEffect, DragEvent } from "react";
import Link from "next/link";
import useSWR from "swr";
import { api } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import type { PipelineEvent } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Send, Wand2, Sparkles, Film, Zap, Heart, Minimize2,
  TrendingUp, Star, Clapperboard, Code2, X, Loader2,
  Play, ImagePlus, Upload, ChevronRight, Check, Info,
  CheckCircle2, XCircle, Download, RotateCcw, ExternalLink,
  Clock, ArrowLeft, Pause,
} from "lucide-react";

// ── Templates ────────────────────────────────────────────────────────────────

const TEMPLATES = [
  {
    id: "minimalista",    label: "Minimalista",      icon: Minimize2,    gradient: "from-slate-800 to-slate-600",  ring: "ring-slate-400",   tag: "CLEAN",  desc: "Limpio, elegante, sin ruido",
    config: { visual_style: "swiss_pulse",     transition_style: "crossfade", motion_intensity: "calm",      text_animation: "slide",       pipeline_type: "hyperframes", creative_brief: "Estilo minimalista y elegante. Espacio en blanco, tipografía precisa, colores neutros. Menos es más." },
  },
  {
    id: "marketero",      label: "Marketero",        icon: TrendingUp,   gradient: "from-orange-600 to-red-500",   ring: "ring-orange-400",  tag: "SALES",  desc: "Alto impacto, ventas, conversión",
    config: { visual_style: "maximalist_type", transition_style: "flash",     motion_intensity: "energetic", text_animation: "scale",       pipeline_type: "hyperframes", creative_brief: "Video de alto impacto para ventas. Call-to-action potente, urgencia real, beneficios claros. Diseñado para convertir en los primeros 3 segundos." },
  },
  {
    id: "simple",         label: "Simple",           icon: Film,         gradient: "from-blue-600 to-blue-400",    ring: "ring-blue-400",    tag: "CLEAR",  desc: "Directo al punto, fácil de entender",
    config: { visual_style: "soft_signal",     transition_style: "crossfade", motion_intensity: "calm",      text_animation: "slide",       pipeline_type: "ugc",         creative_brief: "Comunicación directa y simple. Sin distracciones, mensaje en primer plano." },
  },
  {
    id: "emocionante",    label: "Emocionante",      icon: Zap,          gradient: "from-purple-700 to-pink-500",  ring: "ring-purple-400",  tag: "ENERGY", desc: "Adrenalina, ritmo, impacto",
    config: { visual_style: "shadow_cut",      transition_style: "glitch",    motion_intensity: "energetic", text_animation: "split",       pipeline_type: "hyperframes", creative_brief: "Energía máxima. Cortes rápidos, impacto visual inmediato, ritmo alto." },
  },
  {
    id: "elegante",       label: "Elegante",         icon: Star,         gradient: "from-amber-800 to-yellow-600", ring: "ring-amber-400",   tag: "LUXURY", desc: "Lujo, premium, sofisticación",
    config: { visual_style: "velvet_standard", transition_style: "wipe_left", motion_intensity: "medium",    text_animation: "split",       pipeline_type: "hyperframes", creative_brief: "Atmósfera de lujo y exclusividad. Paleta oscura con dorados. Movimiento lento y deliberado." },
  },
  {
    id: "cinematografico",label: "Cinematográfico",  icon: Clapperboard, gradient: "from-gray-900 to-gray-600",    ring: "ring-gray-400",    tag: "CINEMA", desc: "Narrativa de cine, drama visual",
    config: { visual_style: "shadow_cut",      transition_style: "crossfade", motion_intensity: "medium",    text_animation: "typewriter",  pipeline_type: "hyperframes", creative_brief: "Narrativa cinematográfica profunda. Ritmo pausado, dramático. Texto como revelación." },
  },
  {
    id: "futurista",      label: "Futurista",        icon: Code2,        gradient: "from-cyan-900 to-blue-700",    ring: "ring-cyan-400",    tag: "TECH",   desc: "Tech, AI, innovación digital",
    config: { visual_style: "data_drift",      transition_style: "glitch",    motion_intensity: "energetic", text_animation: "typewriter",  pipeline_type: "hyperframes", creative_brief: "Estética futurista de datos y código. Neon sobre oscuro." },
  },
  {
    id: "emocional",      label: "Emocional",        icon: Heart,        gradient: "from-rose-700 to-pink-500",    ring: "ring-rose-400",    tag: "STORY",  desc: "Storytelling, conexión, propósito",
    config: { visual_style: "soft_signal",     transition_style: "crossfade", motion_intensity: "calm",      text_animation: "typewriter",  pipeline_type: "hyperframes", creative_brief: "Historia emotiva que conecta. Calidez, autenticidad, propósito compartido." },
  },
] as const;

const VISUAL_STYLES = [
  { value: "swiss_pulse",      label: "Swiss Pulse",  sub: "SaaS · Grids · Inter",         dot: "#3b82f6" },
  { value: "velvet_standard",  label: "Velvet",        sub: "Luxury · Gold · Garamond",      dot: "#d97706" },
  { value: "maximalist_type",  label: "Maximalist",   sub: "Bold · Kinetic · Bebas",         dot: "#ef4444" },
  { value: "data_drift",       label: "Data Drift",   sub: "Neon · Futuristic · Tech",       dot: "#06b6d4" },
  { value: "soft_signal",      label: "Soft Signal",  sub: "Warm · Intimate · Serif",        dot: "#f59e0b" },
  { value: "shadow_cut",       label: "Shadow Cut",   sub: "Dark · Cinematic · Barlow",      dot: "#8b5cf6" },
] as const;

const TRANSITIONS  = [ { value: "crossfade",  label: "Crossfade",   desc: "Smooth dissolve" }, { value: "flash",      label: "Flash",       desc: "Camera snap"  }, { value: "zoom_punch", label: "Zoom Punch",  desc: "Scale impact"  }, { value: "wipe_left",  label: "Wipe Left",   desc: "Horizontal sweep" }, { value: "glitch",     label: "Glitch",      desc: "Digital distortion" } ] as const;
const MOTION       = [ { value: "calm",       label: "Calm",        desc: "Slow, elegant"  }, { value: "medium",     label: "Medium",      desc: "Balanced"      }, { value: "energetic",  label: "Energetic",   desc: "Fast, dynamic" } ] as const;
const TEXT_ANIM    = [ { value: "slide",      label: "Slide",       desc: "Enter from below" }, { value: "scale",    label: "Scale",       desc: "Pop reveal"    }, { value: "split",      label: "Split",       desc: "Word by word"  }, { value: "typewriter", label: "Typewriter",  desc: "Letter by letter" } ] as const;

const QUICK_PROMPTS = [
  "Quiero un video minimalista para mi marca de ropa",
  "Algo energético para vender mi producto en 30 segundos",
  "Video cinematográfico que cuente la historia de mi empresa",
];

const STEP_LABELS: Record<string, string> = {
  brand_load:           "Cargar Marca",
  script_generate:      "Generar Guión",
  image_generate:       "Generar Imágenes",
  image_enhance:        "Mejorar Imágenes",
  photo_analyze:        "Analizar Foto",
  voice_generate:       "Generar Voz",
  video_generate:       "Generar Video (Kling)",
  whisper_transcribe:   "Transcribir Audio",
  hyperframes_compose:  "Componer Animación",
  hyperframes_render:   "Renderizar Video",
  subtitle_generate:    "Generar Subtítulos",
  video_assemble:       "Ensamblar Video",
  subtitle_burn:        "Quemar Subtítulos",
  generate_ads:         "Generar Anuncios",
  lip_sync:             "Sincronizar Labios",
};

// ── Types ─────────────────────────────────────────────────────────────────────

interface ChatMsg    { role: "user" | "assistant"; content: string; loading?: boolean; }
interface MediaItem  { id: string; file: File; preview: string; type: "image" | "video"; uploading?: boolean; path?: string; url?: string; error?: string; }
interface StudioConfig {
  brand_slug: string; pipeline_type: string; platform: string;
  angle_type: string; target_duration: number; visual_style: string;
  transition_style: string; motion_intensity: string; text_animation: string;
  creative_brief: string;
}

const DEFAULT_CONFIG: StudioConfig = {
  brand_slug: "", pipeline_type: "hyperframes", platform: "tiktok", angle_type: "sales",
  target_duration: 60, visual_style: "swiss_pulse", transition_style: "crossfade",
  motion_intensity: "medium", text_animation: "slide", creative_brief: "",
};

// ── Small shared components ───────────────────────────────────────────────────

function Select({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void;
  options: readonly { value: string; label: string }[];
}) {
  return (
    <div>
      <label className="text-xs font-medium text-slate-500 block mb-1">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-300">
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

// ── Generation panel (inline SSE monitor) ────────────────────────────────────

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

interface GenPanelProps {
  runId: string;
  events: PipelineEvent[];
  status: string;
  config: StudioConfig;
  finalVideoUrl: string | null;
  onCreateAnother: () => void;
}

function GenerationPanel({ runId, events, status, config, finalVideoUrl, onCreateAnother }: GenPanelProps) {
  const steps = buildStepList(events);
  const lastProgress = [...events].reverse().find(e => ["progress", "log"].includes(e.event_type));

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="max-w-3xl mx-auto px-6 py-6 space-y-5">

        {/* ── Status header ── */}
        <div className={cn(
          "rounded-2xl p-5 flex items-center gap-4",
          status === "running"   ? "bg-blue-50 border border-blue-200" :
          status === "completed" ? "bg-green-50 border border-green-200" :
          status === "paused"    ? "bg-amber-50 border border-amber-200" :
                                   "bg-red-50 border border-red-200"
        )}>
          <div className={cn(
            "w-12 h-12 rounded-full flex items-center justify-center shrink-0",
            status === "running"   ? "bg-blue-600"   :
            status === "completed" ? "bg-green-600"  :
            status === "paused"    ? "bg-amber-500"  : "bg-red-600"
          )}>
            {status === "running"   && <Loader2   className="h-6 w-6 text-white animate-spin" />}
            {status === "completed" && <CheckCircle2 className="h-6 w-6 text-white" />}
            {status === "paused"    && <Pause     className="h-6 w-6 text-white" />}
            {status === "failed"    && <XCircle   className="h-6 w-6 text-white" />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-bold text-lg text-slate-900">
              {status === "running"   && "Generando tu video…"}
              {status === "completed" && "¡Video completado!"}
              {status === "paused"    && "Esperando revisión…"}
              {status === "failed"    && "Error en la generación"}
            </p>
            {lastProgress && status === "running" && (
              <p className="text-sm text-slate-600 truncate mt-0.5">{lastProgress.message}</p>
            )}
            <p className="text-xs text-slate-400 font-mono mt-1">{runId.slice(0, 16)}… · {config.pipeline_type} · {config.brand_slug || "—"}</p>
          </div>
        </div>

        {/* ── Step progress ── */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Pasos del pipeline</p>
          {steps.length === 0 ? (
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Iniciando pipeline…</span>
            </div>
          ) : (
            <div className="space-y-3">
              {steps.map((step, i) => (
                <div key={step.name} className="flex items-start gap-3">
                  <div className="flex flex-col items-center shrink-0">
                    <div className={cn(
                      "w-7 h-7 rounded-full flex items-center justify-center",
                      step.status === "completed" ? "bg-green-100" :
                      step.status === "running"   ? "bg-blue-100"  :
                      step.status === "failed"    ? "bg-red-100"   :
                      step.status === "paused"    ? "bg-amber-100" : "bg-slate-100"
                    )}>
                      {step.status === "completed" && <Check    className="h-3.5 w-3.5 text-green-600" />}
                      {step.status === "running"   && <Loader2  className="h-3.5 w-3.5 text-blue-600 animate-spin" />}
                      {step.status === "failed"    && <XCircle  className="h-3.5 w-3.5 text-red-600"   />}
                      {step.status === "paused"    && <Pause    className="h-3.5 w-3.5 text-amber-600" />}
                    </div>
                    {i < steps.length - 1 && (
                      <div className={cn("w-0.5 h-4 mt-1", step.status === "completed" ? "bg-green-200" : "bg-slate-100")} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0 pt-1">
                    <p className={cn("text-sm font-medium",
                      step.status === "completed" ? "text-green-700" :
                      step.status === "running"   ? "text-blue-700"  :
                      step.status === "failed"    ? "text-red-700"   :
                      step.status === "paused"    ? "text-amber-700" : "text-slate-400"
                    )}>
                      {STEP_LABELS[step.name] || step.name}
                    </p>
                    {step.message && (
                      <p className="text-xs text-slate-400 truncate">{step.message}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Video player (when completed) ── */}
        {status === "completed" && finalVideoUrl && (
          <div className="rounded-xl overflow-hidden border border-slate-200 bg-black">
            <video
              src={finalVideoUrl}
              controls
              autoPlay
              className="w-full max-h-[480px] object-contain"
            />
          </div>
        )}

        {/* ── Actions ── */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={onCreateAnother}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 text-sm font-semibold hover:bg-slate-50 transition-all"
          >
            <ArrowLeft className="h-4 w-4" />
            Crear otro video
          </button>

          {status === "completed" && finalVideoUrl && (
            <a
              href={finalVideoUrl}
              download
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-sm font-semibold transition-all"
            >
              <Download className="h-4 w-4" />
              Descargar video
            </a>
          )}

          {status === "completed" && (
            <Link
              href="/outputs"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 text-sm font-semibold hover:bg-slate-50 transition-all"
            >
              <ExternalLink className="h-4 w-4" />
              Ver en Outputs
            </Link>
          )}

          <Link
            href={`/pipelines/${runId}`}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-500 text-sm font-medium hover:bg-slate-50 transition-all"
          >
            Monitor completo
            <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {/* ── Event log ── */}
        {events.length > 0 && (
          <div className="bg-slate-900 rounded-xl p-4">
            <p className="text-xs font-mono text-slate-500 mb-3 uppercase tracking-wide">Log de eventos</p>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {[...events].reverse().slice(0, 20).map((ev, i) => (
                <div key={i} className="flex gap-3 text-xs font-mono">
                  <span className="text-slate-600 shrink-0 min-w-[60px]">
                    {new Date(ev.timestamp).toLocaleTimeString("es")}
                  </span>
                  <span className={cn("shrink-0 min-w-[120px]",
                    ev.event_type === "step_complete"   ? "text-green-400" :
                    ev.event_type === "step_start"      ? "text-blue-400"  :
                    ev.event_type.includes("error") || ev.event_type.includes("failed") ? "text-red-400" :
                    ev.event_type === "step_paused"     ? "text-amber-400" : "text-slate-500"
                  )}>
                    {ev.event_type}
                  </span>
                  <span className="text-slate-400 truncate">{ev.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Studio component ─────────────────────────────────────────────────────

export default function StudioPage() {
  const { data: brands }      = useSWR("brands", api.listBrands);
  const { data: recentRuns }  = useSWR("runs",   api.listRuns, { refreshInterval: 8000 });

  // Config
  const [config, setConfig]             = useState<StudioConfig>(DEFAULT_CONFIG);
  const [activeTemplate, setActiveTemplate] = useState<string | null>(null);
  const updateConfig = (patch: Partial<StudioConfig>) => setConfig((p) => ({ ...p, ...patch }));

  // Media
  const [mediaItems, setMediaItems]   = useState<MediaItem[]>([]);
  const [isDragging, setIsDragging]   = useState(false);
  const fileInputRef                  = useRef<HTMLInputElement>(null);

  // Chat
  const [messages, setMessages]       = useState<ChatMsg[]>([{
    role: "assistant",
    content: "¡Hola! Soy tu asistente de video. Cuéntame qué tipo de video necesitas — para qué marca, qué quieres transmitir, y a quién va dirigido. 🎬",
  }]);
  const [inputText, setInputText]     = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const messagesEndRef                = useRef<HTMLDivElement>(null);

  // Generation
  const [runId, setRunId]             = useState<string | null>(null);
  const [generating, setGenerating]   = useState(false);
  const [genError, setGenError]       = useState("");
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);

  // SSE — connects only when runId is set
  const { events, status, pausedEvent } = useSSE(runId);

  // Fetch video output when pipeline completes
  useEffect(() => {
    if (status !== "completed" || !runId) return;
    api.getRunOutputs(runId)
      .then((outputs) => {
        const vid = outputs.find((o: { asset_type: string; id: number }) => o.asset_type === "video");
        if (vid) setFinalVideoUrl(api.getFileUrl(vid.id));
      })
      .catch(() => {});
  }, [status, runId]);

  // Scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Recent studio runs
  const studioRuns = (recentRuns || [])
    .filter((r: { pipeline_type: string }) => ["hyperframes", "ugc"].includes(r.pipeline_type))
    .slice(0, 5);

  // ── Template ──────────────────────────────────────────────────────────────
  function applyTemplate(t: (typeof TEMPLATES)[number]) {
    setActiveTemplate(t.id);
    updateConfig(t.config as Partial<StudioConfig>);
  }

  // ── Media upload ──────────────────────────────────────────────────────────
  async function addFiles(files: FileList | File[]) {
    const arr = Array.from(files);
    const newItems: MediaItem[] = arr.map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      file, preview: URL.createObjectURL(file),
      type: file.type.startsWith("video/") ? "video" : "image",
      uploading: true,
    }));
    setMediaItems((p) => [...p, ...newItems]);
    for (const item of newItems) {
      try {
        const result = await api.uploadMedia(item.file);
        setMediaItems((p) => p.map((m) => m.id === item.id ? { ...m, uploading: false, path: result.path, url: result.url } : m));
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Error al subir";
        setMediaItems((p) => p.map((m) => m.id === item.id ? { ...m, uploading: false, error: msg } : m));
      }
    }
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault(); setIsDragging(false);
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  }

  function removeMedia(id: string) {
    setMediaItems((p) => { const i = p.find((m) => m.id === id); if (i) URL.revokeObjectURL(i.preview); return p.filter((m) => m.id !== id); });
  }

  // ── Chat ──────────────────────────────────────────────────────────────────
  async function sendMessage(text: string) {
    if (!text.trim() || chatLoading) return;
    const userMsg: ChatMsg = { role: "user", content: text.trim() };
    setMessages((p) => [...p, userMsg, { role: "assistant", content: "", loading: true }]);
    setInputText("");
    setChatLoading(true);
    try {
      const history = [...messages, userMsg].filter((m) => !m.loading).map((m) => ({ role: m.role, content: m.content }));
      const res = await api.chatMessage(history, config);
      setMessages((p) => [...p.filter((m) => !m.loading), { role: "assistant", content: res.message }]);
      if (res.config_update) {
        updateConfig(res.config_update as Partial<StudioConfig>);
        if (res.config_update.visual_style) setActiveTemplate(null);
      }
    } catch {
      setMessages((p) => [...p.filter((m) => !m.loading), { role: "assistant", content: "Ocurrió un error. Por favor intenta de nuevo." }]);
    } finally { setChatLoading(false); }
  }

  // ── Generate ──────────────────────────────────────────────────────────────
  async function handleGenerate() {
    if (!config.brand_slug) { setGenError("Selecciona una marca antes de generar"); return; }
    setGenError(""); setGenerating(true); setFinalVideoUrl(null);
    try {
      const uploadedPhoto = mediaItems.find((m) => m.type === "image" && m.path);
      const payload: Record<string, unknown> = {
        ...config, mode: "headless",
        ...(uploadedPhoto ? { user_photo_path: uploadedPhoto.path } : {}),
      };
      const res = await api.runPipeline(payload);
      setRunId(res.run_id);
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Error al generar");
    } finally { setGenerating(false); }
  }

  function handleCreateAnother() {
    setRunId(null); setFinalVideoUrl(null);
  }

  // ── Status badge in header when generating ────────────────────────────────
  const isGenerating = !!runId;

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* ── Header ── */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center">
            <Wand2 className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 leading-none">Video Studio</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {isGenerating ? `Pipeline activo · ${runId!.slice(0, 8)}…` : "Diseña y genera tu video profesional con IA"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {genError && !isGenerating && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-1.5 rounded-lg border border-red-200">{genError}</p>
          )}

          {isGenerating ? (
            <div className="flex items-center gap-3">
              <span className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold",
                status === "running"   ? "bg-blue-100 text-blue-700"   :
                status === "completed" ? "bg-green-100 text-green-700" :
                status === "failed"    ? "bg-red-100 text-red-700"     : "bg-amber-100 text-amber-700"
              )}>
                {status === "running" && <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />}
                {status === "completed" && <Check className="h-3 w-3" />}
                {status}
              </span>
              <button
                onClick={handleCreateAnother}
                className="flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 bg-white text-slate-700 text-sm font-semibold hover:bg-slate-50 transition-all"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Crear otro
              </button>
            </div>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={generating || !config.brand_slug}
              className={cn(
                "flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all",
                config.brand_slug
                  ? "bg-violet-600 hover:bg-violet-700 text-white shadow-md shadow-violet-200"
                  : "bg-slate-200 text-slate-400 cursor-not-allowed"
              )}
            >
              {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {generating ? "Iniciando…" : "Generar Video"}
            </button>
          )}
        </div>
      </header>

      {/* ── Body ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Left: AI Chat ── */}
        <aside className="w-96 shrink-0 flex flex-col border-r border-slate-200 bg-slate-900">
          <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-violet-600 flex items-center justify-center">
              <Sparkles className="h-3.5 w-3.5 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white leading-none">Asistente de Video</p>
              <p className="text-xs text-slate-400 mt-0.5">Describe tu visión, yo configuro todo</p>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
                <div className={cn(
                  "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                  msg.role === "user"
                    ? "bg-violet-600 text-white rounded-br-sm"
                    : "bg-slate-800 text-slate-100 rounded-bl-sm border border-slate-700"
                )}>
                  {msg.loading
                    ? <span className="flex items-center gap-1.5 text-slate-400"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Pensando…</span>
                    : <span className="whitespace-pre-wrap">{msg.content}</span>
                  }
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="px-4 pb-2">
            <p className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wide">Sugerencias</p>
            <div className="flex flex-col gap-1.5">
              {QUICK_PROMPTS.map((p) => (
                <button key={p} type="button" onClick={() => sendMessage(p)}
                  className="text-left text-xs text-slate-400 hover:text-violet-300 transition-colors flex items-start gap-1.5 group">
                  <ChevronRight className="h-3 w-3 mt-0.5 shrink-0 text-slate-600 group-hover:text-violet-500 transition-colors" />
                  <span className="line-clamp-1">{p}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="p-3 border-t border-slate-700">
            <div className="flex items-end gap-2 bg-slate-800 rounded-xl border border-slate-700 p-2">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(inputText); } }}
                placeholder="Describe tu video…"
                rows={2}
                disabled={chatLoading}
                className="flex-1 bg-transparent resize-none text-sm text-white placeholder-slate-500 focus:outline-none min-h-[44px] max-h-32"
              />
              <button type="button" onClick={() => sendMessage(inputText)} disabled={!inputText.trim() || chatLoading}
                className={cn("p-2 rounded-lg transition-all shrink-0",
                  inputText.trim() && !chatLoading ? "bg-violet-600 text-white hover:bg-violet-700" : "bg-slate-700 text-slate-500 cursor-not-allowed"
                )}>
                <Send className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-slate-600 mt-1.5 text-center">Enter para enviar · Shift+Enter nueva línea</p>
          </div>
        </aside>

        {/* ── Right panel: Studio config OR Generation progress ── */}
        {isGenerating ? (
          <GenerationPanel
            runId={runId!}
            events={events}
            status={status}
            config={config}
            finalVideoUrl={finalVideoUrl}
            onCreateAnother={handleCreateAnother}
          />
        ) : (
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto px-6 py-6 space-y-8">

              {/* ── Templates ── */}
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Plantillas profesionales</h2>
                  <span className="text-xs text-slate-400">Elige un estilo o personaliza abajo</span>
                </div>
                <div className="grid grid-cols-4 gap-3">
                  {TEMPLATES.map((t) => {
                    const Icon = t.icon;
                    const active = activeTemplate === t.id;
                    return (
                      <button key={t.id} type="button" onClick={() => applyTemplate(t)}
                        className={cn("relative rounded-xl overflow-hidden text-left transition-all",
                          active ? `ring-2 ${t.ring} shadow-lg` : "ring-1 ring-slate-200 hover:ring-2 hover:ring-slate-300"
                        )}>
                        <div className={cn("bg-gradient-to-br h-20 flex items-end p-2", t.gradient)}>
                          <span className="text-xs font-bold text-white/60 font-mono tracking-wider">{t.tag}</span>
                          {active && <span className="ml-auto bg-white/20 rounded-full p-0.5"><Check className="h-3 w-3 text-white" /></span>}
                        </div>
                        <div className="bg-white p-2.5">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <Icon className="h-3 w-3 text-slate-500" />
                            <p className="text-xs font-bold text-slate-900">{t.label}</p>
                          </div>
                          <p className="text-xs text-slate-500 leading-tight">{t.desc}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </section>

              {/* ── Media upload ── */}
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Tus archivos</h2>
                  <span className="text-xs text-slate-400">Imágenes y videos (JPG, PNG, MP4, MOV…)</span>
                </div>
                <div
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={cn(
                    "border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all",
                    isDragging ? "border-violet-400 bg-violet-50" : "border-slate-200 bg-white hover:border-violet-300 hover:bg-violet-50/40"
                  )}
                >
                  <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
                    <Upload className="h-5 w-5 text-slate-400" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-semibold text-slate-700">Arrastra archivos aquí <span className="text-violet-600">o haz clic</span></p>
                    <p className="text-xs text-slate-400 mt-1">Imágenes y videos hasta 100 MB</p>
                  </div>
                  <input ref={fileInputRef} type="file" multiple accept="image/*,video/*" onChange={(e) => { if (e.target.files?.length) addFiles(e.target.files); e.target.value = ""; }} className="hidden" />
                </div>

                {mediaItems.length > 0 && (
                  <div className="mt-3 grid grid-cols-6 gap-2">
                    {mediaItems.map((item) => (
                      <div key={item.id} className="relative group aspect-square rounded-lg overflow-hidden bg-slate-100">
                        {item.type === "image"
                          // eslint-disable-next-line @next/next/no-img-element
                          ? <img src={item.preview} alt="" className="w-full h-full object-cover" />
                          : <div className="w-full h-full flex items-center justify-center bg-slate-800"><Play className="h-6 w-6 text-white" /></div>
                        }
                        {item.uploading && <div className="absolute inset-0 bg-black/50 flex items-center justify-center"><Loader2 className="h-4 w-4 text-white animate-spin" /></div>}
                        {item.error   && <div className="absolute inset-0 bg-red-900/70 flex items-center justify-center p-1"><p className="text-white text-xs text-center leading-tight">{item.error}</p></div>}
                        {!item.uploading && <button type="button" onClick={(e) => { e.stopPropagation(); removeMedia(item.id); }} className="absolute top-1 right-1 bg-black/60 hover:bg-black/80 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"><X className="h-3 w-3" /></button>}
                        {item.path && !item.uploading && <div className="absolute bottom-0 left-0 right-0 bg-green-600/90 py-0.5"><p className="text-white text-center" style={{ fontSize: "9px" }}>✓ subido</p></div>}
                      </div>
                    ))}
                    <button type="button" onClick={() => fileInputRef.current?.click()} className="aspect-square rounded-lg border-2 border-dashed border-slate-200 hover:border-violet-300 flex items-center justify-center transition-colors">
                      <ImagePlus className="h-5 w-5 text-slate-300" />
                    </button>
                  </div>
                )}
              </section>

              {/* ── Visual style ── */}
              <section>
                <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">Estilo visual</h2>
                <div className="grid grid-cols-3 gap-2">
                  {VISUAL_STYLES.map((s) => {
                    const active = config.visual_style === s.value;
                    return (
                      <button key={s.value} type="button" onClick={() => { updateConfig({ visual_style: s.value }); setActiveTemplate(null); }}
                        className={cn("flex items-center gap-3 px-3 py-3 rounded-xl border text-left transition-all",
                          active ? "border-violet-400 bg-violet-50 ring-2 ring-violet-300" : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                        )}>
                        <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: s.dot }} />
                        <div>
                          <p className={cn("text-sm font-semibold leading-none", active ? "text-violet-700" : "text-slate-800")}>{s.label}</p>
                          <p className="text-xs text-slate-400 mt-0.5 leading-tight">{s.sub}</p>
                        </div>
                        {active && <Check className="h-4 w-4 text-violet-600 ml-auto shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              </section>

              {/* ── Transitions & motion ── */}
              <section>
                <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">Efectos y animación</h2>
                <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-4">
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Transición</p>
                    <div className="flex flex-wrap gap-2">
                      {TRANSITIONS.map((t) => (
                        <button key={t.value} type="button" onClick={() => updateConfig({ transition_style: t.value })} title={t.desc}
                          className={cn("px-3 py-1.5 rounded-lg border text-xs font-semibold transition-all",
                            config.transition_style === t.value ? "bg-violet-600 text-white border-violet-600" : "bg-white text-slate-600 border-slate-200 hover:border-violet-300"
                          )}>{t.label}</button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Intensidad de movimiento</p>
                    <div className="flex gap-2">
                      {MOTION.map((m) => (
                        <button key={m.value} type="button" onClick={() => updateConfig({ motion_intensity: m.value })} title={m.desc}
                          className={cn("flex-1 py-2 rounded-lg border text-xs font-semibold transition-all text-center",
                            config.motion_intensity === m.value ? "bg-violet-600 text-white border-violet-600" : "bg-white text-slate-600 border-slate-200 hover:border-violet-300"
                          )}>{m.label}</button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Animación de texto</p>
                    <div className="flex gap-2">
                      {TEXT_ANIM.map((a) => (
                        <button key={a.value} type="button" onClick={() => updateConfig({ text_animation: a.value })} title={a.desc}
                          className={cn("flex-1 py-2 rounded-lg border text-xs font-semibold transition-all text-center",
                            config.text_animation === a.value ? "bg-violet-600 text-white border-violet-600" : "bg-white text-slate-600 border-slate-200 hover:border-violet-300"
                          )}>{a.label}</button>
                      ))}
                    </div>
                  </div>
                </div>
              </section>

              {/* ── Pipeline settings ── */}
              <section>
                <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">Configuración del video</h2>
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                      <label className="text-xs font-medium text-slate-500 block mb-1">Marca <span className="text-red-500">*</span></label>
                      <select value={config.brand_slug} onChange={(e) => updateConfig({ brand_slug: e.target.value })}
                        className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-300">
                        <option value="">— Selecciona una marca —</option>
                        {brands?.map((b: { slug: string; name: string }) => <option key={b.slug} value={b.slug}>{b.name}</option>)}
                      </select>
                      {!brands?.length && (
                        <p className="text-xs text-amber-600 mt-1 flex items-center gap-1">
                          <Info className="h-3 w-3" />
                          No hay marcas. <a href="/brands/new" className="underline hover:text-amber-800">Crea una aquí.</a>
                        </p>
                      )}
                    </div>
                    <Select label="Motor de render" value={config.pipeline_type} onChange={(v) => updateConfig({ pipeline_type: v })} options={[{ value: "hyperframes", label: "HyperFrames (máxima calidad)" }, { value: "ugc", label: "UGC Pipeline (redes sociales)" }]} />
                    <Select label="Plataforma" value={config.platform} onChange={(v) => updateConfig({ platform: v })} options={[{ value: "tiktok", label: "TikTok" }, { value: "instagram", label: "Instagram Reels" }, { value: "youtube", label: "YouTube Shorts" }, { value: "linkedin", label: "LinkedIn" }]} />
                    <Select label="Ángulo creativo" value={config.angle_type} onChange={(v) => updateConfig({ angle_type: v })} options={[{ value: "sales", label: "Ventas — Conversión directa" }, { value: "educational", label: "Educacional — Enseña algo" }, { value: "trending", label: "Trending — Viral" }, { value: "competitor", label: "Competencia — Por qué yo" }]} />
                    <Select label="Duración objetivo" value={String(config.target_duration)} onChange={(v) => updateConfig({ target_duration: parseInt(v) })} options={[{ value: "15", label: "15 segundos" }, { value: "30", label: "30 segundos" }, { value: "60", label: "60 segundos" }, { value: "90", label: "90 segundos" }]} />
                  </div>
                  <div className="mt-4">
                    <label className="text-xs font-medium text-slate-500 block mb-1">Brief creativo <span className="text-slate-400 font-normal">(el AI lo usa como contexto clave)</span></label>
                    <textarea value={config.creative_brief} onChange={(e) => updateConfig({ creative_brief: e.target.value })} rows={4}
                      placeholder="Describe el tono, la audiencia, el mensaje principal, qué emociones quieres evocar…"
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-300 resize-none" />
                  </div>
                </div>
              </section>

              {/* ── Config preview ── */}
              <section>
                <div className="bg-slate-800 rounded-xl p-4">
                  <p className="text-xs font-mono text-slate-500 mb-2">// Configuración actual</p>
                  <div className="grid grid-cols-3 gap-x-8 gap-y-1">
                    {[["style", config.visual_style], ["transition", config.transition_style], ["motion", config.motion_intensity], ["text", config.text_animation], ["pipeline", config.pipeline_type], ["platform", config.platform], ["duration", `${config.target_duration}s`], ["brand", config.brand_slug || "—"]].map(([k, v]) => (
                      <div key={k} className="flex items-center gap-2">
                        <span className="text-slate-500 text-xs font-mono">{k}:</span>
                        <span className="text-violet-300 text-xs font-mono font-semibold">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              {/* ── Recent studio runs ── */}
              {studioRuns.length > 0 && (
                <section>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Generaciones recientes</h2>
                    <Link href="/outputs" className="text-xs text-violet-600 hover:text-violet-800 font-medium flex items-center gap-1">
                      Ver todos <ExternalLink className="h-3 w-3" />
                    </Link>
                  </div>
                  <div className="space-y-2">
                    {studioRuns.map((run: { run_id: string; pipeline_type: string; status: string; brand_slug?: string; created_at: string }) => (
                      <Link key={run.run_id} href={`/pipelines/${run.run_id}`}
                        className="flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-3 hover:border-violet-300 hover:shadow-sm transition-all group">
                        <div className="flex items-center gap-3">
                          <div className={cn("w-2 h-2 rounded-full",
                            run.status === "completed" ? "bg-green-500" :
                            run.status === "running"   ? "bg-blue-500 animate-pulse" :
                            run.status === "failed"    ? "bg-red-500"  : "bg-amber-500"
                          )} />
                          <div>
                            <p className="text-sm font-semibold text-slate-800 capitalize">{run.pipeline_type.replace("_", " ")}</p>
                            <p className="text-xs text-slate-400">{new Date(run.created_at).toLocaleString("es", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium",
                            run.status === "completed" ? "bg-green-100 text-green-700" :
                            run.status === "running"   ? "bg-blue-100 text-blue-700"   :
                            run.status === "failed"    ? "bg-red-100 text-red-700"     : "bg-amber-100 text-amber-700"
                          )}>{run.status}</span>
                          <Clock className="h-3.5 w-3.5 text-slate-300 group-hover:text-violet-400 transition-colors" />
                        </div>
                      </Link>
                    ))}
                  </div>
                </section>
              )}

              {/* ── Bottom CTA ── */}
              <div className="pb-6">
                {genError && (
                  <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2.5 mb-3">{genError}</p>
                )}
                <button onClick={handleGenerate} disabled={generating || !config.brand_slug}
                  className={cn("w-full py-4 rounded-xl font-bold text-base flex items-center justify-center gap-3 transition-all",
                    config.brand_slug ? "bg-violet-600 hover:bg-violet-700 text-white shadow-lg shadow-violet-200" : "bg-slate-200 text-slate-400 cursor-not-allowed"
                  )}>
                  {generating ? <><Loader2 className="h-5 w-5 animate-spin" /> Iniciando pipeline…</> : <><Sparkles className="h-5 w-5" /> Generar Video Profesional</>}
                </button>
                {!config.brand_slug && (
                  <p className="text-xs text-slate-400 text-center mt-2">Selecciona una marca para habilitar la generación</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

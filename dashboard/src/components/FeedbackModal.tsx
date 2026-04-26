"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { PipelineEvent } from "@/lib/types";

interface FeedbackModalProps {
  runId: string;
  event: PipelineEvent;
  onClose: () => void;
}

export default function FeedbackModal({ runId, event, onClose }: FeedbackModalProps) {
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(false);
  const preview = event.data?.preview as any;

  async function handleApprove() {
    setLoading(true);
    try {
      await api.submitFeedback(runId, true, "");
      onClose();
    } catch (e) {
      alert("Error enviando feedback");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenerate() {
    if (!feedback.trim()) return;
    setLoading(true);
    try {
      await api.submitFeedback(runId, false, feedback);
      onClose();
    } catch (e) {
      alert("Error enviando feedback");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-4">
          <div>
            <h2 className="text-lg font-bold">Revisión requerida</h2>
            <p className="text-sm text-gray-500">{event.message}</p>
          </div>

          {/* Preview */}
          {preview?.data_url && (
            <img
              src={preview.data_url}
              alt="Preview"
              className="rounded-xl w-full object-cover max-h-72"
            />
          )}
          {preview?.script && (
            <div className="bg-gray-50 rounded-xl p-4 text-sm space-y-2 max-h-48 overflow-y-auto">
              <p className="font-semibold">{preview.script.title}</p>
              <p className="text-gray-600 italic">"{preview.script.hook}"</p>
              {preview.script.scenes?.slice(0, 2).map((s: any, i: number) => (
                <div key={i} className="border-t pt-2">
                  <p className="font-medium">Escena {i + 1}: {s.title}</p>
                  <p className="text-gray-600 text-xs">{s.speaker_text?.slice(0, 120)}...</p>
                </div>
              ))}
            </div>
          )}
          {preview?.audio_paths && (
            <p className="text-sm text-gray-500">
              {preview.audio_paths.length} archivos de audio generados
            </p>
          )}

          {/* Feedback input */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">
              Instrucciones para regenerar (opcional)
            </label>
            <textarea
              className="w-full rounded-lg border p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
              placeholder="Ej: Hazlo más energético, cambia el personaje a una mujer de 30 años..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleApprove}
              disabled={loading}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white rounded-lg py-2.5 text-sm font-semibold disabled:opacity-50"
            >
              Aprobar
            </button>
            <button
              onClick={handleRegenerate}
              disabled={loading || !feedback.trim()}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2.5 text-sm font-semibold disabled:opacity-50"
            >
              Regenerar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

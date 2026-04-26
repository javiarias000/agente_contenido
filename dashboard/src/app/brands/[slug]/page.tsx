"use client";

import { use } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function BrandDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const { data: brand, isLoading } = useSWR(`brand-${slug}`, () => api.getBrand(slug));

  if (isLoading) return <div className="p-8 text-gray-400">Cargando...</div>;
  if (!brand) return <div className="p-8 text-red-400">Marca no encontrada</div>;

  return (
    <div className="p-8 space-y-6 max-w-3xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{brand.name}</h1>
          <a href={brand.url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-500 hover:underline">
            {brand.url}
          </a>
        </div>
        <span className="bg-gray-100 text-gray-500 text-xs px-3 py-1 rounded-full">{brand.slug}</span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Colors */}
        {brand.colors?.palette && (
          <div className="bg-white border rounded-xl p-5">
            <h3 className="font-semibold text-sm mb-3">Paleta de Colores</h3>
            <div className="flex gap-2">
              {brand.colors.palette.map((color: string, i: number) => (
                <div key={i} className="flex flex-col items-center gap-1">
                  <div className="w-8 h-8 rounded-full border" style={{ backgroundColor: color }} />
                  <span className="text-xs text-gray-400">{color}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Typography */}
        {brand.typography && (
          <div className="bg-white border rounded-xl p-5">
            <h3 className="font-semibold text-sm mb-3">Tipografía</h3>
            <p className="text-sm"><span className="text-gray-400">Títulos:</span> {brand.typography.heading_font}</p>
            <p className="text-sm mt-1"><span className="text-gray-400">Cuerpo:</span> {brand.typography.body_font}</p>
          </div>
        )}
      </div>

      {/* Analysis */}
      <div className="space-y-4">
        {brand.tone_of_voice && (
          <div className="bg-white border rounded-xl p-5">
            <h3 className="font-semibold text-sm mb-2">Tono de Voz</h3>
            <p className="text-sm text-gray-600">{brand.tone_of_voice}</p>
          </div>
        )}
        {brand.target_audience && (
          <div className="bg-white border rounded-xl p-5">
            <h3 className="font-semibold text-sm mb-2">Audiencia Objetivo</h3>
            <p className="text-sm text-gray-600">{brand.target_audience}</p>
          </div>
        )}
        {brand.brand_values?.length > 0 && (
          <div className="bg-white border rounded-xl p-5">
            <h3 className="font-semibold text-sm mb-2">Valores de Marca</h3>
            <div className="flex flex-wrap gap-2">
              {brand.brand_values.map((v: string) => (
                <span key={v} className="bg-blue-50 text-blue-700 text-xs px-2.5 py-1 rounded-full">{v}</span>
              ))}
            </div>
          </div>
        )}
        {brand.content_suggestions?.length > 0 && (
          <div className="bg-white border rounded-xl p-5">
            <h3 className="font-semibold text-sm mb-2">Ideas de Contenido</h3>
            <ul className="space-y-1">
              {brand.content_suggestions.map((s: string, i: number) => (
                <li key={i} className="text-sm text-gray-600">• {s}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

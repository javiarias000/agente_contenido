"use client";

import { use } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function BrandDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const { data: brand, isLoading } = useSWR(`brand-${slug}`, () => api.getBrand(slug));

  if (isLoading) return <div className="p-8 text-gray-500">Cargando marca...</div>;
  if (!brand) return <div className="p-8 text-red-600 font-medium">Marca no encontrada</div>;

  return (
    <div className="p-8 space-y-6 max-w-4xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-500 mb-2">Marcas / <span className="text-slate-900 font-medium">{brand.name}</span></p>
          <h1 className="text-3xl font-bold text-slate-900">{brand.name}</h1>
          <a href={brand.url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline mt-2 block">
            {brand.url} ↗
          </a>
        </div>
        <span className="bg-blue-50 text-blue-700 text-xs px-3 py-1.5 rounded-full font-medium shrink-0">{brand.slug}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {brand.colors?.palette && (
          <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-3">
            <h3 className="font-semibold text-slate-900">Paleta de Colores</h3>
            <div className="flex gap-3 flex-wrap">
              {brand.colors.palette.map((color: string, i: number) => (
                <div key={i} className="flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-lg border border-gray-300 shadow-xs" style={{ backgroundColor: color }} title={color} />
                  <span className="text-xs text-gray-500 font-mono">{color}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {brand.typography && (
          <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-3">
            <h3 className="font-semibold text-slate-900">Tipografía</h3>
            <div className="space-y-2">
              <p className="text-sm"><span className="text-gray-500">Títulos:</span> <span className="font-medium text-slate-900">{brand.typography.heading_font}</span></p>
              <p className="text-sm"><span className="text-gray-500">Cuerpo:</span> <span className="font-medium text-slate-900">{brand.typography.body_font}</span></p>
            </div>
          </div>
        )}
      </div>

      <div className="space-y-4">
        {brand.tone_of_voice && (
          <div className="bg-white border border-blue-200 border-l-4 border-l-blue-600 rounded-xl p-6">
            <h3 className="font-semibold text-slate-900 mb-2">Tono de Voz</h3>
            <p className="text-sm text-gray-700">{brand.tone_of_voice}</p>
          </div>
        )}

        {brand.target_audience && (
          <div className="bg-white border border-blue-200 border-l-4 border-l-blue-600 rounded-xl p-6">
            <h3 className="font-semibold text-slate-900 mb-2">Audiencia Objetivo</h3>
            <p className="text-sm text-gray-700">{brand.target_audience}</p>
          </div>
        )}

        {brand.brand_values?.length > 0 && (
          <div className="bg-white border border-blue-200 border-l-4 border-l-blue-600 rounded-xl p-6">
            <h3 className="font-semibold text-slate-900 mb-3">Valores de Marca</h3>
            <div className="flex flex-wrap gap-2">
              {brand.brand_values.map((v: string) => (
                <span key={v} className="bg-blue-50 text-blue-700 text-sm px-3 py-1.5 rounded-full font-medium">{v}</span>
              ))}
            </div>
          </div>
        )}

        {brand.content_suggestions?.length > 0 && (
          <div className="bg-white border border-blue-200 border-l-4 border-l-blue-600 rounded-xl p-6">
            <h3 className="font-semibold text-slate-900 mb-3">Ideas de Contenido</h3>
            <ul className="space-y-2">
              {brand.content_suggestions.map((s: string, i: number) => (
                <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                  <span className="text-blue-600 font-bold mt-0.5">•</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

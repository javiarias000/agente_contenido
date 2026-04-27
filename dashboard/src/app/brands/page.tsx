"use client";

import Link from "next/link";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Plus, Trash2 } from "lucide-react";

export default function BrandsPage() {
  const { data: brands, mutate } = useSWR("brands", api.listBrands, { refreshInterval: 10000 });

  async function handleDelete(slug: string) {
    if (!confirm(`¿Eliminar la marca "${slug}"?`)) return;
    await api.deleteBrand(slug);
    mutate();
  }

  return (
    <div className="p-8 space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Marcas</h1>
          <p className="text-gray-500 text-sm mt-1.5">Perfiles de marca analizados</p>
        </div>
        <Link
          href="/brands/new"
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 py-2.5 text-sm font-medium flex items-center gap-2 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Analizar marca
        </Link>
      </div>

      {!brands || brands.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
          <p className="text-gray-600 text-sm mb-4">No hay marcas analizadas aún</p>
          <Link href="/brands/new" className="text-blue-600 text-sm font-medium hover:underline">
            Analizar primera marca →
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {brands.map((brand: any) => (
            <div key={brand.slug} className="bg-white border border-gray-200 rounded-xl p-5 space-y-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-slate-900 truncate">{brand.name}</h3>
                  <p className="text-xs text-gray-500 truncate mt-0.5">{brand.url}</p>
                </div>
                <button
                  onClick={() => handleDelete(brand.slug)}
                  className="text-gray-400 hover:text-red-600 transition-colors p-1"
                  title="Eliminar marca"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>

              {brand.colors?.palette && (
                <div className="flex gap-1.5">
                  {brand.colors.palette.slice(0, 5).map((color: string, i: number) => (
                    <div
                      key={i}
                      className="h-8 w-8 rounded-lg border border-gray-200 shadow-xs"
                      style={{ backgroundColor: color }}
                      title={color}
                    />
                  ))}
                </div>
              )}

              {brand.tone_of_voice && (
                <p className="text-sm text-gray-600 line-clamp-2">{brand.tone_of_voice}</p>
              )}

              <Link
                href={`/brands/${brand.slug}`}
                className="inline-block text-sm text-blue-600 font-medium hover:text-blue-700"
              >
                Ver perfil →
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

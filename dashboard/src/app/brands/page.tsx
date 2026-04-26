"use client";

import Link from "next/link";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function BrandsPage() {
  const { data: brands, mutate } = useSWR("brands", api.listBrands, { refreshInterval: 10000 });

  async function handleDelete(slug: string) {
    if (!confirm(`¿Eliminar la marca "${slug}"?`)) return;
    await api.deleteBrand(slug);
    mutate();
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Marcas</h1>
          <p className="text-gray-500 text-sm mt-1">Perfiles de marca analizados</p>
        </div>
        <Link
          href="/brands/new"
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 py-2 text-sm font-medium"
        >
          + Analizar nueva marca
        </Link>
      </div>

      {!brands || brands.length === 0 ? (
        <div className="bg-white border rounded-xl p-10 text-center text-gray-400">
          <p className="text-sm">No hay marcas. Analiza tu primera URL.</p>
          <Link href="/brands/new" className="mt-3 inline-block text-blue-600 text-sm underline">
            Analizar marca →
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {brands.map((brand: any) => (
            <div key={brand.slug} className="bg-white border rounded-xl p-5 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold">{brand.name}</h3>
                  <p className="text-xs text-gray-400">{brand.url}</p>
                </div>
                <span className="text-xs text-gray-300">{brand.slug}</span>
              </div>
              {brand.tone_of_voice && (
                <p className="text-sm text-gray-600 line-clamp-2">{brand.tone_of_voice}</p>
              )}
              <div className="flex gap-2">
                <Link
                  href={`/brands/${brand.slug}`}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Ver perfil
                </Link>
                <button
                  onClick={() => handleDelete(brand.slug)}
                  className="text-sm text-red-400 hover:underline ml-auto"
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import Link from "next/link";

const PIPELINES = [
  {
    type: "ugc",
    name: "UGC Pipeline",
    desc: "Guión → Personaje → Audio → Video completo con subtítulos",
    color: "bg-blue-600",
  },
  {
    type: "static_ads",
    name: "Static Ads",
    desc: "Genera hasta 40 anuncios estáticos con copy y diseño",
    color: "bg-purple-600",
  },
  {
    type: "avatar_reel",
    name: "Avatar Reel",
    desc: "Reacción a noticias con avatar realista y lip-sync",
    color: "bg-rose-600",
  },
  {
    type: "carousel",
    name: "Carousel",
    desc: "Carrusel de diapositivas para Instagram o LinkedIn",
    color: "bg-amber-600",
  },
];

export default function PipelinesPage() {
  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Pipelines</h1>
        <p className="text-gray-500 text-sm mt-1">Selecciona el tipo de contenido a generar</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {PIPELINES.map((p) => (
          <Link
            key={p.type}
            href={`/pipelines/run?type=${p.type}`}
            className="bg-white border rounded-xl p-6 hover:border-blue-300 hover:shadow-sm transition-all space-y-3"
          >
            <div className={`inline-block ${p.color} text-white text-xs px-2.5 py-1 rounded-full font-medium`}>
              {p.type.replace("_", " ").toUpperCase()}
            </div>
            <h3 className="font-semibold">{p.name}</h3>
            <p className="text-sm text-gray-500">{p.desc}</p>
            <p className="text-xs text-blue-600">Configurar →</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

"use client";

import Link from "next/link";
import { Video, Image, User, LayoutGrid, ArrowRight } from "lucide-react";

const PIPELINES = [
  {
    type: "ugc",
    name: "UGC Pipeline",
    desc: "Guión → Personaje → Audio → Video completo con subtítulos",
    icon: Video,
    color: "from-blue-500 to-blue-600",
    bgAccent: "bg-blue-50",
  },
  {
    type: "static_ads",
    name: "Static Ads",
    desc: "Genera hasta 40 anuncios estáticos con copy y diseño",
    icon: Image,
    color: "from-purple-500 to-purple-600",
    bgAccent: "bg-purple-50",
  },
  {
    type: "avatar_reel",
    name: "Avatar Reel",
    desc: "Reacción a noticias con avatar realista y lip-sync",
    icon: User,
    color: "from-rose-500 to-rose-600",
    bgAccent: "bg-rose-50",
  },
  {
    type: "carousel",
    name: "Carousel",
    desc: "Carrusel de diapositivas para Instagram o LinkedIn",
    icon: LayoutGrid,
    color: "from-amber-500 to-amber-600",
    bgAccent: "bg-amber-50",
  },
];

export default function PipelinesPage() {
  return (
    <div className="p-8 space-y-6 max-w-6xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Pipelines</h1>
        <p className="text-gray-500 text-sm mt-1.5">Selecciona el tipo de contenido a generar</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PIPELINES.map((p) => {
          const Icon = p.icon;
          return (
            <Link
              key={p.type}
              href={`/pipelines/run?type=${p.type}`}
              className={`${p.bgAccent} border border-gray-200 rounded-xl p-6 hover:shadow-md hover:-translate-y-0.5 transition-all space-y-4`}
            >
              <div className={`inline-flex items-center justify-center w-12 h-12 rounded-lg bg-gradient-to-br ${p.color} text-white`}>
                <Icon className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-lg">{p.name}</h3>
                <p className="text-sm text-gray-600 mt-1.5">{p.desc}</p>
              </div>
              <div className="flex items-center text-blue-600 text-sm font-medium gap-1">
                Configurar
                <ArrowRight className="h-4 w-4" />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

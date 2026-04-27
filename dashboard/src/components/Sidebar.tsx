"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { Clapperboard, LayoutDashboard, Briefcase, Zap, FolderOpen } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/brands", label: "Marcas", icon: Briefcase },
  { href: "/pipelines", label: "Pipelines", icon: Zap },
  { href: "/outputs", label: "Outputs", icon: FolderOpen },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-52 bg-white border-r border-gray-200 flex flex-col shrink-0">
      <div className="p-5 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <Clapperboard className="h-5 w-5 text-blue-600" />
          <h1 className="font-bold text-lg tracking-tight text-slate-900">ContentAI</h1>
        </div>
        <p className="text-xs text-gray-500 mt-1">Motor de Contenido</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-slate-600 hover:bg-gray-100 hover:text-slate-900"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-200">
        <p className="text-xs text-gray-400">v1.0.0 · API :8000</p>
      </div>
    </aside>
  );
}

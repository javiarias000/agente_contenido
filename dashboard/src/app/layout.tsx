import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Motor de Contenido IA",
  description: "Agentic AI Content Engine",
};

const nav = [
  { href: "/", label: "Dashboard" },
  { href: "/brands", label: "Marcas" },
  { href: "/pipelines", label: "Pipelines" },
  { href: "/outputs", label: "Outputs" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="h-full">
      <body className={`${inter.className} h-full bg-gray-50`}>
        <div className="flex h-full">
          {/* Sidebar */}
          <aside className="w-56 bg-white border-r flex flex-col shrink-0">
            <div className="p-5 border-b">
              <h1 className="font-bold text-lg tracking-tight">ContentAI</h1>
              <p className="text-xs text-gray-400 mt-0.5">Motor de Contenido</p>
            </div>
            <nav className="flex-1 p-3 space-y-1">
              {nav.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
                >
                  {label}
                </Link>
              ))}
            </nav>
            <div className="p-4 border-t">
              <p className="text-xs text-gray-400">v1.0.0 · API :8000</p>
            </div>
          </aside>

          {/* Main */}
          <main className="flex-1 overflow-y-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

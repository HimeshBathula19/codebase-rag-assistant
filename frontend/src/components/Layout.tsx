import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";

export function Layout() {
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200 bg-white lg:block">
        <Sidebar />
      </aside>
      {open ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button className="absolute inset-0 bg-slate-900/30" aria-label="Close menu" onClick={() => setOpen(false)} />
          <aside className="relative z-50 h-full w-64 bg-white shadow-xl">
            <button className="absolute right-3 top-3 text-slate-500" onClick={() => setOpen(false)} aria-label="Close">
              <X className="h-5 w-5" />
            </button>
            <Sidebar onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      ) : null}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
          <button type="button" onClick={() => setOpen(true)} className="rounded-md border border-slate-200 p-1.5">
            <Menu className="h-5 w-5" />
          </button>
          <span className="text-sm font-semibold">Codebase RAG Assistant</span>
        </header>
        <main className="px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

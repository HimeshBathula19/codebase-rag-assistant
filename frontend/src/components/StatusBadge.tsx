export function StatusBadge({ status }: { status: string | null | undefined }) {
  const value = (status || "unknown").toLowerCase();
  const styles: Record<string, string> = {
    ready: "bg-emerald-50 text-emerald-700 border-emerald-200",
    completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
    ok: "bg-emerald-50 text-emerald-700 border-emerald-200",
    indexing: "bg-blue-50 text-blue-700 border-blue-200",
    running: "bg-blue-50 text-blue-700 border-blue-200",
    queued: "bg-amber-50 text-amber-800 border-amber-200",
    pending: "bg-amber-50 text-amber-800 border-amber-200",
    failed: "bg-red-50 text-red-700 border-red-200",
    error: "bg-red-50 text-red-700 border-red-200",
    not_indexed: "bg-slate-100 text-slate-600 border-slate-200",
    idle: "bg-slate-100 text-slate-600 border-slate-200",
  };
  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${styles[value] ?? "bg-slate-100 text-slate-600 border-slate-200"}`}>
      {status || "unknown"}
    </span>
  );
}

import { Loader2 } from "lucide-react";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-6 text-sm text-slate-600">
      <Loader2 className="h-4 w-4 animate-spin text-accent" />
      {label}
    </div>
  );
}

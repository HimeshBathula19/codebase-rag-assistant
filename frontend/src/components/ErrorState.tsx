import { AlertCircle } from "lucide-react";

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-800">
      <div className="flex items-start gap-2">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p>{message}</p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 text-sm font-medium text-red-700 underline-offset-2 hover:underline"
            >
              Retry
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

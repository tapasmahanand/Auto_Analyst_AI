import type { Step } from "@/lib/api";

const ICONS: Record<Step["status"], string> = {
  pending: "○",
  running: "●",
  retrying: "↻",
  completed: "✓",
  failed: "✕",
};

const ICON_STYLES: Record<Step["status"], string> = {
  pending: "text-slate-400",
  running: "animate-pulse text-blue-600",
  retrying: "text-amber-600",
  completed: "text-emerald-600",
  failed: "text-red-600",
};

export default function PlanSteps({ steps }: { steps: Step[] }) {
  return (
    <ol className="space-y-3">
      {steps.map((step) => (
        <li
          key={step.id}
          className="rounded-lg border border-slate-200 bg-white px-4 py-3"
        >
          <div className="flex items-start gap-3">
            <span
              className={`mt-0.5 w-4 text-center font-bold ${ICON_STYLES[step.status]}`}
            >
              {ICONS[step.status]}
            </span>
            <div className="min-w-0 flex-1">
              <p className="font-medium text-slate-800">
                {step.index + 1}. {step.goal}
              </p>
              {step.method && (
                <p className="mt-0.5 text-sm text-slate-500">{step.method}</p>
              )}
              {step.status === "retrying" && (
                <p className="mt-1 text-xs text-amber-600">
                  Attempt {step.attempts} failed — AI is correcting the code…
                </p>
              )}
              {step.status === "failed" && step.error && (
                <p className="mt-1 whitespace-pre-wrap text-xs text-red-600">
                  Failed after {step.attempts} attempts: {step.error.slice(0, 400)}
                </p>
              )}
              {step.status === "completed" && step.result && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs text-slate-400 hover:text-slate-600">
                    Computed results{step.attempts > 1 ? ` (${step.attempts} attempts)` : ""}
                  </summary>
                  <pre className="mt-1 max-h-56 overflow-auto rounded bg-slate-50 p-2 text-xs text-slate-600">
                    {JSON.stringify(step.result, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

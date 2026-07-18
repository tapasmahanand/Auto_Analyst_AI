"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import ChartGallery from "@/components/ChartGallery";
import InsightPanel from "@/components/InsightPanel";
import PlanSteps from "@/components/PlanSteps";
import StatusBadge from "@/components/StatusBadge";
import { reportUrl, type Run, subscribeToRun } from "@/lib/api";

const STATUS_HINTS: Record<Run["status"], string> = {
  pending: "Queued…",
  planning: "The AI is reading your dataset and drafting an analysis plan…",
  running: "Executing AI-generated analysis code in the sandbox…",
  reviewing: "The AI is reviewing the computed results…",
  reporting: "Writing insights and generating your report…",
  completed: "Analysis complete.",
  failed: "The analysis failed.",
};

const REPORT_LABELS: Record<string, string> = {
  md: "Markdown",
  html: "HTML",
  pdf: "PDF",
};

export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<Run | null>(null);

  useEffect(() => {
    if (!id) return;
    return subscribeToRun(id, setRun);
  }, [id]);

  if (!run) {
    return <p className="text-slate-500">Loading analysis…</p>;
  }

  const done = run.status === "completed";

  return (
    <div className="space-y-8">
      <section>
        <Link href="/" className="text-sm text-blue-600 hover:underline">
          ← New analysis
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            {run.insights?.title ?? run.prompt}
          </h1>
          <StatusBadge status={run.status} />
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Dataset: {run.dataset_filename} · Asked:{" "}
          {new Date(run.created_at).toLocaleString()}
        </p>
        {!done && run.status !== "failed" && (
          <p className="mt-3 rounded-lg bg-blue-50 px-4 py-2 text-sm text-blue-700">
            {STATUS_HINTS[run.status]}
          </p>
        )}
        {run.status === "failed" && (
          <p className="mt-3 whitespace-pre-wrap rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {run.error ?? "Unknown error."}
          </p>
        )}
      </section>

      {(run.steps?.length ?? 0) > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-slate-800">
            Analysis plan
          </h2>
          <PlanSteps steps={run.steps!} />
        </section>
      )}

      {(run.charts?.length ?? 0) > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-slate-800">Charts</h2>
          <ChartGallery charts={run.charts!} />
        </section>
      )}

      {run.insights && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-slate-800">Insights</h2>
          <InsightPanel insights={run.insights} review={run.review} />
        </section>
      )}

      {done && (
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">
            Download report
          </h2>
          <div className="flex flex-wrap gap-3">
            {(run.reports ?? []).map((format) => (
              <a
                key={format}
                href={reportUrl(run.id, format)}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                ⬇ {REPORT_LABELS[format] ?? format.toUpperCase()}
              </a>
            ))}
          </div>
          {!(run.reports ?? []).includes("pdf") && (
            <p className="mt-2 text-xs text-slate-400">
              PDF export needs WeasyPrint&apos;s system libraries (see README);
              Markdown and HTML are always available.
            </p>
          )}
        </section>
      )}
    </div>
  );
}

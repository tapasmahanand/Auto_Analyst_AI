import type { Insights, Review } from "@/lib/api";

export default function InsightPanel({
  insights,
  review,
}: {
  insights: Insights;
  review?: Review | null;
}) {
  const limitations = [
    ...(insights.limitations ?? []),
    ...(review?.limitations ?? []),
  ];
  return (
    <div className="space-y-5">
      {insights.executive_summary && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-blue-700">
            Executive summary
          </h3>
          <p className="text-slate-700">{insights.executive_summary}</p>
        </div>
      )}

      {(insights.key_findings?.length ?? 0) > 0 && (
        <div>
          <h3 className="mb-2 font-semibold text-slate-800">Key findings</h3>
          <div className="space-y-2">
            {insights.key_findings!.map((finding, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-200 bg-white p-3"
              >
                <p className="text-slate-800">{finding.finding}</p>
                {finding.supporting_numbers && (
                  <p className="mt-1 text-sm text-slate-500">
                    📊 {finding.supporting_numbers}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {(insights.recommendations?.length ?? 0) > 0 && (
        <div>
          <h3 className="mb-2 font-semibold text-slate-800">Recommendations</h3>
          <ul className="list-inside list-disc space-y-1 text-slate-700">
            {insights.recommendations!.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {limitations.length > 0 && (
        <div className="rounded-lg bg-amber-50 p-3">
          <h3 className="mb-1 text-sm font-semibold text-amber-800">
            Limitations
          </h3>
          <ul className="list-inside list-disc space-y-0.5 text-sm text-amber-700">
            {limitations.map((limitation, i) => (
              <li key={i}>{limitation}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

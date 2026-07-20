"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import DatasetCard from "@/components/DatasetCard";
import StatusBadge from "@/components/StatusBadge";
import UploadZone from "@/components/UploadZone";
import {
  API_BASE,
  createAnalysis,
  type Dataset,
  getDataset,
  listAnalyses,
  listDatasets,
  type Run,
} from "@/lib/api";

const EXAMPLES = [
  "Which region drives the most revenue, and how did sales trend over time?",
  "Find correlations between the numeric columns and flag any outliers.",
  "Summarize the dataset and highlight data quality issues.",
];

function BackendDownBanner() {
  const isLocalhost = /^https?:\/\/localhost/i.test(API_BASE);
  const isBrowserLocalhost =
    typeof window !== "undefined" &&
    window.location.hostname !== "localhost" &&
    window.location.hostname !== "127.0.0.1";

  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      <div>
        Cannot reach the backend at{" "}
        <code className="rounded bg-amber-100 px-1 break-all">{API_BASE}</code>.
      </div>
      {isLocalhost && isBrowserLocalhost ? (
        <div className="mt-2">
          This deployed site was built without{" "}
          <code className="rounded bg-amber-100 px-1">NEXT_PUBLIC_API_BASE</code>{" "}
          set, so it is trying to call your own machine. Set the variable on
          Netlify to your backend URL (e.g.{" "}
          <code className="rounded bg-amber-100 px-1">
            https://your-service.onrender.com
          </code>
          ) and redeploy with <em>Clear cache and deploy site</em>.
        </div>
      ) : isLocalhost ? (
        <div className="mt-2">
          Start the backend with{" "}
          <code className="rounded bg-amber-100 px-1">
            uvicorn app.main:app --port 8000
          </code>{" "}
          in <code className="rounded bg-amber-100 px-1">backend/</code>.
        </div>
      ) : (
        <div className="mt-2">
          Check that the backend service is running, that{" "}
          <code className="rounded bg-amber-100 px-1">CORS_ORIGINS</code>{" "}
          includes this site&apos;s origin (
          <code className="rounded bg-amber-100 px-1 break-all">
            {typeof window !== "undefined" ? window.location.origin : ""}
          </code>
          ), and that{" "}
          <code className="rounded bg-amber-100 px-1">
            {API_BASE}/api/health
          </code>{" "}
          returns 200. On Render&apos;s free tier the first request after ~15
          min of idle can take up to 50 s to cold-start &mdash; try again in a
          moment.
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [recentDatasets, setRecentDatasets] = useState<Dataset[]>([]);
  const [history, setHistory] = useState<Run[]>([]);
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    listDatasets()
      .then(setRecentDatasets)
      .catch(() => setBackendDown(true));
    listAnalyses()
      .then(setHistory)
      .catch(() => {});
  }, []);

  const selectDataset = async (id: string) => {
    setError(null);
    try {
      setDataset(await getDataset(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dataset");
    }
  };

  const startAnalysis = async () => {
    if (!dataset || prompt.trim().length < 3 || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const run = await createAnalysis(dataset.id, prompt.trim());
      router.push(`/analysis/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      {backendDown && <BackendDownBanner />}

      <section>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Analyze any dataset with AI
        </h1>
        <p className="mt-1 text-slate-500">
          1. Upload a file · 2. Ask a question · 3. Get charts, insights and a
          report.
        </p>
      </section>

      <section className="space-y-4">
        <UploadZone
          onUploaded={(uploaded) => {
            setDataset(uploaded);
            setRecentDatasets((prev) => [uploaded, ...prev.slice(0, 9)]);
          }}
        />

        {!dataset && recentDatasets.length > 0 && (
          <div className="text-sm text-slate-500">
            Or reuse a previous upload:{" "}
            {recentDatasets.slice(0, 5).map((d) => (
              <button
                key={d.id}
                onClick={() => selectDataset(d.id)}
                className="mr-2 rounded-full border border-slate-300 bg-white px-3 py-1 text-slate-700 hover:border-blue-400 hover:text-blue-600"
              >
                {d.filename}
              </button>
            ))}
          </div>
        )}

        {dataset && <DatasetCard dataset={dataset} />}
      </section>

      {dataset && (
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <label
            htmlFor="prompt"
            className="mb-2 block font-medium text-slate-800"
          >
            What would you like to know?
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            placeholder="e.g. Which region drives the most revenue, and why did sales dip in June?"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-800 focus:border-blue-500 focus:outline-none"
          />
          <div className="mt-2 flex flex-wrap gap-2">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                onClick={() => setPrompt(example)}
                className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600 hover:bg-slate-200"
              >
                {example}
              </button>
            ))}
          </div>
          <button
            onClick={startAnalysis}
            disabled={submitting || prompt.trim().length < 3}
            className="mt-4 rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Starting analysis…" : "Run AI analysis"}
          </button>
          {error && (
            <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}
        </section>
      )}

      {history.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-slate-800">
            Previous analyses
          </h2>
          <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
            {history.slice(0, 10).map((run) => (
              <li key={run.id}>
                <Link
                  href={`/analysis/${run.id}`}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800">
                      {run.prompt}
                    </p>
                    <p className="text-xs text-slate-500">
                      {run.dataset_filename} ·{" "}
                      {new Date(run.created_at).toLocaleString()}
                    </p>
                  </div>
                  <StatusBadge status={run.status} />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

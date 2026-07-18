import { type Dataset, formatBytes } from "@/lib/api";

function Chip({ label, values }: { label: string; values?: string[] }) {
  if (!values || values.length === 0) return null;
  return (
    <div className="text-sm">
      <span className="font-medium text-slate-600">{label}: </span>
      <span className="text-slate-500">{values.join(", ")}</span>
    </div>
  );
}

export default function DatasetCard({ dataset }: { dataset: Dataset }) {
  const meta = dataset.metadata ?? {};
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h3 className="font-semibold text-slate-800">{dataset.filename}</h3>
        <span className="text-xs uppercase tracking-wide text-slate-400">
          {dataset.file_type} · {formatBytes(dataset.size_bytes)}
        </span>
      </div>

      {meta.is_tabular ? (
        <>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["Rows", meta.row_count],
              ["Columns", meta.column_count],
              ["Missing values", meta.total_missing_values],
              ["Duplicate rows", meta.duplicate_rows],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 px-3 py-2">
                <div className="text-lg font-semibold text-slate-800">
                  {value ?? "—"}
                </div>
                <div className="text-xs text-slate-500">{label}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 space-y-1">
            <Chip label="Numeric" values={meta.numeric_columns} />
            <Chip label="Categorical" values={meta.categorical_columns} />
            <Chip label="Dates" values={meta.date_columns} />
          </div>
        </>
      ) : (
        <p className="mt-3 text-sm text-slate-500">
          {meta.note ?? "Treated as a text document."}{" "}
          {meta.text_words ? `${meta.text_words} words.` : ""}
        </p>
      )}
    </div>
  );
}

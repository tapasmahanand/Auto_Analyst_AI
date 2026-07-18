/* eslint-disable @next/next/no-img-element */
import { apiUrl, type ChartRef } from "@/lib/api";

export default function ChartGallery({ charts }: { charts: ChartRef[] }) {
  if (charts.length === 0) return null;
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {charts.map((chart) => (
        <figure
          key={chart.id}
          className="rounded-xl border border-slate-200 bg-white p-3"
        >
          <img
            src={apiUrl(chart.url)}
            alt={chart.name}
            className="w-full rounded-lg"
          />
          <figcaption className="mt-2 text-center text-xs text-slate-500">
            {chart.name}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

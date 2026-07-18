const STYLES: Record<string, string> = {
  pending: "bg-slate-100 text-slate-600",
  planning: "bg-blue-100 text-blue-700",
  running: "bg-blue-100 text-blue-700",
  retrying: "bg-amber-100 text-amber-700",
  reviewing: "bg-violet-100 text-violet-700",
  reporting: "bg-violet-100 text-violet-700",
  completed: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
};

const ACTIVE = new Set(["planning", "running", "retrying", "reviewing", "reporting"]);

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
        STYLES[status] ?? STYLES.pending
      }`}
    >
      {ACTIVE.has(status) && (
        <span className="h-2 w-2 animate-pulse rounded-full bg-current" />
      )}
      {status}
    </span>
  );
}

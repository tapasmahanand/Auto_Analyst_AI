"use client";

import { useRef, useState } from "react";
import { type Dataset, uploadDataset } from "@/lib/api";

const ACCEPT = ".csv,.xlsx,.xls,.json,.txt,.pdf";

export default function UploadZone({
  onUploaded,
}: {
  onUploaded: (dataset: Dataset) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = async (file: File | undefined) => {
    if (!file || busy) return;
    setError(null);
    setBusy(true);
    try {
      onUploaded(await uploadDataset(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFile(e.dataTransfer.files[0]);
        }}
        className={`flex w-full flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragging
            ? "border-blue-500 bg-blue-50"
            : "border-slate-300 bg-white hover:border-blue-400 hover:bg-slate-50"
        }`}
      >
        <span className="text-3xl">{busy ? "⏳" : "📂"}</span>
        <span className="mt-2 font-medium text-slate-700">
          {busy ? "Uploading & inspecting…" : "Drop a dataset here or click to browse"}
        </span>
        <span className="mt-1 text-sm text-slate-500">
          CSV, Excel, JSON, TXT or PDF
        </span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      {error && (
        <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}

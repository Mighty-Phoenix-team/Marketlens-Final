"use client";
import { useState } from "react";
import { useAssets } from "./AssetsProvider";
export function SaveAssetButton({ symbol }: { symbol: string }) {
  const {
    profile,
    loading,
    error: profileError,
    change,
    pending,
  } = useAssets();
  const [error, setError] = useState("");
  const saved = profile?.saved_assets.includes(symbol) ?? false;
  const busy = pending.includes(symbol);
  async function save() {
    setError("");
    try {
      await change(symbol, true);
    } catch {
      setError("Gagal menyimpan. Coba lagi.");
    }
  }
  return (
    <div>
      <button
        type="button"
        className={saved ? "button button-saved" : "button button-secondary"}
        disabled={loading || !profile || saved || busy}
        onClick={save}
        aria-label={
          (saved ? "Tersimpan: " : "Tambah ") +
          symbol +
          (saved ? "" : " ke My Assets")
        }
      >
        <span aria-hidden="true">{saved ? "✓" : "+"}</span>{" "}
        {busy ? "Menyimpan…" : saved ? "Tersimpan" : "Tambah ke My Assets"}
      </button>
      {(error || profileError) && (
        <p role="alert" className="mt-2 text-xs text-text-muted">
          {error || profileError}
        </p>
      )}
    </div>
  );
}

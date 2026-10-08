"use client";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAssets } from "@/components/assets/AssetsProvider";
import { compareAssets, ApiError } from "@/lib/api";
import { getActiveProfileId } from "@/lib/session";
import {
  cleanTicker,
  validTicker,
  metricLabel,
  metricValue,
} from "@/lib/format";
import type { ComparisonResponse } from "@/lib/types";
import { AppIcon } from "@/components/ui/AppIcon";

export default function ComparisonPage() {
  const router = useRouter();
  const { profile, loading: profileLoading, error: profileError } = useAssets();
  const [selected, setSelected] = useState<string[]>([]);
  const [ticker, setTicker] = useState("");
  const [result, setResult] = useState<ComparisonResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [completed, setCompleted] = useState(false);
  useEffect(() => {
    if (!getActiveProfileId()) router.replace("/profile");
  }, [router]);
  function select(symbol: string) {
    if (loading) return;
    setError("");
    setCompleted(false);
    setResult(null);
    if (selected.includes(symbol)) {
      setSelected(selected.filter((s) => s !== symbol));
      return;
    }
    if (selected.length >= 4) {
      setError("Bandingkan maksimal 4 aset sekaligus.");
      return;
    }
    setSelected([...selected, symbol]);
  }
  function add(event: FormEvent) {
    event.preventDefault();
    const symbol = cleanTicker(ticker);
    if (!validTicker(symbol)) {
      setError("Masukkan ticker yang valid, misalnya BBCA.");
      return;
    }
    if (selected.includes(symbol)) {
      setError(symbol + " sudah dipilih.");
      return;
    }
    select(symbol);
    setTicker("");
  }
  async function compare() {
    if (!profile || selected.length < 2 || loading) return;
    setLoading(true);
    setError("");
    setCompleted(false);
    setResult(null);
    try {
      setResult(await compareAssets(profile.id, [...selected]));
    } catch (err) {
      const detail =
        err instanceof ApiError &&
        typeof err.body === "object" &&
        err.body !== null &&
        "detail" in err.body
          ? err.body.detail
          : null;
      setError(
        typeof detail === "string"
          ? detail
          : "Comparison belum dapat dimuat. Periksa koneksi lalu coba lagi.",
      );
    } finally {
      setCompleted(true);
      setLoading(false);
    }
  }
  const findings = result?.assets ?? [];
  const metrics = result?.metrics ?? [];
  const periodLabels: Record<string, string> = {
    missing_data: "Data belum lengkap",
    different_units: "Satuan berbeda",
    different_periods: "Periode berbeda",
    matching_labels_only: "Label periode sama; periksa metode",
    unconfirmed: "Kesetaraan belum terkonfirmasi",
  };
  return (
    <div className="page-wrap">
      <div className="page-heading">
        <div>
          <p className="eyebrow">RESEARCH SIDE BY SIDE</p>
          <h1>Comparison</h1>
          <p>Bandingkan evidence dan konteks riset dari 2–4 aset pilihanmu.</p>
        </div>
        <Link href="/my-assets" className="button button-secondary">
          Lihat My Assets →
        </Link>
      </div>
      <section
        className="selection-panel"
        aria-label="Pilih aset untuk comparison"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">Pilih aset</h2>
          <span className="text-xs text-text-muted">
            {selected.length} / 4 dipilih
          </span>
        </div>
        <p className="mt-2 text-sm text-text-muted">
          Ambil dari My Assets atau masukkan ticker lain.
        </p>
        <div className="my-4 flex flex-wrap gap-2">
          {(profile?.saved_assets ?? []).map((s) => (
            <button
              type="button"
              key={s}
              className={
                "asset-chip " + (selected.includes(s) ? "selected" : "")
              }
              aria-pressed={selected.includes(s)}
              onClick={() => select(s)}
              disabled={loading}
            >
              {selected.includes(s) ? "✓ " : "+ "}
              {s}
            </button>
          ))}
          {!profileLoading && !profile?.saved_assets.length && (
            <p className="text-sm text-text-muted">
              Belum ada aset tersimpan. Tambahkan ticker di bawah.
            </p>
          )}
        </div>
        <form onSubmit={add} className="comparison-ticker-form">
          <label htmlFor="comparison-ticker">Ticker lain</label>
          <input
            id="comparison-ticker"
            aria-label="Ticker comparison"
            className="text-input max-w-xs"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="Ticker lain, misalnya TLKM"
            maxLength={15}
            disabled={loading}
          />
          <button className="button button-secondary" disabled={loading}>
            Tambah ticker
          </button>
        </form>
        {!!selected.length && (
          <div className="mt-4 flex flex-wrap gap-2" aria-label="Aset dipilih">
            {selected.map((s) => (
              <button
                key={s}
                className="asset-chip selected"
                aria-label={"Batalkan " + s}
                onClick={() => select(s)}
                disabled={loading}
              >
                {s} ×
              </button>
            ))}
          </div>
        )}
        <div className="selection-footer">
          <p>
            Pilih 2–4 aset. Periode dan sumber ditampilkan bersama setiap
            metrik.
          </p>
          <button
            className="button button-primary"
            onClick={compare}
            disabled={!profile || selected.length < 2 || loading}
          >
            {loading ? "Membandingkan…" : "Bandingkan aset →"}
          </button>
        </div>
      </section>
      {(error || profileError) && (
        <p className="notice" role="alert">
          {error || profileError}
        </p>
      )}
      {loading && (
        <div
          className="skeleton-card"
          role="status"
          aria-label="Memuat comparison"
        />
      )}
      {completed && findings.length > 0 && (
        <section className="comparison-results">
          <div className="section-heading">
            <h2>Evidence comparison</h2>
            <span className="text-xs text-text-muted">
              {profile?.horizon_days} hari diminta
            </span>
          </div>
          <p className="mb-4 text-sm text-text-muted">
            Periksa periode di setiap sel; metrik dengan periode berbeda tidak
            sebanding secara langsung.
          </p>
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Tabel perbandingan aset"
          >
            <table className="comparison-table">
              <caption className="sr-only">
                Evidence per aset, termasuk periode dan sumber
              </caption>
              <thead>
                <tr>
                  <th scope="col">Evidence</th>
                  {findings.map((f) => (
                    <th scope="col" key={f.symbol}>
                      <Link href={"/finding/" + f.symbol}>{f.symbol} ↗</Link>
                      <span>{f.company_name}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">Research Relevance</th>
                  {findings.map((f) => (
                    <td key={f.symbol}>
                      <strong>{f.research_relevance.toFixed(2)} / 10</strong>
                    </td>
                  ))}
                </tr>
                {metrics.map((metric) => (
                  <tr key={metric.metric}>
                    <th scope="row">
                      {metricLabel(metric.metric)}
                      <small>
                        {periodLabels[metric.period_status] ??
                          periodLabels.unconfirmed}
                      </small>
                    </th>
                    {findings.map((f) => {
                      const e = metric.evidence_by_symbol[f.symbol];
                      const value = metric.values[f.symbol];
                      return (
                        <td key={f.symbol}>
                          {value != null ? (
                            <>
                              <strong>
                                {e?.unit &&
                                !["ratio", "fraction"].includes(e.unit)
                                  ? `${value.toLocaleString("id-ID")} ${e.unit}`
                                  : metricValue(metric.metric, value)}
                              </strong>
                              <small>
                                {e?.period ?? "Periode tidak tersedia"}
                              </small>
                              <small>{e?.method}</small>
                              <small>
                                {e?.retrieved_at
                                  ? "Diambil: " +
                                    new Date(e.retrieved_at).toLocaleString(
                                      "id-ID",
                                    )
                                  : "Waktu pengambilan tidak tersedia"}
                              </small>
                              {e?.source && /^https?:\/\//.test(e.source) && (
                                <a
                                  href={e.source}
                                  rel="noreferrer"
                                  target="_blank"
                                >
                                  Sumber ↗
                                </a>
                              )}
                            </>
                          ) : (
                            <span className="text-text-muted">
                              Data unavailable
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!metrics.length && (
            <p className="notice">
              Belum ada evidence numerik untuk aset yang dipilih.
            </p>
          )}
          {!!result?.limitations.length && (
            <div className="notice">
              <strong>Catatan perbandingan</strong>
              <ul>
                {result.limitations.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            </div>
          )}
          {findings.map((f) => (
            <details key={f.symbol} className="limitations">
              <summary>
                Limitations · {f.symbol} ({f.limitations.length})
              </summary>
              <ul>
                {f.limitations.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            </details>
          ))}
        </section>
      )}
      {!loading && !completed && (
        <div className="empty-panel comparison-empty">
          <span className="empty-icon">
            <AppIcon name="compare" />
          </span>
          <h2>Satu konteks, beberapa sudut pandang</h2>
          <p>
            Pilih minimal dua aset untuk melihat metrik, periode, dan
            ketersediaan evidence berdampingan.
          </p>
        </div>
      )}
      {completed && findings.length === 0 && (
        <div className="empty-panel">
          <h2>Comparison belum tersedia</h2>
          <p>
            Semua aset pilihan perlu berhasil dimuat agar hasil perbandingan
            lengkap. Coba lagi setelah koneksi tersedia.
          </p>
        </div>
      )}
      <p className="page-footnote">
        Perbandingan menjelaskan evidence terukur dan relevansi riset; tidak
        menyimpulkan kualitas investasi atau prediksi return.
      </p>
    </div>
  );
}

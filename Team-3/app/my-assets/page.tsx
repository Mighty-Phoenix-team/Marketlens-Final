"use client";
import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { FindingCard } from "@/components/finding/FindingCard";
import { useAssets } from "@/components/assets/AssetsProvider";
import { getMyAssets } from "@/lib/api";
import { getActiveProfileId } from "@/lib/session";
import { cleanTicker, validTicker, unavailableLabel } from "@/lib/format";
import type { MyAssetsResponse } from "@/lib/types";
import { AppIcon } from "@/components/ui/AppIcon";
export default function MyAssetsPage() {
  const router = useRouter();
  const {
    profile,
    loading: profileLoading,
    error: profileError,
    change,
    pending,
  } = useAssets();
  const [data, setData] = useState<MyAssetsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [ticker, setTicker] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const load = useCallback(
    async (refresh = false) => {
      const id = getActiveProfileId();
      if (!id) {
        router.replace("/profile");
        return;
      }
      setLoading(true);
      try {
        setData(await getMyAssets(id, refresh));
      } catch {
        setError("Daftar aset belum dapat dimuat. Coba muat ulang.");
      } finally {
        setLoading(false);
      }
    },
    [router],
  );
  useEffect(() => {
    void load();
  }, [load]);
  async function add(event: FormEvent) {
    event.preventDefault();
    const symbol = cleanTicker(ticker);
    setError("");
    setMessage("");
    if (!validTicker(symbol)) {
      setError("Masukkan ticker berisi 1–12 huruf atau angka, misalnya BBCA.");
      return;
    }
    if (profile?.saved_assets.includes(symbol)) {
      setMessage(symbol + " sudah ada di My Assets.");
      return;
    }
    setSubmitting(true);
    try {
      await change(symbol, true);
      setTicker("");
      setMessage(symbol + " ditambahkan ke My Assets.");
      await load();
    } catch {
      setError("Aset belum tersimpan. Coba lagi.");
    } finally {
      setSubmitting(false);
    }
  }
  async function remove(symbol: string) {
    setError("");
    setMessage("");
    try {
      await change(symbol, false);
      setMessage(symbol + " dihapus dari My Assets.");
      await load();
    } catch {
      setError("Aset belum dihapus. Coba lagi.");
    }
  }
  const removeButton = (symbol: string) => (
    <button
      className="button button-secondary"
      disabled={pending.includes(symbol)}
      onClick={() => remove(symbol)}
      aria-label={"Hapus " + symbol}
    >
      {pending.includes(symbol) ? "Menghapus…" : "Hapus aset"}
    </button>
  );
  const findings = data?.findings ?? [];
  const unavailableSymbols = (profile?.saved_assets ?? []).filter(
    (s) => !findings.some((f) => f.symbol === s),
  );
  return (
    <div className="page-wrap">
      <div className="page-heading">
        <div>
          <p className="eyebrow">YOUR PERSONAL RESEARCH LIST</p>
          <h1>
            My <em>Assets</em>
          </h1>
          <p>
            Simpan aset pilihanmu dan pahami evidence di balik setiap temuan.
          </p>
        </div>
        <Link href="/comparison" className="button button-secondary">
          <AppIcon name="compare" /> Bandingkan aset
        </Link>
      </div>
      <form className="add-asset-panel" onSubmit={add}>
        <div>
          <label htmlFor="asset-ticker" className="font-semibold">
            Tambahkan aset
          </label>
          <p className="mt-1 text-sm text-text-muted">
            Masukkan ticker, termasuk aset yang belum muncul di Discovery.
          </p>
        </div>
        <div className="input-action">
          <input
            id="asset-ticker"
            className="text-input"
            placeholder="Contoh: BBCA"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            maxLength={15}
            autoComplete="off"
          />
          <button
            className="button button-primary"
            disabled={submitting || profileLoading || !profile}
          >
            {submitting ? "Menyimpan…" : "+ Tambah aset"}
          </button>
        </div>
      </form>
      {(error || profileError) && (
        <div className="notice" role="alert">
          {error || profileError}
          <button
            className="detail-link ml-3"
            onClick={() => {
              setError("");
              void load();
            }}
          >
            Coba lagi
          </button>
        </div>
      )}
      {message && (
        <p role="status" className="notice notice-success">
          {message}
        </p>
      )}
      <div className="section-heading">
        <h2>
          Aset tersimpan <span>{profile?.saved_assets.length ?? "—"}</span>
        </h2>
        <button
          className="detail-link"
          onClick={() => void load(true)}
          disabled={loading}
        >
          <AppIcon name="refresh" /> Muat ulang
        </button>
      </div>
      {loading || profileLoading ? (
        <div
          className="skeleton-grid"
          role="status"
          aria-label="Memuat My Assets"
        >
          <div className="skeleton-card" />
        </div>
      ) : (
        <>
          {!profile?.saved_assets.length && !findings.length ? (
            <div className="empty-panel">
              <span className="empty-icon">
                <AppIcon name="list" />
              </span>
              <h2>Mulai daftar risetmu</h2>
              <p>Tambahkan ticker di atas atau simpan temuan dari Discovery.</p>
              <Link className="button button-secondary" href="/discovery">
                Jelajahi Discovery →
              </Link>
            </div>
          ) : (
            <div className="finding-grid">
              {findings.map((f) => (
                <FindingCard
                  key={f.symbol}
                  finding={f}
                  action={removeButton(f.symbol)}
                />
              ))}
              {unavailableSymbols.map((symbol) => (
                <article
                  key={symbol}
                  className="finding-card finding-unavailable"
                  aria-label={symbol}
                >
                  <h2 className="text-xl font-semibold">{symbol}</h2>
                  <p className="my-5 text-sm text-text-muted">
                    Aset tersimpan. Evidence belum tersedia saat ini.
                  </p>
                  <div className="card-actions">{removeButton(symbol)}</div>
                </article>
              ))}
            </div>
          )}
          {!!data?.unavailable_assets.length && (
            <div className="notice">
              {data.unavailable_assets.map(unavailableLabel).join(" · ")}
            </div>
          )}
        </>
      )}
      <p className="page-footnote">
        Daftar aset tersimpan pada research profile dan tetap tersedia setelah
        halaman dimuat ulang.
      </p>
    </div>
  );
}

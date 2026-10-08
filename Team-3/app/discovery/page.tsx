"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FindingCard } from "@/components/finding/FindingCard";
import { getDiscovery } from "@/lib/api";
import { getActiveProfileId } from "@/lib/session";
import { unavailableLabel } from "@/lib/format";
import { useAssets } from "@/components/assets/AssetsProvider";
import type { DiscoveryResponse } from "@/lib/types";
import { AppIcon } from "@/components/ui/AppIcon";
export default function DiscoveryPage() {
  const router = useRouter();
  const { profile } = useAssets();
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("relevance");
  const [savedOnly, setSavedOnly] = useState(false);
  const [data, setData] = useState<DiscoveryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(
    async (refresh = false) => {
      const id = getActiveProfileId();
      if (!id) {
        router.replace("/profile");
        return;
      }
      setLoading(true);
      setError("");
      try {
        setData(await getDiscovery(id, refresh));
      } catch {
        setError(
          "Discovery belum dapat dimuat. Periksa koneksi lalu coba lagi.",
        );
      } finally {
        setLoading(false);
      }
    },
    [router],
  );
  useEffect(() => {
    void load();
  }, [load]);
  const visibleFindings = (data?.findings ?? [])
    .filter((f) => {
      const matchesQuery = `${f.symbol} ${f.company_name} ${f.sector ?? ""}`
        .toLowerCase()
        .includes(query.trim().toLowerCase());
      return (
        matchesQuery && (!savedOnly || profile?.saved_assets.includes(f.symbol))
      );
    })
    .sort((a, b) =>
      sort === "ticker"
        ? a.symbol.localeCompare(b.symbol)
        : b.research_relevance - a.research_relevance,
    );
  function clearFilters() {
    setQuery("");
    setSavedOnly(false);
    setSort("relevance");
  }
  return (
    <div className="page-wrap">
      <div className="page-heading">
        <div>
          <p className="eyebrow">MARKET INTELLIGENCE / DISCOVERY</p>
          <h1>
            Your Relevance <em>Findings</em>
          </h1>
          <p>Temuan pasar yang terhubung dengan fokus risetmu.</p>
        </div>
        <button
          className="button button-secondary"
          onClick={() => void load(true)}
          disabled={loading}
        >
          {!loading && <AppIcon name="refresh" />}
          {loading ? "Memuat…" : "Perbarui temuan"}
        </button>
      </div>
      <div className="context-strip">
        <span className="context-icon">
          <AppIcon name="research" />
        </span>
        <div>
          <strong>Research context</strong>
          <p>
            {profile
              ? (profile.sectors.join(", ") || "Semua sektor") +
                " · " +
                profile.horizon_days +
                " hari"
              : "Memuat profil riset…"}
          </p>
        </div>
        <Link href="/profile" className="detail-link ml-auto">
          Ubah profil →
        </Link>
      </div>
      <dl className="research-stats" aria-label="Ringkasan discovery">
        <div>
          <dt>Universe riset</dt>
          <dd>
            {data?.universe_size ?? "—"}
            <small>aset</small>
          </dd>
        </div>
        <div>
          <dt>Temuan dengan evidence</dt>
          <dd>
            {data?.findings.length ?? "—"}
            <small>temuan</small>
          </dd>
        </div>
        <div>
          <dt>My Assets</dt>
          <dd>
            {profile?.saved_assets.length ?? "—"}
            <small>tersimpan</small>
          </dd>
        </div>
        <div>
          <dt>Rentang riset</dt>
          <dd>
            {profile?.horizon_days ?? "—"}
            <small>hari</small>
          </dd>
        </div>
      </dl>
      <div className="section-heading">
        <h2>
          Market Discovery <span>{data?.findings.length ?? "—"}</span>
        </h2>
        <p>
          {data
            ? data.universe_size + " aset dalam universe"
            : "Menyiapkan evidence"}
        </p>
      </div>
      {!!data?.findings.length && (
        <section className="discovery-controls" aria-label="Filter temuan">
          <label className="discovery-search">
            <span>Cari dalam temuan</span>
            <input
              className="text-input"
              type="search"
              placeholder="Ticker, perusahaan, atau sektor"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <label className="discovery-sort">
            <span>Urutkan</span>
            <select
              className="text-input"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="relevance">Relevansi tertinggi</option>
              <option value="ticker">Ticker A–Z</option>
            </select>
          </label>
          <button
            type="button"
            className="saved-filter"
            aria-pressed={savedOnly}
            onClick={() => setSavedOnly((v) => !v)}
          >
            Hanya tersimpan <span>{profile?.saved_assets.length ?? 0}</span>
          </button>
          <div className="filter-result">
            <span role="status">
              {visibleFindings.length} dari {data.findings.length} temuan
              ditampilkan
            </span>
            {(query || savedOnly || sort !== "relevance") && (
              <button className="detail-link" onClick={clearFilters}>
                Reset filter
              </button>
            )}
          </div>
        </section>
      )}
      {error && (
        <div className="notice" role="alert">
          {error}
        </div>
      )}
      {loading ? (
        <div
          className="skeleton-grid"
          role="status"
          aria-label="Memuat Discovery"
        >
          {[1, 2, 3].map((n) => (
            <div key={n} className="skeleton-card" />
          ))}
        </div>
      ) : (
        data && (
          <>
            {!!data.unavailable_assets.length && (
              <div className="notice">
                {data.unavailable_assets.map(unavailableLabel).join(" · ")}
              </div>
            )}
            {visibleFindings.length ? (
              <div className="finding-grid">
                {visibleFindings.map((f) => (
                  <FindingCard key={f.symbol} finding={f} />
                ))}
              </div>
            ) : (
              <div className="empty-panel">
                <span className="empty-icon">
                  <AppIcon name="search-plus" />
                </span>
                <h2>
                  {data.findings.length
                    ? "Tidak ada temuan yang cocok"
                    : "Belum ada temuan dengan evidence"}
                </h2>
                {data.findings.length > 0 ? (
                  <>
                    <p>
                      Coba ticker atau kata lain, atau hapus filter untuk
                      melihat seluruh temuan yang dimuat.
                    </p>
                    <button
                      className="button button-secondary"
                      onClick={clearFilters}
                    >
                      Tampilkan semua temuan
                    </button>
                  </>
                ) : (
                  <>
                    <p>
                      Periksa ketersediaan data atau sesuaikan konteks risetmu.
                    </p>
                    <Link href="/profile" className="button button-secondary">
                      Ubah research profile
                    </Link>
                  </>
                )}
              </div>
            )}
          </>
        )
      )}
      <p className="page-footnote">
        Research Relevance menggambarkan kesesuaian dengan fokus risetmu. Selalu
        periksa evidence dan periode data.
      </p>
    </div>
  );
}

// components/profile/ProfileForm.tsx
//
// Form profile sesuai FR-01.
//
// REVISI BESAR dari versi lama:
//   - research_focus sekarang ARRAY, dipilih dari 3 nilai tertutup yang
//     TERVERIFIKASI dari response asli: "fundamental", "market_activity",
//     "investor_flow" (sama seperti SignalGroup di lib/types.ts) --
//     BUKAN lagi text bebas seperti "Growth + Market Activity".
//   - horizon sekarang horizon_days: integer 2-90, ditampilkan sebagai
//     slider -- BUKAN lagi 3 pilihan short/medium/long.
//
// CATATAN ASUMSI YANG MASIH BERLAKU (belum dikonfirmasi):
//   - Daftar 11 sektor di bawah pakai klasifikasi IDX-IC (standar BEI).
//     Team 2 sendiri bilang secara eksplisit ini "product configuration,
//     bukan canonical IDX-IC list yang sudah diverifikasi Team 2" --
//     lihat balasan-ke-tim.md. WAJIB dicek sebelum demo.

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Profile, SignalGroup } from "@/lib/types";
import { createProfile, updateProfile, ApiError } from "@/lib/api";
import { setActiveProfileId } from "@/lib/session";

// Klasifikasi IDX-IC (asumsi -- lihat catatan di atas, BELUM dikonfirmasi resmi)
const SECTOR_OPTIONS = [
  "Energy",
  "Basic Materials",
  "Industrials",
  "Consumer Non-Cyclicals",
  "Consumer Cyclicals",
  "Healthcare",
  "Financials",
  "Properties & Real Estate",
  "Technology",
  "Infrastructures",
  "Transportation & Logistics",
] as const;

// TERVERIFIKASI dari response asli (relevance_reason.focus_weights,
// relevance_reason.selected_focus) -- 3 nilai ini persis sama dengan
// SignalGroup.
const RESEARCH_FOCUS_OPTIONS: { value: SignalGroup; label: string }[] = [
  { value: "fundamental", label: "Fundamental" },
  { value: "market_activity", label: "Market Activity" },
  { value: "investor_flow", label: "Investor Flow" },
];

interface ProfileFormProps {
  /** Profile existing untuk mode edit. Kosongkan untuk mode buat baru. */
  initialProfile?: Profile;
}

export function ProfileForm({ initialProfile }: ProfileFormProps) {
  const router = useRouter();
  const [sectors, setSectors] = useState<string[]>(
    initialProfile?.sectors ?? [],
  );
  const [researchFocus, setResearchFocus] = useState<string[]>(
    initialProfile?.research_focus ?? [],
  );
  const [horizonDays, setHorizonDays] = useState<number>(
    initialProfile?.horizon_days ?? 30,
  );
  const [activeStep, setActiveStep] = useState("sectors");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const sameSelection = (a: string[], b: string[]) =>
    [...a].sort().join("|") === [...b].sort().join("|");
  const dirty =
    !sameSelection(sectors, initialProfile?.sectors ?? []) ||
    !sameSelection(researchFocus, initialProfile?.research_focus ?? []) ||
    horizonDays !== (initialProfile?.horizon_days ?? 30);
  function jumpTo(step: string) {
    setActiveStep(step);
    const section = document.getElementById("profile-" + step);
    section?.focus({ preventScroll: true });
    section?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "start",
    });
  }
  function resetChoices() {
    setSectors(initialProfile?.sectors ?? []);
    setResearchFocus(initialProfile?.research_focus ?? []);
    setHorizonDays(initialProfile?.horizon_days ?? 30);
    setSearch("");
    setError(null);
  }

  function toggleSector(sector: string) {
    setError(null);
    setSectors((prev) =>
      prev.includes(sector)
        ? prev.filter((s) => s !== sector)
        : [...prev, sector],
    );
  }

  function toggleFocus(focus: SignalGroup) {
    setError(null);
    setResearchFocus((prev) =>
      prev.includes(focus) ? prev.filter((f) => f !== focus) : [...prev, focus],
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;

    if (sectors.length === 0) {
      setError("Pilih minimal 1 sektor.");
      return;
    }
    if (researchFocus.length === 0) {
      setError("Pilih minimal 1 research focus.");
      return;
    }
    setError(null);
    setSubmitting(true);

    const input = {
      sectors,
      research_focus: researchFocus,
      horizon_days: horizonDays,
    };

    try {
      const profile = initialProfile
        ? await updateProfile(initialProfile.id, input)
        : await createProfile(input);
      setActiveProfileId(profile.id);
      router.push("/discovery");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 0
          ? "Layanan belum terhubung. Pilihanmu tetap ada; coba simpan lagi setelah koneksi tersedia."
          : "Gagal menyimpan profile. Coba lagi.",
      );
      setSubmitting(false);
    }
  }

  const filteredSectors = SECTOR_OPTIONS.filter((s) =>
    s.toLowerCase().includes(search.toLowerCase()),
  );
  const ready = sectors.length > 0 && researchFocus.length > 0;
  const descriptions: Record<string, string> = {
    fundamental: "Pendapatan, laba, dan pertumbuhan perusahaan.",
    market_activity: "Pergerakan harga dan aktivitas volume transaksi.",
    investor_flow: "Arus transaksi investor asing dan keseimbangannya.",
  };
  return (
    <form onSubmit={handleSubmit} className="profile-grid">
      <nav className="profile-step-nav" aria-label="Bagian profil">
        {[
          { id: "sectors", label: "Sektor", complete: sectors.length > 0 },
          { id: "focus", label: "Fokus", complete: researchFocus.length > 0 },
          { id: "horizon", label: "Rentang waktu", complete: true },
        ].map((step, i) => (
          <button
            type="button"
            key={step.id}
            disabled={submitting}
            aria-current={activeStep === step.id ? "step" : undefined}
            onClick={() => jumpTo(step.id)}
          >
            <span aria-hidden="true">{step.complete ? "✓" : `0${i + 1}`}</span>
            {step.label}
          </button>
        ))}
        <button
          type="button"
          className="summary-jump"
          onClick={() => jumpTo("summary")}
        >
          Ringkasan <span aria-hidden="true">↗</span>
        </button>
      </nav>
      <div className="profile-sections">
        <fieldset
          id="profile-sectors"
          tabIndex={-1}
          onFocusCapture={() => setActiveStep("sectors")}
          className="profile-panel"
          disabled={submitting}
        >
          <legend className="sr-only">Sektor yang diminati</legend>
          <div className="profile-section-title">
            <span className="step-number">01</span>
            <div>
              <h2>Pilih sektor risetmu</h2>
              <p>Pilih satu atau lebih sektor yang ingin kamu telusuri.</p>
            </div>
            <span className="selection-count">{sectors.length} dipilih</span>
          </div>
          <input
            className="text-input sector-search"
            type="search"
            aria-label="Cari sektor"
            placeholder="Cari sektor, misalnya Financials"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="sector-options">
            {filteredSectors.map((sector) => (
              <button
                key={sector}
                type="button"
                aria-pressed={sectors.includes(sector)}
                className="sector-option"
                onClick={() => toggleSector(sector)}
              >
                <span>{sector}</span>
                <span aria-hidden="true" className="selection-mark">
                  {sectors.includes(sector) ? "✓" : "+"}
                </span>
              </button>
            ))}
          </div>
          {!filteredSectors.length && (
            <p className="profile-hint">
              Tidak ada sektor yang cocok. Coba kata lain.
            </p>
          )}
          {!!sectors.length && (
            <button
              type="button"
              className="detail-link mt-4"
              onClick={() => setSectors([])}
            >
              Hapus pilihan sektor
            </button>
          )}
        </fieldset>
        <fieldset
          id="profile-focus"
          tabIndex={-1}
          onFocusCapture={() => setActiveStep("focus")}
          className="profile-panel"
          disabled={submitting}
        >
          <legend className="sr-only">Research focus</legend>
          <div className="profile-section-title">
            <span className="step-number">02</span>
            <div>
              <h2>Apa yang ingin kamu pahami?</h2>
              <p>Kamu bisa memilih lebih dari satu fokus riset.</p>
            </div>
          </div>
          <div className="focus-options">
            {RESEARCH_FOCUS_OPTIONS.map((opt) => (
              <button
                type="button"
                key={opt.value}
                aria-pressed={researchFocus.includes(opt.value)}
                onClick={() => toggleFocus(opt.value)}
                className="focus-option"
              >
                <span className="focus-option-top">
                  <span className="selection-mark" aria-hidden="true">
                    {researchFocus.includes(opt.value) ? "✓" : "+"}
                  </span>
                </span>
                <strong>{opt.label}</strong>
                <span>{descriptions[opt.value]}</span>
              </button>
            ))}
          </div>
        </fieldset>
        <fieldset
          id="profile-horizon"
          tabIndex={-1}
          onFocusCapture={() => setActiveStep("horizon")}
          className="profile-panel"
          disabled={submitting}
        >
          <legend className="sr-only">Research horizon</legend>
          <div className="profile-section-title">
            <span className="step-number">03</span>
            <div>
              <h2>Tentukan rentang waktu</h2>
              <p>Rentang data transaksi yang dipakai untuk risetmu.</p>
            </div>
            <output className="horizon-value" htmlFor="horizonDays">
              {horizonDays}
              <small>hari</small>
            </output>
          </div>
          <div className="horizon-presets">
            {[7, 14, 30, 60, 90].map((days) => (
              <button
                type="button"
                key={days}
                aria-pressed={horizonDays === days}
                onClick={() => setHorizonDays(days)}
              >
                {days} hari
              </button>
            ))}
          </div>
          <label htmlFor="horizonDays" className="sr-only">
            Rentang waktu riset
          </label>
          <input
            id="horizonDays"
            type="range"
            min={2}
            max={90}
            value={horizonDays}
            onChange={(e) => setHorizonDays(Number(e.target.value))}
            className="horizon-slider"
          />
          <div className="range-labels">
            <span>2 hari</span>
            <span>90 hari</span>
          </div>
        </fieldset>
      </div>
      <aside
        id="profile-summary"
        tabIndex={-1}
        className="profile-summary"
        aria-label="Ringkasan profil"
      >
        <h2>Ringkasan profil</h2>
        <p className="profile-hint">
          Pilihanmu membantu menyesuaikan relevansi temuan di Discovery.
        </p>
        <div
          className="profile-progress"
          aria-label={
            ready ? "Profil siap disimpan" : "Lengkapi sektor dan fokus"
          }
        >
          <span className={sectors.length ? "complete" : ""} />
          <span className={researchFocus.length ? "complete" : ""} />
          <span className="complete" />
        </div>
        <dl className="profile-summary-list">
          <div>
            <dt>
              Sektor pilihan{" "}
              <button
                type="button"
                className="summary-edit"
                onClick={() => jumpTo("sectors")}
              >
                Ubah sektor
              </button>
            </dt>
            <dd className="summary-chips">
              {sectors.length
                ? sectors.map((sector) => (
                    <button
                      type="button"
                      key={sector}
                      disabled={submitting}
                      aria-label={"Hapus sektor " + sector}
                      onClick={() => toggleSector(sector)}
                    >
                      {sector} <span aria-hidden="true">×</span>
                    </button>
                  ))
                : "Belum dipilih"}
            </dd>
          </div>
          <div>
            <dt>
              Fokus riset{" "}
              <button
                type="button"
                className="summary-edit"
                onClick={() => jumpTo("focus")}
              >
                Ubah fokus
              </button>
            </dt>
            <dd>
              {RESEARCH_FOCUS_OPTIONS.filter((o) =>
                researchFocus.includes(o.value),
              )
                .map((o) => o.label)
                .join(" · ") || "Belum dipilih"}
            </dd>
          </div>
          <div>
            <dt>
              Rentang waktu{" "}
              <button
                type="button"
                className="summary-edit"
                onClick={() => jumpTo("horizon")}
              >
                Ubah waktu
              </button>
            </dt>
            <dd>{horizonDays} hari</dd>
          </div>
        </dl>
        <div
          className="draft-status"
          role="status"
          aria-label="Status penyimpanan profil"
        >
          <span className={dirty ? "draft-dot changed" : "draft-dot"} />
          {submitting
            ? "Menyimpan profil…"
            : dirty
              ? "Perubahan belum disimpan"
              : initialProfile
                ? "Sesuai profil tersimpan"
                : "Profil belum disimpan"}
        </div>
        {dirty && (
          <button
            type="button"
            disabled={submitting}
            className="detail-link reset-profile"
            onClick={resetChoices}
          >
            {initialProfile
              ? "Kembalikan pilihan tersimpan"
              : "Mulai ulang pilihan"}
          </button>
        )}
        {error && (
          <p className="notice" role="alert">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="button button-primary profile-submit"
        >
          {submitting
            ? "Menyimpan…"
            : initialProfile
              ? "Simpan perubahan →"
              : "Simpan & buka Discovery →"}
        </button>
        <p className="profile-hint summary-footnote">
          {ready
            ? "Siap. Kamu bisa mengubah pilihan ini kapan saja."
            : "Pilih minimal satu sektor dan satu fokus untuk mulai."}
        </p>
      </aside>
    </form>
  );
}

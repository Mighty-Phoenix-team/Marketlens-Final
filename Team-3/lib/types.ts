// Team 2 API contracts. Evidence fields were checked against the backend
// model; live populated responses still require integration verification.
// Keep API snake_case names unchanged.

// --- Finding ---------------------------------------------------------

export type SignalGroup = "fundamental" | "market_activity" | "investor_flow";

/** Measured evidence from the Team 2 finding model. */
export interface EvidenceItem {
  group: SignalGroup;
  metric: string;
  /** Angka mentah (mis. 0.0844), BUKAN string yang sudah diformat. */
  value: number;
  period: string;
  method: string;
  source: string | null;
  baseline: number | null;
  strength: number;
  observed_at: string | null;
  retrieved_at: string;
}

/**
 * Detail penuh perhitungan Research Relevance untuk satu finding.
 * TERVERIFIKASI dari response asli (finding_detail.json, my_asset.json,
 * explanation_context.json, explain_asset.json — bentuknya identik di
 * keempatnya).
 */
export interface RelevanceReason {
  selected_focus: string[];
  matched_groups: string[];
  sector_match: boolean;
  group_strength: {
    fundamental: number;
    market_activity: number;
    investor_flow: number;
  };
  availability_factor: number;
  sector_factor: number;
  focus_weights: {
    fundamental: number;
    market_activity: number;
    investor_flow: number;
  };
}

/**
 * Struktur inti sebuah finding. TERVERIFIKASI dari finding_detail.json
 * dan my_asset.json (bentuknya identik di keduanya, sesuai prinsip
 * shared engine FR-08).
 */
export interface Finding {
  id: string;
  symbol: string;
  company_name: string;

  /** Bisa null — terlihat di response asli saat company report gagal diambil. */
  sector: string | null;

  /** Skor 0-10. BUKAN investment score (PRD section 6.2). */
  research_relevance: number;

  /**
   * PENTING: ini array of string, BUKAN string tunggal seperti asumsi
   * lama. Contoh nyata: ["Data unavailable for a measured finding."]
   */
  observation: string[];

  /** Evidence entries retain their metric, period, method and provenance. */
  evidence: EvidenceItem[];

  signal_groups: SignalGroup[];

  /**
   * PENTING: ini object terstruktur, BUKAN string[] seperti asumsi lama
   * (whyThisAppeared). Ditampilkan sebagai "Why This Appeared" di UI,
   * tapi field ini sendiri jauh lebih detail dari sekadar daftar alasan
   * -- ini breakdown penuh formula Research Relevance.
   */
  relevance_reason: RelevanceReason;

  reasoning: string;
  method: string;
  retrieved_at: string;
  limitations: string[];
  source_endpoints: string[];
}

// --- Discovery & My Assets response wrappers --------------------------

/**
 * Response GET /api/profiles/{profile_id}/discovery.
 * TERVERIFIKASI dari discovery.json.
 */
export type UnavailableAsset = { symbol: string; error: string } | string;

export interface DiscoveryResponse {
  title: string;
  findings: Finding[];
  unavailable_assets: UnavailableAsset[];
  universe_size: number;
}

/**
 * Response GET /api/profiles/{profile_id}/assets (My Assets).
 * TERVERIFIKASI dari my_asset.json -- BUKAN array of Finding polos,
 * ini object wrapper dengan unavailable_assets terpisah.
 */
export interface MyAssetsResponse {
  findings: Finding[];
  unavailable_assets: UnavailableAsset[];
}

// --- Profile -----------------------------------------------------------

/**
 * Research profile milik user (FR-01). TERVERIFIKASI dari
 * create_profile.json / get_profile.json / save_asset.json (bentuknya
 * identik di ketiganya).
 */
export interface Profile {
  id: string;
  sectors: string[];

  /**
   * PENTING: ini array of string, BUKAN string tunggal seperti asumsi
   * lama (mis. "Growth + Market Activity"). Contoh nyata: ["fundamental"].
   * Nilai yang didukung sejauh ini: "fundamental", "market_activity",
   * "investor_flow" (sama seperti SignalGroup).
   */
  research_focus: string[];

  /**
   * PENTING: integer jumlah hari (2-90), BUKAN enum
   * "short"|"medium"|"long" seperti asumsi lama.
   */
  horizon_days: number;

  created_at: string;

  /** Array of ticker string, BUKAN object SavedAsset terpisah. */
  saved_assets: string[];
}

// --- Explain Finding -----------------------------------------------------

/**
 * Response POST /api/profiles/{profile_id}/assets/{symbol}/explanation.
 * TERVERIFIKASI dari explain_asset.json.
 */
export interface ExplainAssetResponse {
  finding: Finding;
  explanation: {
    summary: string;
    why_relevant: string;
    evidence_summary: string[];
    limitations: string[];
    next_research_questions: string[];
  };
}

/**
 * Response GET /api/profiles/{profile_id}/assets/{symbol}/explanation-context.
 * TERVERIFIKASI dari explanation_context.json.
 *
 * CATATAN: ini adalah payload INTERNAL yang dipakai backend untuk
 * membangun prompt AI (lihat evidence_boundary.instructions) -- bukan
 * untuk ditampilkan langsung ke user. Frontend kemungkinan besar TIDAK
 * PERNAH perlu memanggil endpoint ini secara langsung; disertakan di
 * sini untuk referensi/dokumentasi, bukan karena akan dipakai UI.
 */
export interface ExplanationContextResponse {
  research_profile: {
    sectors: string[];
    research_focus: string[];
    horizon_days: number;
  };
  finding: Omit<Finding, "id" | "signal_groups">;
  evidence_boundary: {
    scope: string;
    causal_explanation_available: boolean;
    document_context_available: boolean;
    instructions: string[];
  };
}

export interface ComparisonResponse {
  symbols: string[];
  assets: {
    symbol: string;
    company_name: string;
    research_relevance: number;
    signal_groups: string[];
    methodology_version: string | null;
    limitations: string[];
  }[];
  metrics: {
    metric: string;
    values: Record<string, number | null>;
    missing_symbols: string[];
    group: string | null;
    evidence_by_symbol: Record<
      string,
      (EvidenceItem & { unit?: string | null }) | null
    >;
    period_status: string;
  }[];
  shared_signal_groups: string[];
  limitations: string[];
}

"use client";

// components/finding/FindingDetail.tsx

import { useState } from "react";
import Link from "next/link";
import { SaveAssetButton } from "@/components/assets/SaveAssetButton";
import type { Finding } from "@/lib/types";
import { ResearchRelevanceBadge } from "./ResearchRelevanceBadge";
import { EvidenceList } from "./EvidenceList";
import { explainAsset, ApiError } from "@/lib/api";
import type { ExplainAssetResponse } from "@/lib/types";
import { LoadingState } from "@/components/states/LoadingState";
import { ErrorState } from "@/components/states/ErrorState";
import { AppIcon } from "@/components/ui/AppIcon";

interface FindingDetailProps {
  finding: Finding;
  profileId: string;
}

function formatSignalGroup(group: string): string {
  switch (group) {
    case "fundamental":
      return "Fundamental";
    case "market_activity":
      return "Market Activity";
    case "investor_flow":
      return "Investor Flow";
    default:
      return group;
  }
}

export function FindingDetail({ finding, profileId }: FindingDetailProps) {
  const [explanation, setExplanation] = useState<
    ExplainAssetResponse["explanation"] | null
  >(null);
  const [explainState, setExplainState] = useState<
    "idle" | "loading" | "error"
  >("idle");
  const [explainError, setExplainError] = useState<string | null>(null);

  async function handleExplainFinding() {
    setExplainState("loading");
    setExplainError(null);
    try {
      const result = await explainAsset(profileId, finding.symbol);
      setExplanation(result.explanation);
      setExplainState("idle");
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 0
          ? "Tidak bisa terhubung ke server."
          : "AI explanation tidak tersedia saat ini.";
      setExplainError(message);
      setExplainState("error");
    }
  }

  return (
    <div className="detail-page">
      <div className="detail-toolbar">
        <Link href="/discovery" className="detail-link">
          <AppIcon className="inline-icon" name="arrow-left" /> Discovery
        </Link>
        <SaveAssetButton symbol={finding.symbol} />
      </div>

      {/* Entity */}
      <div className="detail-identity">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-faint">
            {finding.symbol}
          </p>
          <h1 className="font-serif text-2xl font-semibold text-text">
            {finding.company_name}
          </h1>
          {finding.sector && (
            <p className="mt-1 text-sm text-text-muted">{finding.sector}</p>
          )}
        </div>
        <ResearchRelevanceBadge score={finding.research_relevance} />
      </div>

      {/* Why This Appeared (Paling atas, non-dropdown) */}
      <section>
        <h2 className="text-sm font-semibold text-text">Why This Appeared</h2>
        <div className="mt-3 space-y-3 text-sm">
          <div>
            <span className="text-text-muted">Fokus riset dipilih: </span>
            <span className="text-text">
              {finding.relevance_reason.selected_focus
                .map(formatSignalGroup)
                .join(", ") || "-"}
            </span>
          </div>
          <div>
            <span className="text-text-muted">Kelompok yang cocok: </span>
            <span className="text-text">
              {finding.relevance_reason.matched_groups.length > 0
                ? finding.relevance_reason.matched_groups
                    .map(formatSignalGroup)
                    .join(", ")
                : "Tidak ada"}
            </span>
          </div>
          <div>
            <span className="text-text-muted">
              Sektor cocok dengan profile:{" "}
            </span>
            <span className="text-text">
              {finding.relevance_reason.sector_match ? "Ya" : "Tidak"}
            </span>
          </div>
          <div>
            <span className="mb-1 block text-text-muted">
              Kekuatan evidence per kelompok:
            </span>
            <ul className="ml-4 list-inside list-disc text-text">
              {Object.entries(finding.relevance_reason.group_strength).map(
                ([group, strength]) => (
                  <li key={group}>
                    {formatSignalGroup(group)}: {strength.toFixed(2)}
                  </li>
                ),
              )}
            </ul>
          </div>
        </div>
      </section>

      {/* Explain Finding */}
      <section className="border-t border-border pt-6">
        <h2 className="text-sm font-semibold text-text">Explain Finding</h2>

        {explainState === "idle" && !explanation && (
          <button
            onClick={handleExplainFinding}
            className="button button-primary mt-3"
          >
            Explain Finding
          </button>
        )}

        {explainState === "loading" && (
          <LoadingState label="Menghasilkan penjelasan..." />
        )}

        {explainState === "error" && (
          <div className="mt-3">
            <ErrorState
              title="AI explanation tidak tersedia"
              description={explainError ?? undefined}
              onRetry={handleExplainFinding}
            />
          </div>
        )}

        {explanation && (
          <div className="mt-3 space-y-4">
            <div>
              <h3 className="text-xs font-semibold text-text-muted">Summary</h3>
              <p className="mt-1 text-sm text-text">{explanation.summary}</p>
            </div>
            <div>
              <h3 className="text-xs font-semibold text-text-muted">
                Why Relevant
              </h3>
              <p className="mt-1 text-sm text-text">
                {explanation.why_relevant}
              </p>
            </div>
            <div>
              <h3 className="text-xs font-semibold text-text-muted">
                Evidence Used
              </h3>
              <ul className="mt-1 list-inside list-disc text-sm text-text">
                {explanation.evidence_summary.map((line, idx) => (
                  <li key={idx}>{line}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-xs font-semibold text-text-muted">
                Limitations
              </h3>
              <ul className="mt-1 list-inside list-disc text-sm text-text">
                {explanation.limitations.map((line, idx) => (
                  <li key={idx}>{line}</li>
                ))}
              </ul>
            </div>
            {explanation.next_research_questions.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-text-muted">
                  Further Research
                </h3>
                <ul className="mt-1 list-inside list-disc text-sm text-text">
                  {explanation.next_research_questions.map((q, idx) => (
                    <li key={idx}>{q}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Dropdown Sections (Di bawah Explain Finding) */}
      <div className="mt-6 space-y-4 border-t border-border pt-6">
        {/* Observation */}
        <details className="group cursor-pointer">
          <summary className="text-sm font-semibold text-text select-none list-none flex items-center justify-between">
            <span>Observation</span>
            <span className="text-xs text-text-muted transition-transform group-open:rotate-180">
              ▼
            </span>
          </summary>
          <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-text-muted">
            {finding.observation.map((line, idx) => (
              <li key={idx}>{line}</li>
            ))}
          </ul>
        </details>

        {/* Evidence */}
        <details className="group cursor-pointer">
          <summary className="text-sm font-semibold text-text select-none list-none flex items-center justify-between">
            <span>Evidence</span>
            <span className="text-xs text-text-muted transition-transform group-open:rotate-180">
              ▼
            </span>
          </summary>
          <div className="mt-3">
            <EvidenceList evidence={finding.evidence} mode="full" />
          </div>
        </details>

        {/* Method & Reasoning */}
        <details className="group cursor-pointer">
          <summary className="text-sm font-semibold text-text select-none list-none flex items-center justify-between">
            <span>Method &amp; Reasoning</span>
            <span className="text-xs text-text-muted transition-transform group-open:rotate-180">
              ▼
            </span>
          </summary>
          <p className="mt-2 text-sm text-text-muted">{finding.reasoning}</p>
          <p className="mt-2 font-mono text-xs text-text-faint">
            {finding.method}
          </p>
        </details>

        {/* Limitations */}
        <details className="group cursor-pointer">
          <summary className="text-sm font-semibold text-text select-none list-none flex items-center justify-between">
            <span>Limitations</span>
            <span className="text-xs text-text-muted transition-transform group-open:rotate-180">
              ▼
            </span>
          </summary>
          <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-text-muted">
            {finding.limitations.map((line, idx) => (
              <li key={idx}>{line}</li>
            ))}
          </ul>
        </details>

        {/* Sources */}
        <details className="group cursor-pointer">
          <summary className="text-sm font-semibold text-text select-none list-none flex items-center justify-between">
            <span>Sources</span>
            <span className="text-xs text-text-muted transition-transform group-open:rotate-180">
              ▼
            </span>
          </summary>
          <ul className="mt-2 space-y-1 text-sm text-text-faint">
            {finding.source_endpoints.map((url, idx) => (
              <li key={idx}>{url}</li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-text-faint">
            Diambil pada: {new Date(finding.retrieved_at).toLocaleString("id-ID")}
          </p>
        </details>
      </div>
    </div>
  );
}
import Link from "next/link";
import type { Finding } from "@/lib/types";
import { EvidenceList } from "./EvidenceList";
import { SaveAssetButton } from "@/components/assets/SaveAssetButton";
import { metricLabel } from "@/lib/format";
import type { ReactNode } from "react";
import { AppIcon } from "@/components/ui/AppIcon";

export function FindingCard({
  finding,
  action,
}: {
  finding: Finding;
  action?: ReactNode;
}) {
  const detailHref = "/finding/" + encodeURIComponent(finding.symbol);
  return (
    <article className="finding-card" aria-label={finding.symbol}>
      <div className="finding-identity">
        <Link href={detailHref} className="finding-symbol">
          {finding.symbol}{" "}
          <AppIcon className="inline-icon" name="arrow-up-right" />
        </Link>
        <p className="finding-company">{finding.company_name}</p>
        <div className="finding-meta">
          <span>{finding.sector || "Sektor belum tersedia"}</span>
          <span>{finding.evidence.length} evidence</span>
        </div>
        <p className="finding-reason">
          <span>Why This Appeared</span>
          {finding.relevance_reason.matched_groups.length
            ? "Sesuai fokus " +
              finding.relevance_reason.matched_groups
                .map(metricLabel)
                .join(", ") +
              "."
            : "Lihat detail untuk konteks riset dan ketersediaan data."}
        </p>
      </div>
      <div className="relevance">
        <span>Research Relevance</span>
        <strong>
          {finding.research_relevance.toFixed(2)}
          <small> / 10</small>
        </strong>
        <span>Kesesuaian fokus riset</span>
      </div>
      <div className="card-evidence">
        <EvidenceList
          evidence={finding.evidence}
          mode="preview"
          previewCount={3}
        />
      </div>
      <div className="card-actions">
        {action ?? <SaveAssetButton symbol={finding.symbol} />}
        <Link href={detailHref} className="detail-link" aria-label="Detail →">
          Detail <AppIcon className="inline-icon" name="arrow-right" />
        </Link>
      </div>
    </article>
  );
}

import type { EvidenceItem } from "@/lib/types";
import { metricLabel, metricValue } from "@/lib/format";
export function EvidenceList({
  evidence,
  mode,
  previewCount = 3,
}: {
  evidence: EvidenceItem[];
  mode: "preview" | "full";
  previewCount?: number;
}) {
  const visible =
    mode === "preview" ? evidence.slice(0, previewCount) : evidence;
  if (!evidence.length)
    return (
      <p className="text-sm text-text-muted">Data evidence belum tersedia.</p>
    );
  return (
    <div className={"evidence-list evidence-" + mode}>
      <ul>
        {visible.map((item, index) => (
          <li key={item.metric + index}>
            <div className="evidence-value">
              <span className="text-text-muted">
                {metricLabel(item.metric)}
              </span>
              <strong className="whitespace-nowrap tabular-nums">
                {metricValue(item.metric, item.value)}
              </strong>
            </div>
            {mode === "preview" && (
              <p className="evidence-period">{item.period}</p>
            )}
            {mode === "full" && (
              <div className="mt-1 space-y-1 text-xs leading-relaxed text-text-muted">
                <p>Periode: {item.period}</p>
                <p>{item.method}</p>
                {item.source && /^https?:\/\//.test(item.source) && (
                  <a
                    href={item.source}
                    target="_blank"
                    rel="noreferrer"
                    className="text-accent underline"
                  >
                    Sumber evidence ↗
                  </a>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
      {mode === "preview" && evidence.length > visible.length && (
        <p className="mt-3 text-xs text-text-faint">
          +{evidence.length - visible.length} evidence di detail
        </p>
      )}
    </div>
  );
}

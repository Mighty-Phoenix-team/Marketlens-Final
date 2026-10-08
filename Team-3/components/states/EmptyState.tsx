// components/states/EmptyState.tsx
//
// State kosong generik — dipakai saat request BERHASIL tapi hasilnya
// nol item (mis. Discovery tanpa finding, My Assets tanpa saved asset).
//
// BEDA dengan "Data unavailable" (itu di level 1 field evidence, lihat
// EvidenceList) dan BEDA dengan ErrorState (itu untuk request GAGAL).

interface EmptyStateProps {
  title: string;
  description?: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="empty-panel">
      <h2>{title}</h2>
      {description && (
        <p className="mt-1 text-sm text-text-faint">{description}</p>
      )}
    </div>
  );
}

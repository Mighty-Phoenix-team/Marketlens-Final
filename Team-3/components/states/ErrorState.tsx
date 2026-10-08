// components/states/ErrorState.tsx
//
// Dipakai saat request GAGAL total (network error, 4xx/5xx dari
// Sectors API nanti). BEDA dari EmptyState (request berhasil, 0 item)
// dan BEDA dari "Data unavailable" di EvidenceList (request berhasil,
// 1 field kosong).

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Gagal memuat data",
  description = "Terjadi kesalahan saat mengambil data. Coba lagi.",
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="notice notice-error" role="alert">
      <p className="font-semibold">{title}</p>
      <p className="mt-1 text-sm">{description}</p>
      {onRetry && (
        <button onClick={onRetry} className="button button-secondary mt-3">
          Coba lagi
        </button>
      )}
    </div>
  );
}

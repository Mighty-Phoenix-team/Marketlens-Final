// components/states/LoadingState.tsx
//
// Dipakai untuk async fetch yang sesungguhnya (mis. nanti saat
// lib/api.ts sudah manggil Sectors API). JANGAN dipakai untuk baca
// localStorage atau operasi sinkron lain yang selesai dalam 1 tick —
// itu cuma bikin flash tanpa guna.

interface LoadingStateProps {
  label?: string;
}

export function LoadingState({ label = "Memuat..." }: LoadingStateProps) {
  return (
    <div className="flex items-center justify-center gap-2 p-8" role="status">
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-accent"
      />
      <span className="text-sm text-text-muted">{label}</span>
    </div>
  );
}

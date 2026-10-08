// components/finding/ResearchRelevanceBadge.tsx
//
// Menampilkan skor Research Relevance (0-10).
// PENTING (PRD section 6.2): angka ini BUKAN investment score.
// Jangan tambahkan warna hijau/merah yang menyiratkan "bagus/buruk"
// seperti indikator saham pada umumnya — itu bisa disalahartikan
// sebagai sinyal beli/jual, melanggar AC-07.

interface ResearchRelevanceBadgeProps {
  score: number; // 0-10
}

export function ResearchRelevanceBadge({ score }: ResearchRelevanceBadgeProps) {
  return (
    <div className="relevance">
      <span>Research Relevance</span>
      <strong>
        {score.toFixed(2)}
        <small> / 10</small>
      </strong>
      <span>Kesesuaian fokus riset</span>
    </div>
  );
}

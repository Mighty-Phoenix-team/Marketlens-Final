import type { NextConfig } from "next";

// Next.js (sejak versi ~15.5) memblokir request ke aset dev internal
// (/_next/*) dari origin selain localhost secara default — ini fitur
// keamanan, BUKAN bug (lihat CVE-2025-48068). Tanpa config ini, halaman
// yang diakses lewat network link (mis. http://192.168.x.x:3000) akan
// tampil putih total karena browser gagal memuat JS untuk hydration,
// walau HTML dasarnya tetap terkirim (200 OK) — makanya gejalanya
// membingungkan: server tidak error, tapi halaman kosong.
//
// PENTING: `allowedDevOrigins` TIDAK mendukung notasi CIDR/range
// (mis. "192.168.1.0/24" TIDAK akan berfungsi) — hanya menerima
// hostname/IP literal atau wildcard subdomain (mis. "*.local-origin.dev").
// Ganti IP di bawah dengan IP lokal mesin kamu PERSIS seperti yang
// muncul di terminal saat `npm run dev`, baris "Network: http://<IP>:3000".
// Kalau IP kamu berubah (ganti WiFi, pindah jaringan, dsb), update lagi
// baris ini — ini memang konfigurasi yang terikat ke mesin masing-masing,
// bukan sesuatu yang bisa "sekali set selamanya".
const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "192.168.1.6"
  ],
};

export default nextConfig;

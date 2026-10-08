# MarketLens Team-2: Comparison + Explain Finding

Dasar: Team-2-forzip(1).zip milik pengguna (P1, prompt 1–21, timeout dashboard 120 detik)
Digabung dengan: team-2-comparison.zip milik rekan (Watchlist vs Discovery + comparison engine).
API versi 0.4.0; metodologi tetap 2.1-income. Team-1 P1 tetap dipakai.

## Pasang di project lama

Ini satu folder Team-2 lengkap. Tetap merge ke project lama agar konfigurasi, virtual environment,
dan database lokal tetap tersedia. Jangan menjalankan folder hasil extract sebagai project terpisah.

1. Matikan terminal API Team-2 dan terminal Streamlit dengan Ctrl+C. Team-1 boleh tetap berjalan.
2. Backup folder Team-2 lama.
3. Copy folder Team-2 dari ZIP ke folder MarketLens-Stage1 lama, sejajar Team-1.
4. Pilih Replace untuk file dengan nama yang sama. Jangan hapus folder Team-2 lama.
   Paket tidak berisi .env, .venv, database, atau API key. File yang tidak disertakan tetap ada.
5. Dari terminal di Team-2 lama jalankan:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\verify_update.py
```

Dependency google-genai minimum 2.26 ditentukan dari versi SDK yang dipakai dalam pengujian.
verify_update.py memakai fixture dan provider simulasi: Sectors 0 calls, Gemini 0 calls.
Baris `reason=timeout` dalam tes ini sengaja dibuat untuk menguji fallback, bukan error API live.
Output akhirnya harus PASS untuk Comparison, cache, dan timeout.

## Jalankan server

Terminal API Team-2, dari folder Team-2 lama:

```powershell
$env:MARKETLENS_ASSET_API_BASE_URL = "http://127.0.0.1:8000"
$env:MARKETLENS_DISCOVERY_UNIVERSE = "BBCA"
.\.venv\Scripts\python.exe -m uvicorn marketlens.api:app --host 127.0.0.1 --port 8001
```

Terminal Streamlit terpisah, dari folder Team-2 lama:

```powershell
$env:MARKETLENS_API_BASE_URL = "http://127.0.0.1:8001"
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py
```

GEMINI_MODEL dan GEMINI_API_KEY tetap diambil dari .env pengguna; tidak perlu key baru.
Browser: http://localhost:8501. API docs: http://127.0.0.1:8001/docs.

## Smoke test lokal yang hemat request

1. Pilih valuation, profitability, income dan Apply profile. Buka BBCA.
2. Explain finding sekali. Lihat Explanation source dan expander Response timing.
3. Untuk mengecek cache, Back -> buka BBCA lagi -> Explain sekali lagi segera, tanpa mengubah profil.
   Jika evidence/timestamp masih sama, caption menunjukkan penjelasan digunakan kembali.
   Cache hilang setelah restart API. Data baru atau profil berbeda menghasilkan request baru.
4. Buka Comparison untuk Watchlist vs Discovery. Simpan BBCA melalui fitur My Assets bila belum disimpan.
5. Tabel Compare evidence butuh minimal dua aset yang berhasil dimuat.
   Tambahkan satu ticker lain, misalnya BMRI, melalui My Assets. Data live ticker baru bisa memakai kredit Sectors.
   Biarkan universe BBCA untuk smoke test kecil; saved assets juga masuk Comparison.
6. Pilih BBCA dan BMRI, lalu Compare selected evidence. Periksa Valuation, Quality, Income,
   satuan %, ×, pp, serta expander periode/metode/sumber. Comparison tidak memanggil Gemini.

Jangan menilai nilai BBCA vs TEST dalam verify_update sebagai perbandingan pasar nyata:
TEST adalah salinan sintetis fixture untuk pengujian. Fixture menggabungkan capture report P0 1 Oktober
serta dividend 2 Oktober, dengan provenance terpisah. Market/foreign-flow tidak ditambahkan ke fixture itu.

## Perubahan yang disertakan

- Menu Watchlist vs Discovery dari rekan digabung tanpa menimpa P0/P1, pilihan fokus, fallback,
  format unit, dan aturan prompt 1–21 pengguna.
- Schema relevance_reason menerima objek P1; perbaikan signal_group -> signal_groups, dengan alias lama tetap ada.
- Endpoint GET /api/profiles/{id}/comparison untuk watchlist vs discovery; POST pada path yang sama
  menerima {"symbols":["BBCA","BMRI"]} untuk tabel metrik. API maksimum 10, UI maksimum 4 ticker.
- Comparison menyimpan evidence lengkap per ticker: periode, unit, baseline, metode, source, retrieved_at.
  Nilai kosong/nonfinite bukan nol. Label periode yang sama tidak membuktikan basis perhitungan setara.
  Tidak ada pemenang investasi atau selisih rasio lintas perusahaan yang diasumsikan sebanding.
- Aset yang gagal dimuat muncul sebagai unavailable_assets; hitungan watchlist memuat aset berhasil saja,
  saved_asset_count memberi jumlah aset tersimpan sebenarnya. Universe dihapus duplikatnya.
- Engine/metodologi/normalisasi P0 dan Income tidak diubah. Skor dalam Finding dan Comparison memakai engine yang sama.
- Explain memakai SDK async, deadline Gemini default 60 detik, satu percobaan HTTP tanpa retry otomatis.
  Pengambilan asset dibatasi 20 detik; dashboard explanation menunggu hingga 120 detik.
  Deadline membatalkan request lokal; bukan jaminan pemrosesan di server provider langsung berhenti.
- Cache penjelasan di memori maksimal 15 menit/256 entri. Seluruh evidence/timestamp/profil/metodologi,
  model/prompt/schema menjadi bagian identitas cache. Fetch ulang asset setelah TTL 5 menit biasanya
  menghasilkan timestamp baru sehingga cache penjelasan dibatalkan. Restart juga mengosongkan cache.
- Request identik yang bersamaan berbagi satu generasi. Maksimal empat generasi berbeda berjalan sekaligus.
- Fallback disimpan 30 detik untuk menghindari percobaan berulang cepat. UI menampilkan kategori penyebab
  seperti timeout, rate_limited, missing_api_key, invalid_response, atau provider_error.
- explanation_meta ditambahkan tanpa menghapus finding, explanation, ai_explanation, explanation_source.
  Memuat asset_seconds, generation_seconds, total_seconds, cache_hit, coalesced, generated_at, reason, provider_status.
- Payload model menghapus teks observasi duplikat dan menggabungkan metadata sumber berulang.
  Fixture 24 metrik: 27.652 -> 15.424 karakter (~44,2% lebih pendek), bukan ukuran token atau janji percepatan live.
  Semua nilai, periode, unit, baseline, metode, sumber, dan limitations tetap tersedia.
- .env dibaca dari root Team-2. CORS frontend rekan tetap didukung untuk localhost:3000;
  alamat LAN pribadi rekan tidak ditanamkan. Ubah MARKETLENS_CORS_ORIGINS bila frontend perlu origin lain.

## Konfigurasi opsional

Tanpa mengedit .env, default sudah aktif. Bila diperlukan, pengaturan berikut dibaca saat runtime/restart:

| Variabel | Default | Batas |
| --- | --- | --- |
| MARKETLENS_EXPLANATION_TIMEOUT_SECONDS | 60 | 1–85 detik |
| MARKETLENS_EXPLANATION_CACHE_TTL_SECONDS | 900 | 0–3600 detik; 0 menonaktifkan cache |
| MARKETLENS_CORS_ORIGINS | http://localhost:3000,http://127.0.0.1:3000 | daftar origin dipisah koma |

## Hasil pengujian

43 tes lolos: tes pengguna, tes Comparison rekan, serta regresi integrasi P1, cache, deadline,
pembatalan waiter, klasifikasi rate limit, lifecycle SDK, sumber/periode, dan dua tes interaktif Streamlit.
SDK diuji dengan google-genai 2.26.0; provider Sectors/Gemini dimock. Tidak ada API live baru.
Kecepatan Gemini live di mesin pengguna belum diukur setelah update ini.

Untuk menjalankan seluruh suite:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Rujukan konfigurasi SDK (sumber resmi):
https://github.com/googleapis/python-genai
https://googleapis.github.io/python-genai/

Perubahan lokal belum dipush ke repository mana pun. Gunakan hasil gabungan ini sebagai versi bersama
setelah smoke test, lalu samakan repository/branch kerja tim agar versi engine tidak terpisah lagi.

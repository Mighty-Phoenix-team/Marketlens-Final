# MarketLens — evaluasi Explain Finding dengan Ragas

Paket tambahan untuk Team-2 Comparison + P1 yang terakhir dipakai. Satu file lama berubah: `marketlens/llm.py`, untuk merekam input/output setelah Gemini berhasil menghasilkan penjelasan. Prompt 1–21, model generation, parameter generation, engine, rumus Research Relevance, API, cache penjelasan, dan pemilihan Comparison dipertahankan.

## Cara cepat di Windows / PowerShell

1. Matikan API Team-2 (port 8001) dengan Ctrl+C. Team-1 dan Streamlit boleh tetap berjalan.
2. Backup `Team-2/marketlens/llm.py` lama.
3. Ekstrak ZIP. Salin **isi** folder `Team-2` dari ZIP ke dalam folder Team-2 project yang sekarang dipakai. Pilih Replace untuk `marketlens/llm.py`. Ini patch, bukan pengganti seluruh project; jangan menghapus folder lama. `.env`, `.venv`, database profil/watchlist, dan file Comparison tidak ada dalam ZIP.
4. Dari terminal folder Team-2, cek pemasangan tanpa API berbayar:

```powershell
.\.venv\Scripts\python.exe .\verify_ragas.py
```

5. Nyalakan kembali API Team-2 di terminal yang sama agar environment sebelumnya tetap berlaku:

```powershell
.\.venv\Scripts\python.exe -m uvicorn marketlens.api:app --host 127.0.0.1 --port 8001
```

Jika memakai terminal baru, set kembali `MARKETLENS_ASSET_API_BASE_URL` dan `MARKETLENS_DISCOVERY_UNIVERSE` seperti konfigurasi project sebelumnya. Tidak perlu mengganti daftar ticker untuk evaluasi.

6. Di dashboard, Back ke Discovery lalu buka finding dan klik **Explain Finding**. Pastikan label sumber **Gemini**. Mulai satu saham dahulu. Terminal API akan menampilkan `MarketLens evaluation sample saved`. Penjelasan yang sudah terbuka di Streamlit sebelum patch bukan sampel baru.
7. Buka terminal baru di folder Team-2 dan jalankan:

```powershell
.\.venv\Scripts\python.exe .\run_ragas.py --limit 1
```

Perintah ini membuat `.venv-ragas` khusus evaluasi dan memasang dependensi yang telah dipilih. Pemasangan pertama memerlukan internet dan dapat memakan waktu beberapa menit. Venv API/Streamlit tidak diubah. Sesudah setup, evaluator memakai key dari `.env` Team-2 tanpa perlu menyalinnya ke file lain.

8. Buka `index.html` pada lokasi laporan yang dicetak terminal. Laporan juga berisi `results.csv` dan `results.json`, berada di `evaluation_data/reports/<waktu-run>/`.

Sesudah satu sampel berjalan, evaluasi sampai lima sampel terbaru yang sudah tersimpan:

```powershell
.\.venv\Scripts\python.exe .\run_ragas.py --limit 5
```

Menjalankan `--limit 5` tidak mengumpulkan lima saham atau menghasilkan penjelasan baru secara otomatis. Ia hanya membaca sampel yang sudah direkam, paling banyak lima.

## Metrik dan interpretasi

| Metrik | Skala | Arti |
| --- | --- | --- |
| Faithfulness | 0–1 | Proporsi klaim dalam penjelasan yang dinilai didukung konteks aktual. |
| Limitation retention (Aspect Critic) | 0/1 | Kelulusan terhadap kriteria pelestarian batasan data, termasuk dua ketidakpastian TTM ketika berlaku. |
| Profile alignment (Aspect Critic) | 0/1 | Kesesuaian alasan relevansi dengan profil dan matched groups, serta penggunaan skor Research Relevance secara benar. |

Ketiganya memakai **kelas metrik Ragas asli**, dengan Gemini sebagai LLM evaluator. Dua kriteria Aspect Critic didefinisikan di `evaluation/criteria.py`; bukan metrik bawaan dengan nama tersebut. `strictness=1` dipilih untuk membatasi biaya. Tidak diperlukan reference answer, embedding, atau OpenAI API key.

Faithfulness di laporan adalah konsistensi terhadap evidence yang dikirim, bukan verifikasi kebenaran data Sectors di dunia nyata. Nilai tinggi tidak membuktikan semua informasi penting sudah dibahas, kesimpulan investasi benar, atau data penyedia akurat. Ringkasan laporan menampilkan rata-rata Faithfulness dan proporsi lolos untuk setiap Aspect Critic secara terpisah. Tidak ada skor gabungan atau batas kelulusan universal yang dikarang.

Laporan menyediakan hasil per sampel dan keluaran judge untuk pemeriksaan manual. Periksa juga angka, satuan `%`/`pp`/`×`, periode, dan beberapa keputusan judge. Generator dan evaluator dapat menggunakan model yang sama; hasil ini bukan validasi manusia independen. Sampel kecil adalah pilot untuk contoh kasus tersebut, bukan validasi seluruh pasar.

## Pencatatan dan biaya

- Snapshot diambil dari **request aktual Gemini**, termasuk konteks compact dan pemetaan sumber S1/S2/S3. Tidak mengambil konteks lewat endpoint terpisah setelah jawaban selesai.
- Tugas evaluasi berasal dari instruksi aplikasi, ticker, dan profil sebelum jawaban dibuat, walaupun pengguna tidak mengetik prompt.
- Hanya penjelasan Gemini yang berhasil di-parse yang direkam. Deterministic fallback tidak dimasukkan ke evaluasi Gemini. Kegagalan menyimpan sampel dicatat di log tanpa mengubah penjelasan menjadi fallback.
- Cache hit tidak menjalankan generation lagi, sehingga tidak merekam sampel baru. Fingerprint input/output juga menghindari duplikasi pasangan yang benar-benar identik. Penjelasan yang berbeda dari input sama masih merupakan sampel berbeda dan bukan kasus independen untuk klaim statistik.
- Recorder hanya menulis file lokal, tanpa memanggil evaluator. Evaluasi dilakukan melalui perintah terpisah, bukan setiap klik Explain Finding.
- Runner tidak memanggil Sectors atau backend aset; data berasal dari file tersimpan. **Pembuatan penjelasan saat mengumpulkan sampel** tetap mengikuti biaya/caching aplikasi biasa.
- Evaluasi menggunakan kuota Gemini. Umumnya dua panggilan untuk Faithfulness, satu untuk tiap Aspect Critic: sekitar empat panggilan evaluator per sampel, tidak termasuk upaya koreksi output yang tidak valid. Tidak menjanjikan satu sampel = satu kredit atau biaya tertentu.
- Default batas keras 30 panggilan SDK per run; maksimal empat panggilan per metrik untuk membatasi upaya perbaikan output. Request dijalankan berurutan. Timeout per metrik default 120 detik. Timeout lokal tidak menjamin layanan penyedia membatalkan pemrosesan/billing yang sudah dimulai.
- Hasil evaluasi disimpan per sampel/model/versi implementasi/kriteria. Pengulangan yang identik memakai hasil tersimpan. Perubahan alias model di sisi penyedia tidak otomatis terdeteksi saat cache dipakai; gunakan model dengan versi tetap untuk eksperimen yang perlu dapat direproduksi, atau refresh secara eksplisit.
- Error, timeout, rate limit, dan jawaban tanpa klaim ditandai error/unscored, **tidak diubah menjadi 0 atau 1**. Rata-rata hanya memakai skor valid dan mencantumkan jumlah yang belum dinilai. Jika run berhenti, laporan parsial tetap tersedia.
- Key, `.env`, objek client, dan ID profil pengguna tidak direkam dalam snapshot. Snapshot tetap berisi evidence riset dan jawaban; folder `evaluation_data` diabaikan oleh Git melalui `.gitignore` di dalamnya.

## Perintah tambahan

Cek snapshot tanpa memasang/memanggil Ragas:

```powershell
.\.venv\Scripts\python.exe .\run_ragas.py --check
```

Hanya dua pemeriksaan inti (Faithfulness dan batasan data), dengan batas panggilan lebih kecil:

```powershell
.\.venv\Scripts\python.exe .\run_ragas.py --limit 1 --core-only --max-calls 6
```

Ulangi metrik yang sebelumnya gagal setelah masalah kuota/koneksi diperbaiki; hasil sukses tetap memakai cache:

```powershell
.\.venv\Scripts\python.exe .\run_ragas.py --limit 1 --retry-errors
```

`--refresh` memaksa evaluasi ulang termasuk hasil sukses, sehingga memakai kuota lagi. Gunakan hanya ketika memang ingin menilai ulang. `--model NAMA_MODEL` mengganti model evaluator untuk run itu.

Environment opsional di `.env`:

| Nama | Perilaku |
| --- | --- |
| `MARKETLENS_EVAL_CAPTURE=0` | Matikan recorder; perlu restart API. Default recorder aktif. |
| `MARKETLENS_EVAL_SAMPLES_DIR` | Direktori snapshot; path relatif dihitung dari Team-2. |
| `MARKETLENS_EVAL_MODEL` | Model evaluator; default memakai `GEMINI_MODEL`, lalu `gemini-flash-latest`. |
| `MARKETLENS_EVAL_API_KEY` | Key khusus evaluator jika diinginkan; default memakai `GEMINI_API_KEY`, lalu `GOOGLE_API_KEY`. |

## Struktur perubahan untuk tim web

`marketlens/llm.py` memanggil recorder untuk jalur sync dan async. `marketlens/evaluation_capture.py` memakai standard library, sehingga backend tidak memerlukan Ragas untuk berjalan. `evaluation/` berisi dataset validation, adapter Gemini, tiga metrik, runner, serta pembuat laporan. `run_ragas.py` menyiapkan lingkungan evaluator terpisah. Tidak ada kontrak endpoint web yang diubah; skor evaluasi tidak mengganti Research Relevance.

Dependensi utama dipin di `requirements-eval.txt`, termasuk Ragas 0.4.3 dan keluarga LangChain 0.3 yang masih memuat modul yang dipakai Ragas tersebut. Adapter mengimplementasikan `BaseRagasLLM` dengan Google GenAI SDK langsung, menghindari ketergantungan pada adapter otomatis Instructor untuk request Gemini. Paket `openai` adalah dependensi transitif Ragas; evaluator ini tidak membuat client atau panggilan OpenAI.

Versi ini memakai API metrik `SingleTurnSample` yang masih tersedia pada Ragas 0.4.3. Jangan mencampurkan contoh `collections` dari dokumentasi terbaru tanpa migrasi dan pengujian. Telemetry opsional Ragas/LangSmith dinonaktifkan oleh runner. Keluaran Gemini yang dibatasi karena safety atau panjang respons dianggap error, bukan dipaksa menjadi skor.

## Verifikasi pengembangan

`verify_ragas.py` menguji capture + cache dengan SDK mock, tidak menghasilkan skor kualitas. Tes tambahan ada di `tests/test_evaluation_capture.py` dan `tests/test_ragas_runner.py`; tes Ragas memakai kelas metrik sesungguhnya dengan balasan model yang dikontrol. Skor simulasi tes bukan hasil evaluasi Gemini live. Jalankan tes Ragas pada lingkungan evaluator yang telah memasang pytest jika mengembangkan lebih lanjut.

Referensi resmi:
- https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/faithfulness/
- https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/general_purpose/
- https://docs.ragas.io/en/latest/howtos/integrations/gemini/

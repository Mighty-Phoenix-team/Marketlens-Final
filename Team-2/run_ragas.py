"""One command: create an isolated evaluator environment, then run evaluation."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    # Existing Team-2 dependencies suffice for this non-billable check.
    if "--check" in sys.argv[1:] or "--help" in sys.argv[1:]:
        from evaluation.run import main as check_main
        return check_main(sys.argv[1:])
    from dotenv import load_dotenv
    from evaluation.dataset import load_samples, sample_directory
    load_dotenv(ROOT / ".env", encoding="utf-8-sig", override=False)
    args = sys.argv[1:]
    # Early check avoids installing hundreds of MB before any sample exists.
    directory = sample_directory()
    if "--samples" in args and args.index("--samples") + 1 < len(args):
        directory = Path(args[args.index("--samples") + 1])
    if not load_samples(directory, 1)[0]:
        print("Belum ada sampel Gemini yang valid. Restart API setelah patch, lalu Explain Finding satu saham dulu.")
        return 2
    env_dir = ROOT / ".venv-ragas"
    python = env_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    requirements = ROOT / "requirements-eval.txt"
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    stamp = env_dir / "marketlens-requirements.sha256"
    try:
        if not python.exists():
            print("Menyiapkan .venv-ragas terpisah. Venv API tetap dipakai seperti biasa.", flush=True)
            subprocess.run([sys.executable, "-m", "venv", str(env_dir)], check=True, cwd=ROOT)
        (env_dir / ".gitignore").write_text("*\n", encoding="utf-8")
        if not stamp.exists() or stamp.read_text().strip() != fingerprint:
            print("Memasang dependensi evaluasi (pertama kali perlu waktu dan internet).", flush=True)
            subprocess.run([str(python), "-m", "pip", "install", "-r", str(requirements)], check=True, cwd=ROOT)
            stamp.write_text(fingerprint, encoding="utf-8")
        return subprocess.run([str(python), "-m", "evaluation.run", *args], cwd=ROOT).returncode
    except subprocess.CalledProcessError:
        print("Pemasangan evaluator belum selesai. Periksa pesan pip di atas; jalankan ulang setelah masalah diperbaiki.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

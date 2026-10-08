"use client";

// components/layout/ThemeToggle.tsx
//
// Kontrol dark/light toggle. Sinkron dengan themeInitScript di
// app/layout.tsx — keduanya pakai key localStorage yang sama
// ("marketlens.theme") dan atribut yang sama (data-theme di <html>).
// Kalau salah satu diubah, yang lain WAJIB ikut diubah supaya tidak
// desync (efeknya: flash tema salah saat reload).

import { useEffect, useState } from "react";

type Theme = "light" | "dark";
const STORAGE_KEY = "marketlens.theme";

export function ThemeToggle() {
  const [theme, setThemeState] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const current = document.documentElement.getAttribute("data-theme");
    setThemeState(current === "dark" ? "dark" : "light");
    setMounted(true);
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setThemeState(next);
    document.documentElement.setAttribute("data-theme", next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }

  // Hindari mismatch hydration: sebelum mounted, tampilkan placeholder
  // netral (bukan icon final) karena server tidak tahu preferensi tema
  // client sampai script init jalan.
  if (!mounted) {
    return <div className="h-10 w-10" aria-hidden="true" />;
  }

  return (
    <button
      onClick={toggle}
      aria-label={
        theme === "dark" ? "Ganti ke mode terang" : "Ganti ke mode gelap"
      }
      className="flex h-10 w-10 items-center justify-center rounded-sm border border-border text-text-muted transition hover:border-accent hover:text-accent"
    >
      {theme === "dark" ? (
        <svg
          aria-hidden="true"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
        >
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </svg>
      ) : (
        <svg
          aria-hidden="true"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
        >
          <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5Z" />
        </svg>
      )}
    </button>
  );
}

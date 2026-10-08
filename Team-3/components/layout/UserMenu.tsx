"use client";

// components/layout/UserMenu.tsx
//
// Ikon akun user di top bar. Dropdown berisi tombol Logout — SENGAJA
// belum berfungsi (cuma UI) karena project ini belum punya sistem
// akun/autentikasi sama sekali. Begitu ada, ganti handleLogout
// dengan logic sesungguhnya (clear session, redirect, dst).

import { useEffect, useRef, useState } from "react";

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleLogout() {
    // TODO: belum ada sistem akun — ganti begitu autentikasi tersedia.
    setOpen(false);
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Menu akun"
        aria-expanded={open}
        className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-text-muted transition hover:border-accent hover:text-accent"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c0-4.4 3.6-7 8-7s8 2.6 8 7" />
        </svg>
      </button>

      {open && (
        <div className="absolute left-0 top-10 z-20 w-40 rounded-sm border border-border bg-surface py-1 shadow-sm">
          <button
            onClick={handleLogout}
            className="block w-full px-3 py-2 text-left text-sm text-text-muted hover:bg-bg-subtle hover:text-text"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  );
}

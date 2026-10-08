"use client";

// components/layout/SearchBar.tsx
//
// UI SEARCH BAR SAJA — belum ada logic pencarian sungguhan.
// Belum jelas dari PRD: search ini untuk cari finding/ticker
// (di dalam Discovery/My Assets), atau cari sesuatu yang lain.
// TODO: konfirmasi target pencarian sebelum menyambungkan ke data.

import { useState } from "react";

export function SearchBar() {
  const [value, setValue] = useState("");

  return (
    <div className="mx-auto w-full max-w-md">
      <div className="flex items-center gap-2 rounded-sm border border-border bg-bg-subtle px-3 py-1.5">
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="shrink-0 text-text-faint"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Cari ticker atau finding..."
          className="w-full bg-transparent text-sm text-text placeholder:text-text-faint focus:outline-none"
        />
      </div>
    </div>
  );
}

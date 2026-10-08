"use client";

// components/layout/NavBar.tsx
//
// Navigasi utama antar 3 halaman. Sengaja pakai usePathname untuk
// highlight active state — tanpa ini, user tidak punya cara tahu
// sedang di halaman mana selain judul halaman itu sendiri.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./ThemeToggle";

const NAV_ITEMS = [
  { href: "/discovery", label: "Discovery" },
  { href: "/my-assets", label: "My Assets" },
  { href: "/profile", label: "Profile" },
] as const;

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex max-w-2xl items-center justify-between px-6 py-4">
        <span className="font-serif text-lg font-semibold tracking-tight text-text">
          MarketLens
        </span>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={
                  active
                    ? "rounded-md bg-accent-subtle px-3 py-1.5 text-sm font-medium text-accent"
                    : "rounded-md px-3 py-1.5 text-sm text-text-muted transition hover:text-text"
                }
              >
                {item.label}
              </Link>
            );
          })}
          <div className="ml-2 border-l border-border pl-3">
            <ThemeToggle />
          </div>
        </nav>
      </div>
    </header>
  );
}

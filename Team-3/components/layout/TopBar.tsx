"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./ThemeToggle";
export function TopBar() {
  const pathname = usePathname();
  const section = pathname.startsWith("/finding/")
    ? "Finding detail"
    : ({
        "/discovery": "Discovery",
        "/my-assets": "My Assets",
        "/comparison": "Comparison",
        "/profile": "Research profile",
        "/settings": "Settings",
      }[pathname] ?? "Workspace");
  return (
    <header className="topbar">
      <div className="topbar-context">
        <span>
          Research workspace{" "}
          <span className="topbar-divider" aria-hidden="true">
            /
          </span>{" "}
          <strong>{section}</strong>
        </span>
        <small>IDX · End-of-day data</small>
      </div>
      <div className="flex items-center gap-3">
        <ThemeToggle />
        <Link
          className="profile-avatar"
          href="/profile"
          aria-label="Buka research profile"
        >
          R
        </Link>
      </div>
    </header>
  );
}

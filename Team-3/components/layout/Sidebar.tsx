"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AppIcon, type AppIconName } from "@/components/ui/AppIcon";
const items = [
  { href: "/discovery", label: "Discovery", icon: "search-plus" },
  { href: "/my-assets", label: "My Assets", icon: "briefcase" },
  { href: "/comparison", label: "Comparison", icon: "compare" },
] satisfies { href: string; label: string; icon: AppIconName }[];
export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sidebar">
      <Link href="/discovery" className="brand" aria-label="MarketLens">
        <span className="brand-wordmark" aria-hidden="true">
          <span>Market</span>
          <strong>Lens</strong>
        </span>
      </Link>
      <Link
        href="/profile"
        aria-current={pathname === "/profile" ? "page" : undefined}
        className={
          "nav-link sidebar-profile " +
          (pathname === "/profile" ? "active" : "")
        }
      >
        <AppIcon name="user" />
        Profile
      </Link>
      <p className="nav-caption">WORKSPACE</p>
      <nav aria-label="Navigasi utama">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            aria-current={
              pathname === item.href ||
              (item.href === "/discovery" && pathname.startsWith("/finding/"))
                ? "page"
                : undefined
            }
            className={
              "nav-link " +
              (pathname === item.href ||
              (item.href === "/discovery" && pathname.startsWith("/finding/"))
                ? "active"
                : "")
            }
          >
            <AppIcon name={item.icon} />
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="sidebar-note">
        <span className="market-label">IDX / EQUITIES</span>
        <p>Indonesian equities</p>
        <p>Evidence, sources &amp; research context</p>
      </div>
    </aside>
  );
}

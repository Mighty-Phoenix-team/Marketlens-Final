import type { SVGProps } from "react";

export type AppIconName =
  | "activity"
  | "arrow-left"
  | "arrow-right"
  | "arrow-up-right"
  | "briefcase"
  | "chart"
  | "compare"
  | "flow"
  | "list"
  | "refresh"
  | "research"
  | "search-plus"
  | "user";

export function AppIcon({
  name,
  className,
  ...props
}: { name: AppIconName } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {name === "search-plus" && (
        <>
          <circle cx="11" cy="11" r="7" />
          <path d="m16 16 5 5M11 8v6M8 11h6" />
        </>
      )}
      {name === "briefcase" && (
        <>
          <rect x="3" y="5" width="18" height="16" rx="3" />
          <path d="M8 5V3h8v2M3 11h18M10 11v3h4v-3" />
        </>
      )}
      {name === "compare" && (
        <path d="M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4" />
      )}
      {name === "user" && (
        <>
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21v-2a8 8 0 0 1 16 0v2" />
        </>
      )}
      {name === "research" && (
        <>
          <path d="M4 19V8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v11" />
          <path d="M8 4h8M8 11h8M8 15h5M2 19h20" />
        </>
      )}
      {name === "chart" && <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />}
      {name === "activity" && <path d="M3 12h4l2.5-6 5 12 2.5-6h4" />}
      {name === "flow" && (
        <>
          <path d="M5 7h11m-3-3 3 3-3 3M19 17H8m3-3-3 3 3 3" />
          <circle cx="4" cy="17" r="1" />
          <circle cx="20" cy="7" r="1" />
        </>
      )}
      {name === "refresh" && (
        <>
          <path d="M20 11a8 8 0 1 0-2.3 5.7" />
          <path d="M20 4v7h-7" />
        </>
      )}
      {name === "arrow-up-right" && <path d="M7 17 17 7M8 7h9v9" />}
      {name === "arrow-right" && <path d="M5 12h14m-5-5 5 5-5 5" />}
      {name === "arrow-left" && <path d="M19 12H5m5-5-5 5 5 5" />}
      {name === "list" && (
        <>
          <path d="M9 6h11M9 12h11M9 18h11" />
          <path d="M4 6h.01M4 12h.01M4 18h.01" />
        </>
      )}
    </svg>
  );
}

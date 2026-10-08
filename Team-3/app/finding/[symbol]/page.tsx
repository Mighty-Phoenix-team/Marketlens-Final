"use client";

// app/finding/[symbol]/page.tsx
//
// Halaman detail 1 finding, diakses dari klik FindingCard di Discovery
// atau My Assets. Route pakai [symbol] (bukan [id]) karena API asli
// memakai path /assets/{symbol}/finding -- symbol dan id kebetulan
// sama nilainya di skema saat ini, tapi symbol lebih eksplisit untuk
// dipakai sebagai path parameter.

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { FindingDetail } from "@/components/finding/FindingDetail";
import { LoadingState } from "@/components/states/LoadingState";
import { ErrorState } from "@/components/states/ErrorState";
import { getFindingDetail, ApiError } from "@/lib/api";
import { getActiveProfileId } from "@/lib/session";
import type { Finding } from "@/lib/types";

export default function FindingDetailPage() {
  const params = useParams<{ symbol: string }>();
  const router = useRouter();
  const [finding, setFinding] = useState<Finding | null>(null);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [status, setStatus] = useState<"loading" | "error" | "ready">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadFinding() {
    const activeProfileId = getActiveProfileId();
    if (!activeProfileId) {
      // Belum ada profile aktif -- tidak mungkin fetch Finding tanpa
      // profile_id, jadi arahkan balik ke halaman profile.
      router.push("/profile");
      return;
    }
    setProfileId(activeProfileId);
    setStatus("loading");
    try {
      const result = await getFindingDetail(activeProfileId, params.symbol);
      setFinding(result);
      setStatus("ready");
    } catch (err) {
      setErrorMessage(
        err instanceof ApiError && err.status === 0
          ? "Tidak bisa terhubung ke server. Pastikan backend Team 2 berjalan di port 8001."
          : "Gagal memuat detail finding."
      );
      setStatus("error");
    }
  }

  useEffect(() => {
    loadFinding();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.symbol]);

  if (status === "loading") {
    return <LoadingState label="Memuat finding..." />;
  }

  if (status === "error" || !finding || !profileId) {
    return (
      <div className="p-6">
        <ErrorState
          title="Gagal memuat finding"
          description={errorMessage ?? undefined}
          onRetry={loadFinding}
        />
      </div>
    );
  }

  return <FindingDetail finding={finding} profileId={profileId} />;
}

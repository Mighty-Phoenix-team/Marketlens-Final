"use client";
import { useCallback, useEffect, useState } from "react";
import { ProfileForm } from "@/components/profile/ProfileForm";
import { LoadingState } from "@/components/states/LoadingState";
import { getProfile, ApiError } from "@/lib/api";
import { getActiveProfileId } from "@/lib/session";
import type { Profile } from "@/lib/types";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>();
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoaded(false);
    setError("");
    const id = getActiveProfileId();
    try {
      if (id) setProfile(await getProfile(id));
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setProfile(undefined);
      else
        setError(
          "Profil belum dapat dimuat. Coba hubungkan kembali untuk mengedit pilihan yang tersimpan.",
        );
    } finally {
      setLoaded(true);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  return (
    <div className="page-wrap profile-page">
      <div className="profile-intro" id="research-profile">
        <p className="eyebrow">Workspace / Profile</p>
        <h1>Research profile</h1>
        <p>
          Tentukan sektor, fokus, dan periode data untuk menyesuaikan temuan di
          Discovery.
        </p>
      </div>
      {!loaded ? (
        <LoadingState label="Memuat profil…" />
      ) : error ? (
        <div className="empty-panel">
          <h2>Hubungkan kembali profilmu</h2>
          <p role="alert">{error}</p>
          <button className="button button-primary" onClick={() => void load()}>
            Coba lagi
          </button>
        </div>
      ) : (
        <ProfileForm initialProfile={profile} />
      )}
    </div>
  );
}

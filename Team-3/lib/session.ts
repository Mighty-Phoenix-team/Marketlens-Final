// lib/session.ts
//
// Backend Team 2 tidak (belum) punya konsep "current user"/auth --
// profile diakses lewat profile_id di URL path. Supaya frontend tidak
// perlu user paste profile_id manual tiap buka halaman, ID-nya
// disimpan di localStorage begitu Profile dibuat.
//
// BEDA dari pola lama: sebelumnya SELURUH data Profile disimpan di
// localStorage (karena belum ada backend). Sekarang localStorage CUMA
// menyimpan ID -- semua data Profile yang sesungguhnya datang dari API
// (lib/api.ts) tiap kali dibutuhkan.

const STORAGE_KEY = "marketlens.activeProfileId";

export function getActiveProfileId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

export function setActiveProfileId(profileId: string) {
  window.localStorage.setItem(STORAGE_KEY, profileId);
}

export function clearActiveProfileId() {
  window.localStorage.removeItem(STORAGE_KEY);
}

// lib/api.ts
//
// Client untuk backend Team 2 (Intelligence Engine), port 8001.
// Endpoint di sini SEMUA sudah diverifikasi lewat Swagger
// (http://127.0.0.1:8001/docs) dengan "Try it out" -- bukan tebakan.
//
// PENTING: frontend HANYA bicara ke Team 2 API. Team 1 (port 8000)
// dipanggil Team 2 secara internal, frontend tidak pernah manggil
// Team 1 langsung (dikonfirmasi di README Team 1: "Team 3 sebaiknya
// mengambil Finding dari API Team 2, bukan membuat Finding dari raw
// Team 1 asset response").
//
// NEXT_PUBLIC_API_BASE_URL sets the Team 2 origin for this frontend build.
// The localhost default is intended for local development.

import { cachedRequest, invalidateRequests } from "./request-cache";

import type {
  ComparisonResponse,
  Profile,
  Finding,
  DiscoveryResponse,
  MyAssetsResponse,
  ExplainAssetResponse,
} from "./types";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8001"
).replace(/\/$/, "");

/**
 * Error kustom supaya pemanggil (page/component) bisa membedakan
 * error dari backend (ada status code) vs error jaringan (fetch gagal
 * total, mis. server belum jalan).
 *
 * CATATAN: format response error asli dari backend BELUM diverifikasi
 * (belum ada contoh actual response 400/404/422/500/503 dari Team 1
 * atau Team 2 -- ini masih pertanyaan terbuka). Untuk sementara, class
 * ini cuma simpan status + raw body apa adanya, TIDAK mengasumsikan
 * ada field "message" atau "detail" tertentu. Sesuaikan begitu format
 * error asli dikonfirmasi.
 */
export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(`API error ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function apiFetch<T>(
  path: string,
  options?: RequestInit,
  refresh = false,
): Promise<T> {
  if (!options?.method || options.method === "GET") {
    return cachedRequest(path, () => request<T>(path, options), refresh);
  }
  return request<T>(path, options).then((value) => {
    const profilePath = path.match(/^\/api\/profiles\/[^/]+/)?.[0];
    if (profilePath) invalidateRequests(profilePath);
    return value;
  });
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      cache: "no-store",
      headers: {
        ...(options?.body ? { "Content-Type": "application/json" } : {}),
        ...options?.headers,
      },
    });
  } catch {
    // fetch() melempar TypeError kalau server tidak bisa dihubungi sama
    // sekali (mis. backend belum dijalankan) -- ini beda dari response
    // error HTTP biasa (400/500/dst), jadi dibedakan statusnya sebagai 0.
    throw new ApiError(0, {
      message:
        "Tidak bisa terhubung ke server. Periksa koneksi dan alamat API yang dikonfigurasi.",
    });
  }

  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = null;
    }
    throw new ApiError(response.status, body);
  }

  return response.json() as Promise<T>;
}

// --- Profile -----------------------------------------------------------

export interface CreateProfileInput {
  sectors: string[];
  research_focus: string[];
  horizon_days: number;
}

export function createProfile(input: CreateProfileInput): Promise<Profile> {
  return apiFetch<Profile>("/api/profiles", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getProfile(profileId: string): Promise<Profile> {
  return apiFetch<Profile>(`/api/profiles/${profileId}`);
}

export function updateProfile(
  profileId: string,
  input: CreateProfileInput,
): Promise<Profile> {
  return apiFetch<Profile>(`/api/profiles/${profileId}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

// --- Discovery & My Assets ------------------------------------------------

export function getDiscovery(
  profileId: string,
  refresh = false,
): Promise<DiscoveryResponse> {
  return apiFetch<DiscoveryResponse>(
    `/api/profiles/${profileId}/discovery`,
    undefined,
    refresh,
  );
}

export function getMyAssets(
  profileId: string,
  refresh = false,
): Promise<MyAssetsResponse> {
  return apiFetch<MyAssetsResponse>(
    `/api/profiles/${profileId}/assets`,
    undefined,
    refresh,
  );
}

export function saveAsset(profileId: string, symbol: string): Promise<Profile> {
  return apiFetch<Profile>(`/api/profiles/${profileId}/assets/${symbol}`, {
    method: "PUT",
  });
}

export function removeAsset(
  profileId: string,
  symbol: string,
): Promise<Profile> {
  return apiFetch<Profile>(`/api/profiles/${profileId}/assets/${symbol}`, {
    method: "DELETE",
  });
}

// --- Finding Detail & Explain --------------------------------------------

export function getFindingDetail(
  profileId: string,
  symbol: string,
): Promise<Finding> {
  return apiFetch<Finding>(
    `/api/profiles/${profileId}/assets/${symbol}/finding`,
  );
}

export function explainAsset(
  profileId: string,
  symbol: string,
): Promise<ExplainAssetResponse> {
  return apiFetch<ExplainAssetResponse>(
    `/api/profiles/${profileId}/assets/${symbol}/explanation`,
    { method: "POST" },
  );
}

// Catatan: GET .../explanation-context SENGAJA tidak dibuatkan client
// function di sini. Berdasarkan isi response-nya (lihat
// ExplanationContextResponse di lib/types.ts), endpoint ini adalah
// payload internal untuk prompt AI, bukan untuk ditampilkan ke user --
// frontend kemungkinan besar tidak pernah perlu memanggilnya langsung.

// Read-only POST: keyed by profile and the exact ordered selection.
export function compareAssets(
  profileId: string,
  symbols: string[],
  refresh = false,
): Promise<ComparisonResponse> {
  const path = `/api/profiles/${profileId}/comparison`;
  return cachedRequest(
    `${path}:${JSON.stringify(symbols)}`,
    () =>
      request<ComparisonResponse>(path, {
        method: "POST",
        body: JSON.stringify({ symbols }),
      }),
    refresh,
  );
}

"use client";
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { usePathname } from "next/navigation";
import { getProfile, saveAsset, removeAsset } from "@/lib/api";
import { getActiveProfileId } from "@/lib/session";
import type { Profile } from "@/lib/types";

type AssetState = {
  profile: Profile | null;
  loading: boolean;
  error: string;
  change: (symbol: string, saved: boolean) => Promise<void>;
  pending: string[];
};
const Context = createContext<AssetState | null>(null);
export function AssetsProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<string[]>([]);
  const busy = useRef(new Set<string>());
  useEffect(() => {
    let active = true;
    const id = getActiveProfileId();
    setLoading(true);
    setError("");
    if (!id) {
      setProfile(null);
      setLoading(false);
      return;
    }
    getProfile(id)
      .then((value) => {
        if (active) setProfile(value);
      })
      .catch(() => {
        if (active) {
          setProfile(null);
          setError("Profil belum dapat dimuat. Coba muat ulang halaman.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [pathname]);
  async function change(symbol: string, saved: boolean) {
    if (!profile)
      throw new Error("Buat atau muat research profile terlebih dahulu.");
    if (busy.current.has(symbol)) return;
    busy.current.add(symbol);
    setPending([...busy.current]);
    try {
      await (saved
        ? saveAsset(profile.id, symbol)
        : removeAsset(profile.id, symbol));
      // Merge only the confirmed symbol: parallel saves cannot overwrite each other.
      setProfile(
        (current) =>
          current && {
            ...current,
            saved_assets: saved
              ? [...new Set([...current.saved_assets, symbol])]
              : current.saved_assets.filter((item) => item !== symbol),
          },
      );
    } finally {
      busy.current.delete(symbol);
      setPending([...busy.current]);
    }
  }
  return (
    <Context.Provider value={{ profile, loading, error, change, pending }}>
      {children}
    </Context.Provider>
  );
}
export function useAssets() {
  const context = useContext(Context);
  if (!context) throw new Error("AssetsProvider is required");
  return context;
}

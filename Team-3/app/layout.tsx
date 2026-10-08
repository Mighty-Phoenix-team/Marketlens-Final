import { Archivo, Inter, Playfair_Display } from "next/font/google";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { AssetsProvider } from "@/components/assets/AssetsProvider";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});
const display = Archivo({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-archivo",
});
const editorial = Playfair_Display({
  subsets: ["latin"],
  display: "swap",
  style: ["normal", "italic"],
  variable: "--font-editorial",
});

export const metadata = {
  title: "MarketLens",
  description: "Research radar untuk konteks pasar yang relevan.",
};

// Script ini SENGAJA inline & synchronous (bukan di useEffect) supaya
// jalan SEBELUM React hydrate — mencegah "flash" tema salah sesaat
// (mis. render dark dulu baru snap ke light) saat halaman pertama
// dimuat. Baca preferensi tersimpan dari localStorage; kalau belum
// ada, ikuti preferensi sistem OS pengguna.
const themeInitScript = `
  (function () {
    try {
      var stored = window.localStorage.getItem("marketlens.theme");
      var theme = stored || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      document.documentElement.setAttribute("data-theme", theme);
    } catch (e) {}
  })();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="id"
      suppressHydrationWarning
      className={`${inter.variable} ${display.variable} ${editorial.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="bg-bg font-sans text-text">
        <a href="#main-content" className="skip-link">
          Lewati ke konten utama
        </a>
        <AssetsProvider>
          {/*
          Layout 2 kolom: Sidebar (fixed width, full height) di kiri,
          kolom kanan berisi TopBar + konten halaman yang scroll
          sendiri. Sidebar & TopBar ditaruh di root layout supaya
          konsisten di semua halaman tanpa diulang. Root "/" tidak
          masalah ikut wrapping ini karena dia cuma redirect() sekilas
          (lihat app/page.tsx).
        */}
          <div className="app-shell">
            <Sidebar />
            <div className="workspace">
              <TopBar />
              <main id="main-content" className="min-w-0 flex-1">
                {children}
              </main>
            </div>
          </div>
        </AssetsProvider>
      </body>
    </html>
  );
}

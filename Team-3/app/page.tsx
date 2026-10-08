import { redirect } from "next/navigation";

// Root route tidak render UI apapun — sesuai user flow PRD section 4,
// entry point aplikasi selalu diarahkan ke /profile.
//
// Catatan: file ini sempat ketimpa jadi test page manual untuk uji
// FindingCard (lihat PROGRESS.md). Versi test itu SUDAH DIPINDAHKAN,
// bukan dihapus — kalau perlu uji komponen secara terisolasi lagi,
// jangan pakai app/page.tsx, buat route terpisah misalnya
// app/_dev/test-finding-card/page.tsx supaya tidak ketiban lagi.
export default function RootPage() {
  redirect("/profile");
}

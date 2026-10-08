import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("marketlens.theme", "light"),
  );
});

test("profile choices update summary and preserve selections after failed save", async ({
  page,
}) => {
  await page.goto("/profile");
  await page.getByRole("button", { name: "Simpan & buka Discovery" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Pilih minimal 1 sektor",
  );
  await page.getByRole("searchbox", { name: "Cari sektor" }).fill("financial");
  await page.getByRole("button", { name: "Financials", exact: true }).click();
  await page.getByRole("searchbox", { name: "Cari sektor" }).fill("");
  await page.getByRole("button", { name: /Fundamental/ }).click();
  await page.getByRole("button", { name: "60 hari", exact: true }).click();
  await expect(page.getByLabel("Ringkasan profil")).toContainText("Financials");
  await expect(page.getByLabel("Ringkasan profil")).toContainText("60 hari");
  await expect(page.getByRole("slider")).toHaveValue("60");
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "test-results/profile-desktop.png",
    fullPage: true,
  });
  await page.route("http://127.0.0.1:8001/**", (route) => route.abort());
  await page.getByRole("button", { name: "Simpan & buka Discovery" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Pilihanmu tetap ada",
  );
  await expect(
    page.getByRole("button", { name: "Financials", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
});

test("mobile profile supports keyboard selection and dark mode without overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/profile");
  const sector = page.getByRole("button", { name: "Technology", exact: true });
  await sector.focus();
  await page.keyboard.press("Space");
  await expect(sector).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: /Investor Flow/ }).click();
  await expect(page.getByLabel("Ringkasan profil")).toContainText("Technology");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/profile-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Ganti ke mode gelap" }).click();
  await page.screenshot({
    path: "test-results/profile-dark-mobile.png",
    animations: "disabled",
    fullPage: true,
  });
});

test("existing profile network failure offers retry instead of an empty creation form", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("marketlens.activeProfileId", "existing"),
  );
  await page.route("http://127.0.0.1:8001/**", (route) => route.abort());
  await page.goto("/profile");
  await expect(page.getByRole("button", { name: "Coba lagi" })).toBeVisible();
  await expect(page.getByRole("searchbox")).toHaveCount(0);
});

test("profile quick navigation, summary edits and reset stay in sync", async ({
  page,
}) => {
  await page.goto("/profile");
  await page.getByRole("button", { name: "Financials", exact: true }).click();
  await page.getByRole("button", { name: /Fundamental/ }).click();
  await expect(
    page.getByRole("status", { name: "Status penyimpanan profil" }),
  ).toContainText("Perubahan belum disimpan");
  await page.getByRole("button", { name: "Ubah waktu", exact: true }).click();
  await expect(page.locator("#profile-horizon")).toBeFocused();
  await page.getByRole("button", { name: "60 hari", exact: true }).click();
  await expect(page.getByLabel("Ringkasan profil")).toContainText("60 hari");
  await page.getByRole("button", { name: "Hapus sektor Financials" }).click();
  await expect(
    page.getByRole("button", { name: "Financials", exact: true }),
  ).toHaveAttribute("aria-pressed", "false");
  await page.getByRole("button", { name: "Mulai ulang pilihan" }).click();
  await expect(page.getByRole("slider")).toHaveValue("30");
  await expect(
    page.getByRole("button", { name: /Fundamental/ }),
  ).toHaveAttribute("aria-pressed", "false");
  await expect(
    page.getByRole("status", { name: "Status penyimpanan profil" }),
  ).toContainText("Profil belum disimpan");
});

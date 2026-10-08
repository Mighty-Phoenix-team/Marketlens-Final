import { test, expect, type Page } from "@playwright/test";
import type { Finding, Profile } from "../lib/types";

test("research workspace stays readable across desktop, tablet and mobile in both themes", async ({
  page,
}) => {
  test.setTimeout(90000);
  await mockApi(page, ["BBCA", "BBRI"]);
  for (const width of [1440, 1024, 768, 375]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const route of [
      "/discovery",
      "/my-assets",
      "/finding/BBCA",
      "/comparison",
      "/profile",
      "/settings",
    ]) {
      await page.goto(route);
      if (route === "/profile")
        await expect(page.getByRole("slider")).toBeVisible();
      else if (route === "/discovery" || route === "/my-assets")
        await expect(page.getByRole("article").first()).toBeVisible();
      else
        await expect(
          page.getByRole("main").getByRole("heading", { level: 1 }),
        ).toBeVisible();
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        )
        .toBe(true);
      if (route === "/finding/BBCA") {
        await expect(
          page
            .getByRole("navigation")
            .getByRole("link", { name: "Discovery", exact: true }),
        ).toHaveAttribute("aria-current", "page");
        await expect(
          page.getByRole("link", { name: "Sumber evidence" }).first(),
        ).toBeVisible();
      }
      if (width === 1440 || width === 375) {
        await page.screenshot({
          path: `test-results/audit-${route.replaceAll("/", "-")}-${width}.png`,
          fullPage: true,
          animations: "disabled",
        });
      }
    }
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: "Ganti ke mode gelap" }).click();
  for (const route of [
    "/discovery",
    "/my-assets",
    "/finding/BBCA",
    "/comparison",
  ]) {
    await page.goto(route);
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    if (route === "/discovery" || route === "/my-assets")
      await expect(page.getByRole("article").first()).toBeVisible();
    else
      await expect(
        page.getByRole("main").getByRole("heading", { level: 1 }),
      ).toBeVisible();
    await page.screenshot({
      path: `test-results/audit-${route.replaceAll("/", "-")}-dark.png`,
      fullPage: true,
      animations: "disabled",
    });
  }
});

// Simulated responses only. Browser tests do not call Sectors or Gemini.
const finding = (symbol: string): Finding => ({
  id: symbol,
  symbol,
  company_name:
    symbol === "BBCA"
      ? "Bank Central Asia"
      : symbol === "BBRI"
        ? "Bank Rakyat Indonesia"
        : "Telekomunikasi Indonesia",
  sector: "Financials",
  research_relevance: symbol === "BBCA" ? 7.25 : 5.4,
  signal_groups: ["fundamental", "market_activity"],
  observation: ["Measured fixture for browser testing."],
  evidence: [
    {
      group: "fundamental",
      metric: "revenue_growth",
      value: 0.12,
      baseline: null,
      period: "year-over-year quarter (source supplied)",
      method: "Source-supplied ratio",
      source: "https://example.com/company-report",
      observed_at: null,
      retrieved_at: "2026-09-29T00:00:00Z",
      strength: 1,
    },
    ...(symbol === "BBRI"
      ? []
      : [
          {
            group: "market_activity" as const,
            metric: "price_change",
            value: -0.035,
            baseline: 100,
            period: "2026-09-01 to 2026-09-28",
            method: "(last - first) / first",
            source: "https://example.com/daily",
            observed_at: "2026-09-28",
            retrieved_at: "2026-09-29T00:00:00Z",
            strength: 0.7,
          },
        ]),
    {
      group: "investor_flow",
      metric: "foreign_imbalance",
      value: -0.2,
      baseline: 100,
      period: "2026-09-28",
      method: "net / (buy + sell)",
      source: "https://example.com/flow",
      observed_at: "2026-09-28",
      retrieved_at: "2026-09-29T00:00:00Z",
      strength: 1,
    },
  ],
  relevance_reason: {
    selected_focus: ["fundamental"],
    matched_groups: ["fundamental"],
    sector_match: true,
    group_strength: { fundamental: 1, market_activity: 0.7, investor_flow: 1 },
    availability_factor: 1,
    sector_factor: 1,
    focus_weights: { fundamental: 1, market_activity: 0.4, investor_flow: 0.4 },
  },
  reasoning: "Measured evidence is matched to research focus.",
  method: "Documented research relevance method.",
  retrieved_at: "2026-09-29T00:00:00Z",
  limitations: ["Measurements do not establish causes."],
  source_endpoints: ["https://example.com/company-report"],
});

async function mockApi(
  page: Page,
  saved: string[] = [],
  options: { failSave?: boolean; failFinding?: string } = {},
) {
  const profile: Profile = {
    id: "qa",
    sectors: ["Financials"],
    research_focus: ["fundamental"],
    horizon_days: 30,
    created_at: "2026-09-29",
    saved_assets: [...saved],
  };
  await page.addInitScript(() => {
    localStorage.setItem("marketlens.activeProfileId", "qa");
    if (!localStorage.getItem("marketlens.theme")) {
      localStorage.setItem("marketlens.theme", "light");
    }
  });
  await page.route("http://127.0.0.1:8001/**", async (route) => {
    const request = route.request(),
      path = new URL(request.url()).pathname;
    const headers = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
      "Access-Control-Allow-Headers": "content-type",
    };
    const respond = (json: unknown, status = 200) =>
      route.fulfill({ status, json, headers });
    if (request.method() === "OPTIONS") return respond({});
    if (path.endsWith("/comparison")) {
      const symbols: string[] = request.postDataJSON().symbols;
      if (symbols.includes(options.failFinding ?? ""))
        return respond(
          { detail: `Team 1 asset API unavailable for ${options.failFinding}` },
          502,
        );
      const findings = symbols.map(finding);
      return respond({
        symbols,
        assets: findings.map((f) => ({ ...f, methodology_version: "test-v1" })),
        metrics: [
          ...new Set(findings.flatMap((f) => f.evidence.map((e) => e.metric))),
        ].map((metric) => ({
          metric,
          group: "fundamental",
          values: Object.fromEntries(
            findings.map((f) => [
              f.symbol,
              f.evidence.find((e) => e.metric === metric)?.value ?? null,
            ]),
          ),
          evidence_by_symbol: Object.fromEntries(
            findings.map((f) => [
              f.symbol,
              f.evidence.find((e) => e.metric === metric) ?? null,
            ]),
          ),
          missing_symbols: findings
            .filter((f) => !f.evidence.some((e) => e.metric === metric))
            .map((f) => f.symbol),
          period_status:
            metric === "price_change" ? "missing_data" : "different_periods",
        })),
        shared_signal_groups: ["fundamental"],
        limitations: [
          "Matching labels do not establish identical calculation bases.",
        ],
      });
    }
    if (path.endsWith("/discovery"))
      return respond({
        title: "Your Relevance Findings",
        findings: ["BBCA", "BBRI", "TLKM"].map(finding),
        unavailable_assets: [],
        universe_size: 3,
      });
    const match = path.match(/\/assets\/([^/]+)(\/finding)?$/);
    if (match) {
      const symbol = match[1];
      if (match[2])
        return options.failFinding === symbol
          ? respond({ detail: "Upstream unavailable" }, 502)
          : respond(finding(symbol));
      if (request.method() === "PUT") {
        if (options.failSave) return respond({ detail: "Save failed" }, 500);
        profile.saved_assets = [...new Set([...profile.saved_assets, symbol])];
      }
      if (request.method() === "DELETE")
        profile.saved_assets = profile.saved_assets.filter((s) => s !== symbol);
      return respond(profile);
    }
    if (path.endsWith("/assets"))
      return respond({
        findings: profile.saved_assets.filter((s) => s !== "BAD").map(finding),
        unavailable_assets: profile.saved_assets.includes("BAD")
          ? [{ symbol: "BAD", error: "Data unavailable" }]
          : [],
      });
    return respond(profile);
  });
}

test("Discovery save persists across navigation and reload; removal works", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/discovery");
  await expect(
    page.getByRole("heading", { name: "Your Relevance Findings" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/discovery-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Tambah BBCA ke My Assets" }).click();
  await expect(
    page.getByRole("button", { name: "Tersimpan: BBCA" }),
  ).toBeDisabled();
  await page.getByRole("link", { name: "My Assets", exact: true }).click();
  await expect(page).toHaveURL(/\/my-assets$/);
  await expect(
    page.getByRole("article", { name: "BBCA", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("article", { name: "BBCA", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Hapus BBCA", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Mulai daftar risetmu" }),
  ).toBeVisible();
});

test("manual ticker normalization, duplicates and unavailable saved assets", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/my-assets");
  await page.getByLabel("Tambahkan aset").fill(" bbca.jk ");
  await page
    .getByRole("button", { name: "+ Tambah aset", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("BBCA ditambahkan");
  await page.getByLabel("Tambahkan aset").fill("BBCA");
  await page
    .getByRole("button", { name: "+ Tambah aset", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("sudah ada");
  await page.getByLabel("Tambahkan aset").fill("BAD");
  await page
    .getByRole("button", { name: "+ Tambah aset", exact: true })
    .click();
  await expect(
    page.getByRole("article", { name: "BAD", exact: true }),
  ).toContainText("Evidence belum tersedia");
  await page.getByRole("button", { name: "Hapus BAD", exact: true }).click();
  await expect(
    page.getByRole("article", { name: "BAD", exact: true }),
  ).toHaveCount(0);
});

test("save failure stays unsaved and exposes a retryable error", async ({
  page,
}) => {
  await mockApi(page, [], { failSave: true });
  await page.goto("/discovery");
  await page.getByRole("button", { name: "Tambah BBCA ke My Assets" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Gagal menyimpan",
  );
  await expect(
    page.getByRole("button", { name: "Tambah BBCA ke My Assets" }),
  ).toBeEnabled();
});

test("comparison shows periods, ratios and missing evidence", async ({
  page,
}) => {
  await mockApi(page, ["BBCA", "BBRI"]);
  await page.goto("/comparison");
  await expect(
    page.getByRole("button", { name: "Bandingkan aset →", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "+ BBCA", exact: true }).click();
  await page.getByRole("button", { name: "+ BBRI", exact: true }).click();
  await page
    .getByRole("button", { name: "Bandingkan aset →", exact: true })
    .click();
  await expect(page.getByRole("table")).toContainText("-20.00%");
  await expect(page.getByRole("table")).toContainText("Data unavailable");
  await expect(page.getByRole("table")).toContainText(
    "2026-09-01 to 2026-09-28",
  );
  await page.screenshot({
    path: "test-results/comparison-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Batalkan BBRI" }).click();
  await expect(page.getByRole("table")).toHaveCount(0);
});

test("comparison reports failed assets without inventing values", async ({
  page,
}) => {
  await mockApi(page, ["BBCA", "BBRI"], { failFinding: "BBRI" });
  await page.goto("/comparison");
  await page.getByRole("button", { name: "+ BBCA", exact: true }).click();
  await page.getByRole("button", { name: "+ BBRI", exact: true }).click();
  await page
    .getByRole("button", { name: "Bandingkan aset →", exact: true })
    .click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("BBRI");
  await expect(page.getByRole("table")).toHaveCount(0);
});

test("mobile navigation, detail save and theme work without horizontal page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);
  await page.goto("/discovery");
  await expect(page.getByRole("article").first()).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/discovery-mobile.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Detail →" }).first().click();
  await expect(page).toHaveURL(/\/finding\/BBCA$/);
  await page.getByRole("button", { name: "Tambah BBCA ke My Assets" }).click();
  await expect(
    page.getByRole("button", { name: "Tersimpan: BBCA" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Ganti ke mode gelap" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("link", { name: "Comparison", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Comparison", exact: true }),
  ).toBeVisible();
});

test("navigation reuses responses, manual refresh fetches again, TTL expires", async ({
  page,
}) => {
  await mockApi(page);
  let discovery = 0;
  page.on("request", (r) => {
    if (
      r.method() === "GET" &&
      r.url().endsWith("/discovery") &&
      r.url().includes(":8001")
    )
      discovery++;
  });
  await page.goto("/discovery");
  await expect(page.getByRole("article").first()).toBeVisible();
  expect(discovery).toBe(1);
  await page.getByRole("link", { name: "My Assets", exact: true }).click();
  await expect(page).toHaveURL(/\/my-assets$/);
  await expect(
    page.getByRole("heading", { name: "Mulai daftar risetmu" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Discovery", exact: true }).click();
  await expect(page.getByRole("article").first()).toBeVisible();
  expect(discovery).toBe(1);
  await page.getByRole("button", { name: /Perbarui temuan/ }).click();
  await expect(page.getByRole("article").first()).toBeVisible();
  expect(discovery).toBe(2);
  await page.clock.install();
  await page.clock.fastForward(61_000);
  await page.getByRole("link", { name: "My Assets", exact: true }).click();
  await expect(page).toHaveURL(/\/my-assets$/);
  await expect(
    page.getByRole("heading", { name: "Mulai daftar risetmu" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Discovery", exact: true }).click();
  await expect(page.getByRole("article").first()).toBeVisible();
  expect(discovery).toBe(3);
});

test("comparison sends one batch, reuses selection and displays backend cautions", async ({
  page,
}) => {
  await mockApi(page, ["BBCA", "BBRI"]);
  let batches = 0,
    details = 0;
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith("/comparison")) {
      batches++;
      expect(r.postDataJSON()).toEqual({ symbols: ["BBCA", "BBRI"] });
    }
    if (r.url().endsWith("/finding")) details++;
  });
  await page.goto("/comparison");
  await page.getByRole("button", { name: "+ BBCA", exact: true }).click();
  await page.getByRole("button", { name: "+ BBRI", exact: true }).click();
  await page.getByRole("button", { name: /Bandingkan aset/ }).click();
  await expect(page.getByRole("table")).toContainText("Periode berbeda");
  await expect(
    page.getByText(
      "Matching labels do not establish identical calculation bases.",
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: /Bandingkan aset/ }).click();
  await expect(page.getByRole("table")).toBeVisible();
  expect(batches).toBe(1);
  expect(details).toBe(0);
});

test("Discovery search, saved filter and sorting reuse loaded findings", async ({
  page,
}) => {
  await mockApi(page, ["TLKM"]);
  let requests = 0;
  page.on("request", (request) => {
    if (
      request.url().includes(":8001/") &&
      request.url().endsWith("/discovery")
    )
      requests++;
  });
  await page.goto("/discovery");
  await expect(page.getByRole("article")).toHaveCount(3);
  await page
    .getByRole("searchbox", { name: "Cari dalam temuan" })
    .fill("rakyat");
  await expect(page.getByRole("article")).toHaveCount(1);
  await expect(page.getByRole("article")).toHaveAttribute("aria-label", "BBRI");
  await page.getByRole("button", { name: "Hanya tersimpan" }).click();
  await expect(
    page.getByRole("heading", { name: "Tidak ada temuan yang cocok" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Tampilkan semua temuan" }).click();
  await page.getByRole("button", { name: "Hanya tersimpan" }).click();
  await expect(page.getByRole("article")).toHaveAttribute("aria-label", "TLKM");
  await page.getByRole("button", { name: "Reset filter" }).click();
  await page.getByRole("combobox", { name: "Urutkan" }).selectOption("ticker");
  await expect(page.getByRole("article")).toHaveCount(3);
  expect(
    await page
      .getByRole("article")
      .evaluateAll((items) =>
        items.map((item) => item.getAttribute("aria-label")),
      ),
  ).toEqual(["BBCA", "BBRI", "TLKM"]);
  expect(requests).toBe(1);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/discovery-interactive-mobile.png",
    fullPage: true,
  });
});

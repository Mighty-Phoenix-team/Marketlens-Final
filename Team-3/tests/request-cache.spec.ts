import { test, expect } from "@playwright/test";
import { cachedRequest, invalidateRequests } from "../lib/request-cache";

test("overlapping reads share a request; failed requests can retry", async () => {
  invalidateRequests("/");
  let resolve!: (value: number) => void;
  let calls = 0;
  const fetcher = () => {
    calls++;
    return new Promise<number>((r) => {
      resolve = r;
    });
  };
  const first = cachedRequest("/same", fetcher);
  const second = cachedRequest("/same", fetcher);
  expect(calls).toBe(1);
  resolve(42);
  expect(await Promise.all([first, second])).toEqual([42, 42]);
  await expect(
    cachedRequest("/failed", () => Promise.reject(new Error("offline"))),
  ).rejects.toThrow("offline");
  expect(await cachedRequest("/failed", async () => 7)).toBe(7);
});

test("mutation invalidation prevents a late response from restoring old cache", async () => {
  invalidateRequests("/");
  let resolve!: (value: string) => void;
  const old = cachedRequest(
    "/profile/a",
    () =>
      new Promise<string>((r) => {
        resolve = r;
      }),
  );
  invalidateRequests("/profile/a");
  expect(await cachedRequest("/profile/a", async () => "new")).toBe("new");
  resolve("old");
  await old;
  expect(await cachedRequest("/profile/a", async () => "unexpected")).toBe(
    "new",
  );
  expect(await cachedRequest("/profile/b", async () => "other profile")).toBe(
    "other profile",
  );
});

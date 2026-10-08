// Short-lived, per-tab cache. Never persists profile responses to disk.
const TTL_MS = 60_000;
const MAX_ENTRIES = 100;
const entries = new Map<string, { expires: number; value: unknown }>();
const pending = new Map<string, Promise<unknown>>();

export function invalidateRequests(prefix: string) {
  for (const key of entries.keys())
    if (key.startsWith(prefix)) entries.delete(key);
  // Detach old requests so they cannot repopulate the cache after a mutation.
  for (const key of pending.keys())
    if (key.startsWith(prefix)) pending.delete(key);
}

export function cachedRequest<T>(
  key: string,
  fetcher: () => Promise<T>,
  refresh = false,
): Promise<T> {
  const active = pending.get(key);
  if (active) return active as Promise<T>;
  const cached = entries.get(key);
  if (!refresh && cached && cached.expires > Date.now())
    return Promise.resolve(cached.value as T);
  entries.delete(key);
  const request = fetcher()
    .then((value) => {
      if (pending.get(key) === request) {
        if (entries.size >= MAX_ENTRIES)
          entries.delete(entries.keys().next().value!);
        entries.set(key, { value, expires: Date.now() + TTL_MS });
      }
      return value;
    })
    .finally(() => {
      if (pending.get(key) === request) pending.delete(key);
    });
  pending.set(key, request);
  return request;
}

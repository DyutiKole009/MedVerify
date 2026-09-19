/**
 * Helper to get or generate a persistent anonymous client UUIDv4 (§7).
 */
export function getAnonymousId(): string {
  const STORAGE_KEY = 'medverify_anonymous_id';
  let anonId = localStorage.getItem(STORAGE_KEY);
  if (!anonId) {
    anonId = 'anon-' + crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, anonId);
  }
  return anonId;
}

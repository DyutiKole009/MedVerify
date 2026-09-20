import type { CaseRecord } from '../components/cloudscape/DashboardView';

const ANON_STORAGE_KEY = 'medverify_anonymous_id';
const SESSIONS_STORAGE_KEY = 'medverify_saved_sessions';

/**
 * Helper to get or generate a persistent anonymous client UUIDv4 (§7).
 */
export function getAnonymousId(): string {
  let anonId = localStorage.getItem(ANON_STORAGE_KEY);
  if (!anonId) {
    anonId = 'anon-' + crypto.randomUUID();
    localStorage.setItem(ANON_STORAGE_KEY, anonId);
  }
  return anonId;
}

/**
 * Retrieve real past verification sessions stored locally for this client.
 */
export function getStoredVerificationSessions(): CaseRecord[] {
  try {
    const raw = localStorage.getItem(SESSIONS_STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

/**
 * Save a new real verification session to local client storage.
 */
export function saveStoredVerificationSession(record: CaseRecord): void {
  try {
    const existing = getStoredVerificationSessions();
    const updated = [record, ...existing.filter((s) => s.id !== record.id)].slice(0, 50);
    localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(updated));
  } catch (e) {
    console.warn('Failed to persist session:', e);
  }
}

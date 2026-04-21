const STORAGE_KEY = 'demo_session';

export interface DemoSession {
  session_token: string;
  demo_user_id: string;
  demo_course_id: number | null;
  full_name: string;
  expires_at: string;
}

export function getDemoSession(): DemoSession | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const session: DemoSession = JSON.parse(raw);
    if (new Date(session.expires_at) < new Date()) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

export function saveDemoSession(session: DemoSession): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearDemoSession(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(STORAGE_KEY);
}

export function demoHeaders(session: DemoSession | null): Record<string, string> {
  if (!session) return {};
  return { 'X-Demo-Token': session.session_token };
}

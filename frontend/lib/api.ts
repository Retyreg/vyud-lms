import type {
  ApiEdge,
  ApiNode,
  DashboardData,
  HealthInfo,
  ROIData,
  SOPDetail,
  SOPListItem,
  StreakInfo,
} from '@/types';

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'https://vyud-lms-backend.onrender.com';

/**
 * Returns X-Init-Data header when running inside Telegram Mini App.
 * Safe to call in SSR — guards against missing window.
 */
function tmaHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const initData = window.Telegram?.WebApp?.initData;
  return initData ? { 'X-Init-Data': initData } : {};
}

type GraphData = { nodes: ApiNode[]; edges: ApiEdge[] };

export async function fetchGraphData(orgId: number | null, userKey?: string): Promise<GraphData> {
  const base = orgId
    ? `${API_BASE_URL}/api/orgs/${orgId}/courses/latest`
    : `${API_BASE_URL}/api/courses/latest`;
  const endpoint = userKey ? `${base}?user_key=${encodeURIComponent(userKey)}` : base;
  const res = await fetch(endpoint);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchHealth(): Promise<HealthInfo> {
  const res = await fetch(`${API_BASE_URL}/api/health`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchDueNodes(orgId: number, userKey: string): Promise<number[]> {
  const res = await fetch(
    `${API_BASE_URL}/api/orgs/${orgId}/due-nodes?user_key=${encodeURIComponent(userKey)}`,
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.due_node_ids as number[];
}

export async function fetchStreak(userKey: string): Promise<StreakInfo> {
  const res = await fetch(`${API_BASE_URL}/api/streaks/${encodeURIComponent(userKey)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchExplanation(
  nodeId: number,
  regenerate = false,
): Promise<{ explanation: string; cached: boolean }> {
  const url = `${API_BASE_URL}/api/explain/${nodeId}${regenerate ? '?regenerate=true' : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function markNodeComplete(nodeId: number, userKey?: string): Promise<void> {
  await fetch(`${API_BASE_URL}/api/nodes/${nodeId}/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...tmaHeaders() },
    body: JSON.stringify({ user_key: userKey ?? '' }),
  });
}

export async function submitReview(
  nodeId: number,
  userKey: string,
  quality: 0 | 1 | 2 | 3,
): Promise<void> {
  await fetch(`${API_BASE_URL}/api/nodes/${nodeId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...tmaHeaders() },
    body: JSON.stringify({ user_key: userKey, quality }),
  });
}

export async function generateCourse(
  topic: string,
  orgId?: number | null,
  userKey?: string,
): Promise<void> {
  const url = orgId
    ? `${API_BASE_URL}/api/orgs/${orgId}/courses/generate?user_key=${encodeURIComponent(userKey ?? '')}`
    : `${API_BASE_URL}/api/courses/generate`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...tmaHeaders() },
    body: JSON.stringify({ topic }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? 'Ошибка генерации');
  }
}

export async function uploadCoursePdf(
  orgId: number,
  file: File,
  topic?: string,
): Promise<{ course_id: number; node_count: number }> {
  const formData = new FormData();
  formData.append('file', file);
  if (topic?.trim()) formData.append('topic', topic.trim());
  const res = await fetch(`${API_BASE_URL}/api/orgs/${orgId}/courses/upload-pdf`, {
    method: 'POST',
    headers: tmaHeaders(),
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? 'Ошибка загрузки PDF');
  }
  return res.json();
}

export async function createOrg(
  name: string,
  managerKey: string,
): Promise<{ org_id: number; org_name: string; invite_code: string }> {
  const res = await fetch(`${API_BASE_URL}/api/orgs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...tmaHeaders() },
    body: JSON.stringify({ name, manager_key: managerKey }),
  });
  if (!res.ok) throw new Error('Ошибка создания организации');
  return res.json();
}

export async function joinOrg(
  inviteCode: string,
  userKey: string,
): Promise<{ org_id: number; org_name: string }> {
  const res = await fetch(`${API_BASE_URL}/api/orgs/join?invite_code=${inviteCode}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...tmaHeaders() },
    body: JSON.stringify({ user_key: userKey }),
  });
  if (!res.ok) throw new Error('Неверный инвайт-код');
  return res.json();
}

export async function fetchOrgProgress(
  orgId: number,
  userKey?: string,
): Promise<DashboardData & { invite_code: string }> {
  const qs = userKey ? `?user_key=${encodeURIComponent(userKey)}` : '';
  const res = await fetch(`${API_BASE_URL}/api/orgs/${orgId}/progress${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchOrgROI(orgId: number): Promise<ROIData> {
  const res = await fetch(`${API_BASE_URL}/api/orgs/${orgId}/roi`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchOrgSops(orgId: number, userKey: string): Promise<SOPListItem[]> {
  const res = await fetch(
    `${API_BASE_URL}/api/orgs/${orgId}/sops?user_key=${encodeURIComponent(userKey)}`,
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchSop(sopId: number): Promise<SOPDetail> {
  const res = await fetch(`${API_BASE_URL}/api/sops/${sopId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function completeSop(
  sopId: number,
  userKey: string,
  score: number,
  maxScore: number,
): Promise<void> {
  await fetch(
    `${API_BASE_URL}/api/sops/${sopId}/complete?user_key=${encodeURIComponent(userKey)}&score=${score}&max_score=${maxScore}`,
    { method: 'POST', headers: tmaHeaders() },
  );
}

export interface OrgBrand {
  brand_color: string | null;
  logo_url: string | null;
  bot_username: string | null;
  display_name: string | null;
}

export async function fetchOrgInfo(
  orgId: number,
  userKey: string,
): Promise<{ org_id: number; org_name: string; invite_code: string; is_manager: boolean }> {
  const res = await fetch(
    `${API_BASE_URL}/api/orgs/${orgId}?user_key=${encodeURIComponent(userKey)}`,
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchOrgBrand(orgId: number): Promise<OrgBrand> {
  const res = await fetch(`${API_BASE_URL}/api/orgs/${orgId}/brand`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function updateOrgBrand(
  orgId: number,
  userKey: string,
  brand: Partial<OrgBrand>,
): Promise<OrgBrand> {
  const res = await fetch(
    `${API_BASE_URL}/api/orgs/${orgId}/brand?user_key=${encodeURIComponent(userKey)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...tmaHeaders() },
      body: JSON.stringify(brand),
    },
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function uploadSopPdf(
  orgId: number,
  file: File,
  userKey: string,
): Promise<{ sop_id: number; steps_count: number; quiz_count: number }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_key', userKey);
  const res = await fetch(`${API_BASE_URL}/api/orgs/${orgId}/sops/upload-pdf`, {
    method: 'POST',
    headers: tmaHeaders(),
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? 'Ошибка загрузки PDF');
  }
  return res.json();
}

import type {
  ApiEdge,
  ApiNode,
  DashboardData,
  HealthInfo,
  ROIData,
  StreakInfo,
} from '@/types';

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'https://vyud-lms-backend.onrender.com';

type GraphData = { nodes: ApiNode[]; edges: ApiEdge[] };

export async function fetchGraphData(orgId: number | null): Promise<GraphData> {
  const endpoint = orgId
    ? `${API_BASE_URL}/api/orgs/${orgId}/courses/latest`
    : `${API_BASE_URL}/api/courses/latest`;
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
    headers: { 'Content-Type': 'application/json' },
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
    headers: { 'Content-Type': 'application/json' },
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
    headers: { 'Content-Type': 'application/json' },
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
    headers: { 'Content-Type': 'application/json' },
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_key: userKey }),
  });
  if (!res.ok) throw new Error('Неверный инвайт-код');
  return res.json();
}

export async function fetchOrgProgress(orgId: number): Promise<DashboardData & { invite_code: string }> {
  const res = await fetch(`${API_BASE_URL}/api/orgs/${orgId}/progress`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchOrgROI(orgId: number): Promise<ROIData> {
  const res = await fetch(`${API_BASE_URL}/api/orgs/${orgId}/roi`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

"use client";

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, ReactFlowProvider, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://vyud-lms-backend.onrender.com";

const RETRY_MAX_ATTEMPTS = 6;
const RETRY_BASE_DELAY_MS = 5000;
const RETRY_MAX_DELAY_MS = 20000;

type BackendStatus = 'loading' | 'warming' | 'ok' | 'error';

interface HealthInfo {
  status: 'ok' | 'degraded' | 'error';
  uptime_seconds: number;
  database: 'connected' | 'not_configured' | 'error';
  database_error: string | null;
  ai_groq: 'configured' | 'not_configured';
  ai_gemini: 'configured' | 'not_configured';
}

interface ApiNode {
  id: number;
  label: string;
  level: number;
  is_completed: boolean;
  is_available: boolean;
}

interface ApiEdge {
  source: number;
  target: number;
}

interface FlowNode {
  id: string;
  data: { label: string; isAvailable: boolean };
}

function HealthPanel({ health, onRefresh }: { health: HealthInfo | null; onRefresh: () => void }) {
  const [open, setOpen] = useState(false);

  const dotColor = health === null
    ? '#94a3b8'
    : health.status === 'ok' ? '#22c55e'
    : health.status === 'degraded' ? '#f59e0b'
    : '#ef4444';

  const statusLabel = health === null ? 'Проверка...'
    : health.status === 'ok' ? 'Всё работает'
    : health.status === 'degraded' ? 'Частично'
    : 'Ошибка';

  return (
    <div style={{ position: 'absolute', top: 20, right: 20, zIndex: 30 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: 'white', border: '1px solid #e2e8f0',
          borderRadius: 8, padding: '6px 12px', cursor: 'pointer',
          boxShadow: '0 2px 6px rgba(0,0,0,0.08)', fontSize: 13,
        }}
      >
        <span style={{ width: 10, height: 10, borderRadius: '50%', background: dotColor, display: 'inline-block' }} />
        {statusLabel}
      </button>

      {open && (
        <div style={{
          marginTop: 6, background: 'white', border: '1px solid #e2e8f0',
          borderRadius: 10, padding: 16, width: 260,
          boxShadow: '0 4px 16px rgba(0,0,0,0.12)', fontSize: 13,
        }}>
          <div style={{ fontWeight: 600, marginBottom: 10, color: '#1e293b' }}>🩺 Статус системы</div>

          {health === null ? (
            <p style={{ color: '#64748b', margin: 0 }}>Загрузка...</p>
          ) : (
            <>
              <HealthRow label="Сервер" value={health.status === 'ok' ? '✅ Работает' : health.status === 'degraded' ? '⚠️ Частично' : '❌ Ошибка'} />
              <HealthRow
                label="База данных"
                value={
                  health.database === 'connected' ? '✅ Подключена' :
                  health.database === 'not_configured' ? '⚠️ Не настроена' : '❌ Ошибка'
                }
              />
              {health.database_error && (
                <div style={{ fontSize: 11, color: '#ef4444', marginBottom: 6, wordBreak: 'break-word' }}>
                  {health.database_error}
                </div>
              )}
              <HealthRow
                label="AI (Groq)"
                value={health.ai_groq === 'configured' ? '✅ Настроен' : '⚠️ Не настроен'}
              />
              <HealthRow
                label="AI (Gemini)"
                value={health.ai_gemini === 'configured' ? '✅ Настроен' : '⚠️ Не настроен'}
              />
              <HealthRow label="Аптайм" value={formatUptime(health.uptime_seconds)} />
            </>
          )}

          <button
            onClick={() => { onRefresh(); setOpen(false); }}
            style={{
              marginTop: 10, width: '100%', padding: '6px 0',
              background: '#f1f5f9', border: 'none', borderRadius: 6,
              cursor: 'pointer', fontSize: 12, color: '#475569',
            }}
          >
            🔄 Обновить
          </button>
        </div>
      )}
    </div>
  );
}

function HealthRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, color: '#334155' }}>
      <span style={{ color: '#64748b' }}>{label}</span>
      <span>{value}</span>
    </div>
  );
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}с`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}мин`;
  return `${Math.floor(seconds / 3600)}ч ${Math.floor((seconds % 3600) / 60)}мин`;
}

function Flow() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { fitView } = useReactFlow();

  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [nodeId, setNodeId] = useState<number | null>(null);
  const [isCached, setIsCached] = useState(false);
  const [orgId, setOrgId] = useState<number | null>(null);
  const [orgName, setOrgName] = useState<string | null>(null);
  const [showOrgSetup, setShowOrgSetup] = useState(false);
  const [inviteCode, setInviteCode] = useState('');
  const [userKey, setUserKey] = useState('');
  const [newCourseTopic, setNewCourseTopic] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('loading');
  const [hasNodes, setHasNodes] = useState(false);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/health`);
      if (res.ok) {
        setHealth(await res.json());
      }
    } catch {
      // health fetch is best-effort; ignore failures
    }
  }, []);

  const fetchGraph = useCallback(async (isRetry = false) => {
    if (!isRetry) {
      attemptRef.current = 0;
    }
    attemptRef.current += 1;
    const attempt = attemptRef.current;

    if (attempt > 1) {
      setBackendStatus('warming');
    } else {
      setBackendStatus('loading');
    }

    try {
      const currentOrgId = localStorage.getItem('vyud_org_id');
      const endpoint = currentOrgId
        ? `${API_BASE_URL}/api/orgs/${currentOrgId}/courses/latest`
        : `${API_BASE_URL}/api/courses/latest`;
      const res = await fetch(endpoint);

      if (!res.ok) {
        // 503 = DB not configured, still show the UI
        if (res.status === 503) {
          setBackendStatus('ok');
          fetchHealth();
          return;
        }
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      setBackendStatus('ok');
      fetchHealth();

      if (data?.nodes?.length > 0) {
        setHasNodes(true);
        const formattedNodes = data.nodes.map((node: ApiNode, idx: number) => ({
          id: String(node.id),
          position: { x: idx * 250, y: (node.level || 1) * 150 },
          data: { label: node.is_completed ? `${node.label} ✅` : node.label, isAvailable: node.is_available },
          style: {
            background: node.is_completed ? '#4ADE80' : node.is_available ? '#fff' : '#f3f4f6',
            border: node.is_available ? '2px solid #3b82f6' : '2px dashed #ccc',
            borderRadius: '12px', width: 200, padding: '10px', textAlign: 'center' as const,
          },
        }));

        const formattedEdges = data.edges.map((e: ApiEdge) => ({
          id: `e${e.source}-${e.target}`,
          source: String(e.source),
          target: String(e.target),
          animated: true,
        }));

        setNodes(formattedNodes);
        setEdges(formattedEdges);
        setTimeout(() => fitView({ duration: 800 }), 100);
      } else {
        setHasNodes(false);
      }
    } catch {
      // Server may be sleeping (free-tier cold start) — retry with growing delay
      if (attempt < RETRY_MAX_ATTEMPTS) {
        const delay = Math.min(RETRY_BASE_DELAY_MS * attempt, RETRY_MAX_DELAY_MS);
        setBackendStatus('warming');
        retryTimerRef.current = setTimeout(() => fetchGraph(true), delay);
      } else {
        setBackendStatus('error');
      }
    }
  }, [setNodes, setEdges, fitView, fetchHealth]);

  useEffect(() => {
    fetchGraph();
    return () => {
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    };
  }, [fetchGraph]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const invite = params.get('invite');
    const savedOrgId = localStorage.getItem('vyud_org_id');
    const savedOrgName = localStorage.getItem('vyud_org_name');

    if (savedOrgId) {
      setOrgId(Number(savedOrgId));
      setOrgName(savedOrgName);
    } else if (invite) {
      setInviteCode(invite);
      setShowOrgSetup(true);
    }
  }, []);

  const handleJoinOrg = async () => {
    if (!userKey.trim() || !inviteCode) return;
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/orgs/join?invite_code=${inviteCode}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_key: userKey }),
        }
      );
      if (!res.ok) throw new Error('Неверный код');
      const data = await res.json();
      localStorage.setItem('vyud_org_id', String(data.org_id));
      localStorage.setItem('vyud_org_name', data.org_name);
      setOrgId(data.org_id);
      setOrgName(data.org_name);
      setShowOrgSetup(false);
      fetchGraph();
    } catch {
      alert('Неверный инвайт-код или ошибка сети.');
    }
  };

  const handleGenerateCourse = async () => {
    if (!newCourseTopic.trim()) return;
    if (backendStatus === 'error') {
      alert("Сервер временно недоступен. Попробуйте позже.");
      return;
    }
    setIsGenerating(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/courses/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: newCourseTopic }),
      });
      if (res.ok) {
        setNewCourseTopic("");
        fetchGraph();
      } else {
        const error = await res.json();
        alert(`Ошибка: ${error.detail || "Что-то пошло не так"}`);
      }
    } catch {
      const msg = backendStatus === 'warming'
        ? "Сервер ещё не запустился — подождите немного и попробуйте снова."
        : "Ошибка сети. Сервер временно недоступен.";
      alert(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  const onNodeClick = async (_: React.MouseEvent, node: FlowNode, regenerate = false) => {
    if (!node.data.isAvailable) return alert("Тема заблокирована!");

    const id = Number(node.id);
    setSelectedTopic(node.data.label);
    setNodeId(id);
    setIsAiLoading(true);
    setExplanation(null);

    try {
      const url = `${API_BASE_URL}/api/explain/${id}${regenerate ? '?regenerate=true' : ''}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setExplanation(data.explanation);
      setIsCached(data.cached ?? false);
    } catch {
      setExplanation("Ошибка загрузки объяснения. Попробуйте ещё раз.");
      setIsCached(false);
    } finally {
      setIsAiLoading(false);
    }
  };

  const handleMarkComplete = async () => {
    if (!nodeId) return;
    try {
      await fetch(`${API_BASE_URL}/api/nodes/${nodeId}/complete`, { method: 'POST' });
      fetchGraph();
      setSelectedTopic(null);
    } catch {
      alert("Не удалось сохранить прогресс.");
    }
  };

  const statusBanner = () => {
    if (backendStatus === 'loading') {
      return (
        <div style={{ position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)', zIndex: 20, background: '#1e293b', color: 'white', padding: '10px 20px', borderRadius: 8, fontSize: 14 }}>
          ⏳ Подключаюсь к серверу...
        </div>
      );
    }
    if (backendStatus === 'warming') {
      return (
        <div style={{ position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)', zIndex: 20, background: '#92400e', color: 'white', padding: '10px 20px', borderRadius: 8, fontSize: 14 }}>
          🔄 Сервер просыпается. Подождите ~30 сек...
        </div>
      );
    }
    if (backendStatus === 'error') {
      return (
        <div
          style={{ position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)', zIndex: 20, background: '#7f1d1d', color: 'white', padding: '10px 20px', borderRadius: 8, fontSize: 14, cursor: 'pointer' }}
          onClick={() => fetchGraph()}
        >
          ❌ Сервер недоступен. Нажмите, чтобы повторить попытку
        </div>
      );
    }
    if (backendStatus === 'ok' && !hasNodes) {
      return (
        <div style={{ position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)', zIndex: 20, background: '#1e3a5f', color: 'white', padding: '10px 20px', borderRadius: 8, fontSize: 14 }}>
          ✨ Введите тему выше и нажмите «Создать», чтобы сгенерировать курс!
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#f8f9fa' }}>
      {/* Top-left: create course panel */}
      <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 10, background: 'white', padding: 20, borderRadius: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        <div style={{ marginBottom: 8, fontWeight: 600, fontSize: 16, color: '#1e293b' }}>🎓 VYUD LMS</div>
        <input
          value={newCourseTopic}
          onChange={(e) => setNewCourseTopic(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleGenerateCourse()}
          placeholder="Тема курса (напр. Python, React...)"
          style={{ padding: '8px', border: '1px solid #ddd', borderRadius: 6, marginRight: 10, width: 220 }}
        />
        <button
          onClick={handleGenerateCourse}
          disabled={isGenerating || backendStatus === 'loading' || backendStatus === 'warming'}
          style={{ padding: '8px 16px', background: isGenerating ? '#94a3b8' : '#3b82f6', color: 'white', border: 'none', borderRadius: 6, cursor: isGenerating ? 'not-allowed' : 'pointer' }}
        >
          {isGenerating ? "Генерация..." : "Создать"}
        </button>

        {orgName ? (
          <div style={{ marginTop: 10, fontSize: 12, color: '#64748b' }}>
            Org: <strong>{orgName}</strong>
            <button
              onClick={async () => {
                const res = await fetch(`${API_BASE_URL}/api/orgs/${orgId}/progress`);
                const data = await res.json();
                const code = data.invite_code;
                const url = `${window.location.origin}${window.location.pathname}?invite=${code}`;
                await navigator.clipboard.writeText(url);
                alert(`Ссылка скопирована:\n${url}`);
              }}
              style={{
                marginLeft: 8, fontSize: 11, padding: '2px 8px',
                background: '#f1f5f9', border: '1px solid #e2e8f0',
                borderRadius: 4, cursor: 'pointer',
              }}
            >
              Скопировать инвайт
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowOrgSetup(true)}
            style={{
              marginTop: 8, width: '100%', padding: '6px 0',
              background: '#f8fafc', border: '1px dashed #cbd5e1',
              borderRadius: 6, cursor: 'pointer', fontSize: 12, color: '#64748b',
            }}
          >
            + Создать организацию
          </button>
        )}
      </div>

      {/* Top-right: health status panel */}
      <HealthPanel health={health} onRefresh={() => { fetchGraph(); fetchHealth(); }} />

      <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onNodeClick={onNodeClick} fitView>
        <Background />
        <Controls />
      </ReactFlow>

      {statusBanner()}

      {/* Topic explanation panel */}
      {selectedTopic && (
        <div style={{
          position: 'absolute', top: 80, right: 20, width: 350,
          background: 'white', padding: 25, borderRadius: 12,
          boxShadow: '0 4px 20px rgba(0,0,0,0.15)', zIndex: 100,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <h3 style={{ margin: 0, fontSize: 16, color: '#1e293b' }}>{selectedTopic.replace(' ✅', '')}</h3>
            <button
              onClick={() => setSelectedTopic(null)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: '#94a3b8', lineHeight: 1 }}
            >✕</button>
          </div>

          {isAiLoading ? (
            <p style={{ color: '#64748b', fontSize: 14 }}>🤖 Думаю...</p>
          ) : (
            <>
              <p style={{ fontSize: 14, lineHeight: 1.6, color: '#334155', margin: '0 0 16px' }}>
                {explanation}
              </p>
              {isCached && (
                <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 10 }}>из кэша</div>
              )}
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={handleMarkComplete}
                  style={{
                    flex: 1, padding: '10px 0', background: '#22c55e',
                    color: 'white', border: 'none', borderRadius: 8,
                    cursor: 'pointer', fontSize: 14, fontWeight: 500,
                  }}
                >
                  Понятно ✓
                </button>
                <button
                  onClick={() => {
                    if (nodeId) {
                      const fakeNode = { id: String(nodeId), data: { label: selectedTopic, isAvailable: true } } as FlowNode;
                      onNodeClick({} as React.MouseEvent, fakeNode, true);
                    }
                  }}
                  style={{
                    flex: 1, padding: '10px 0', background: '#f1f5f9',
                    color: '#475569', border: 'none', borderRadius: 8,
                    cursor: 'pointer', fontSize: 14,
                  }}
                >
                  Иначе ↺
                </button>
              </div>
            </>
          )}
        </div>
      )}
      {showOrgSetup && (
        <div style={{
          position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200,
        }}>
          <div style={{
            background: 'white', borderRadius: 16, padding: 32,
            width: 360, boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
          }}>
            {inviteCode ? (
              <>
                <h3 style={{ marginTop: 0 }}>Вступить в команду</h3>
                <p style={{ color: '#64748b', fontSize: 14 }}>Введите ваш email чтобы присоединиться</p>
                <input
                  value={userKey}
                  onChange={e => setUserKey(e.target.value)}
                  placeholder="ваш@email.com"
                  style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 12, boxSizing: 'border-box' }}
                />
                <button
                  onClick={handleJoinOrg}
                  style={{ width: '100%', padding: 12, background: '#3b82f6', color: 'white', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 15 }}
                >
                  Присоединиться
                </button>
              </>
            ) : (
              <>
                <h3 style={{ marginTop: 0 }}>Создать организацию</h3>
                <input
                  placeholder="Название компании"
                  id="org-name-input"
                  style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 8, boxSizing: 'border-box' }}
                />
                <input
                  value={userKey}
                  onChange={e => setUserKey(e.target.value)}
                  placeholder="Ваш email (менеджер)"
                  style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 12, boxSizing: 'border-box' }}
                />
                <button
                  onClick={async () => {
                    const nameInput = document.getElementById('org-name-input') as HTMLInputElement;
                    if (!nameInput.value.trim() || !userKey.trim()) return;
                    const res = await fetch(`${API_BASE_URL}/api/orgs`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ name: nameInput.value, manager_key: userKey }),
                    });
                    const data = await res.json();
                    localStorage.setItem('vyud_org_id', String(data.org_id));
                    localStorage.setItem('vyud_org_name', data.org_name);
                    setOrgId(data.org_id);
                    setOrgName(data.org_name);
                    setShowOrgSetup(false);
                  }}
                  style={{ width: '100%', padding: 12, background: '#3b82f6', color: 'white', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 15 }}
                >
                  Создать
                </button>
              </>
            )}
            <button
              onClick={() => setShowOrgSetup(false)}
              style={{ width: '100%', marginTop: 8, padding: 10, background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
            >
              Отмена
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Page() {
  return (
    <ReactFlowProvider>
      <Flow />
    </ReactFlowProvider>
  );
}

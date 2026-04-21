'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Background,
  Controls,
  Edge,
  Node,
  ReactFlow,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  createOrg,
  fetchDueNodes,
  fetchExplanation,
  fetchGraphData,
  fetchHealth,
  fetchOrgBrand,
  fetchOrgInfo,
  fetchOrgProgress,
  fetchOrgROI,
  fetchStreak,
  generateCourse,
  joinOrg,
  submitReview,
  uploadCoursePdf,
  type OrgBrand,
} from '@/lib/api';
import { storage } from '@/lib/storage';
import { getTelegramStartParam, getTelegramUser, isTMA } from '@/lib/telegram';
import type {
  ApiEdge,
  ApiNode,
  BackendStatus,
  DashboardData,
  FlowNode,
  HealthInfo,
  ROIData,
  StreakInfo,
} from '@/types';

import { BrandSettingsModal } from '@/components/panels/BrandSettingsModal';
import { FeedbackWidget } from '@/components/panels/FeedbackWidget';
import { WelcomeTourModal } from '@/components/panels/WelcomeTourModal';
import { DemoBanner } from '@/components/panels/DemoBanner';
import { DemoFeedbackModal } from '@/components/panels/DemoFeedbackModal';
import { getDemoSession } from '@/lib/demo';
import { ControlPanel } from '@/components/panels/ControlPanel';
import { DashboardModal } from '@/components/panels/DashboardModal';
import { ExplanationPanel } from '@/components/panels/ExplanationPanel';
import { HealthPanel } from '@/components/panels/HealthPanel';
import { OrgSetupModal } from '@/components/panels/OrgSetupModal';
import { SOPListModal } from '@/components/panels/SOPListModal';
import { SOPViewerModal } from '@/components/panels/SOPViewerModal';
import { StreakModal } from '@/components/panels/StreakModal';
import { OnboardingChecklist } from '@/components/panels/OnboardingChecklist';
import { WizardModal } from '@/components/panels/WizardModal';

const RETRY_MAX_ATTEMPTS = 6;
const RETRY_BASE_DELAY_MS = 5000;
const RETRY_MAX_DELAY_MS = 20000;

/** Compute x-column for each node via topological BFS over prerequisite edges. */
function computeTopoColumns(nodes: ApiNode[], edges: ApiEdge[]): Map<number, number> {
  // incoming edge count and adjacency (source → targets)
  const inDegree = new Map<number, number>(nodes.map(n => [n.id, 0]));
  const adj = new Map<number, number[]>(nodes.map(n => [n.id, []]));
  for (const e of edges) {
    inDegree.set(e.target, (inDegree.get(e.target) ?? 0) + 1);
    adj.get(e.source)?.push(e.target);
  }
  const col = new Map<number, number>();
  const queue: number[] = [];
  for (const [id, deg] of inDegree) {
    if (deg === 0) { queue.push(id); col.set(id, 0); }
  }
  while (queue.length) {
    const id = queue.shift()!;
    const c = col.get(id) ?? 0;
    for (const next of (adj.get(id) ?? [])) {
      col.set(next, Math.max(col.get(next) ?? 0, c + 1));
      const deg = (inDegree.get(next) ?? 1) - 1;
      inDegree.set(next, deg);
      if (deg === 0) queue.push(next);
    }
  }
  // fallback for any node not reached (disconnected)
  let maxCol = 0;
  for (const c of col.values()) maxCol = Math.max(maxCol, c);
  for (const n of nodes) {
    if (!col.has(n.id)) col.set(n.id, ++maxCol);
  }
  return col;
}

/** Map mastery % to a background fill color (only for non-completed nodes). */
function masteryFill(pct: number): string {
  if (pct === 0)  return 'white';
  if (pct < 40)   return '#fffbeb'; // very light yellow
  if (pct < 70)   return '#fef3c7'; // light amber
  if (pct < 100)  return '#dcfce7'; // light green
  return '#4ADE80';                 // full green (same as completed)
}

function buildFlowNodes(nodes: ApiNode[], dueNodeIds: Set<number>, edges: ApiEdge[] = []) {
  const colMap = computeTopoColumns(nodes, edges);
  const colCount = new Map<number, number>();
  return nodes.map((node) => {
    const col = colMap.get(node.id) ?? 0;
    const rowIdx = colCount.get(col) ?? 0;
    colCount.set(col, rowIdx + 1);
    const pct = node.mastery_pct ?? 0;
    const labelText = node.is_completed ? `${node.label} ✅` : node.label;
    const masteryLabel = pct > 0 && !node.is_completed
      ? `\n${pct}% освоено`
      : '';
    return {
      id: String(node.id),
      position: { x: col * 260, y: rowIdx * 160 },
      data: {
        label: labelText + masteryLabel,
        isAvailable: node.is_available,
        mastery_pct: pct,
        next_review: node.next_review,
      },
      style: {
        background: node.is_completed
          ? '#4ADE80'
          : dueNodeIds.has(node.id)
          ? masteryFill(pct)
          : node.is_available
          ? masteryFill(pct)
          : '#f3f4f6',
        border: node.is_completed
          ? '2px solid #16a34a'
          : dueNodeIds.has(node.id)
          ? '2px solid #f59e0b'
          : node.is_available
          ? '2px solid #3b82f6'
          : '2px dashed #ccc',
        borderRadius: '12px',
        width: 200,
        padding: '10px',
        textAlign: 'center' as const,
        whiteSpace: 'pre-line' as const,
      },
    };
  });
}

function buildFlowEdges(edges: ApiEdge[]) {
  return edges.map(e => ({
    id: `e${e.source}-${e.target}`,
    source: String(e.source),
    target: String(e.target),
    animated: true,
  }));
}

export function KnowledgeGraph() {
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<Node>([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const { fitView } = useReactFlow();

  // Graph / backend state
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('loading');
  const [hasNodes, setHasNodes] = useState(false);
  const [dueNodeIds, setDueNodeIds] = useState<Set<number>>(new Set());
  const [health, setHealth] = useState<HealthInfo | null>(null);

  // Org / user state
  const [orgId, setOrgId] = useState<number | null>(null);
  const [orgName, setOrgName] = useState<string | null>(null);
  const [userKey, setUserKey] = useState('');
  const [inviteCode, setInviteCode] = useState('');

  // AI explanation state
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [isCached, setIsCached] = useState(false);

  // Course generation state
  const [courseTopic, setCourseTopic] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPdfUploading, setIsPdfUploading] = useState(false);

  // Dashboard state
  const [showDashboard, setShowDashboard] = useState(false);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [roiData, setRoiData] = useState<ROIData | null>(null);
  const [isDashboardLoading, setIsDashboardLoading] = useState(false);

  // Streak state
  const [streakInfo, setStreakInfo] = useState<StreakInfo | null>(null);

  // Modal state
  const [showOrgSetup, setShowOrgSetup] = useState(false);
  const [wizardStep, setWizardStep] = useState<0 | 1 | 2 | 3>(0);
  const [wizardOrgId, setWizardOrgId] = useState<number | null>(null);
  const [wizardInviteCode, setWizardInviteCode] = useState('');
  const [isWizardGenerating, setIsWizardGenerating] = useState(false);

  // SOP state
  const [showSopList, setShowSopList] = useState(false);
  const [selectedSopId, setSelectedSopId] = useState<number | null>(null);

  // Streak modal
  const [showStreak, setShowStreak] = useState(false);

  // Demo mode
  const [showDemoFeedback, setShowDemoFeedback] = useState(false);
  const demoSession = typeof window !== 'undefined' ? getDemoSession() : null;

  // Brand / white-label
  const [orgBrand, setOrgBrand] = useState<OrgBrand | null>(null);
  const [showBrandSettings, setShowBrandSettings] = useState(false);
  const [isManager, setIsManager] = useState(false);

  // Welcome tour
  const [showTour, setShowTour] = useState(false);

  // TMA state — populated when running inside Telegram Mini App
  const [tmaManagerKey, setTmaManagerKey] = useState<string | undefined>();
  const [tmaDisplayName, setTmaDisplayName] = useState<string | undefined>();

  // Toast
  const [toast, setToast] = useState<string | null>(null);

  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  // ── Health ──────────────────────────────────────────────────────────────────

  const loadHealth = useCallback(async () => {
    try { setHealth(await fetchHealth()); } catch { /* best-effort */ }
  }, []);

  // ── Graph ───────────────────────────────────────────────────────────────────

  const loadGraph = useCallback(async (isRetry = false) => {
    if (!isRetry) attemptRef.current = 0;
    attemptRef.current += 1;
    const attempt = attemptRef.current;

    setBackendStatus(attempt > 1 ? 'warming' : 'loading');

    try {
      const currentOrgId = storage.getOrgId();
      const currentUserKey = storage.getUserKey() ?? undefined;
      const data = await fetchGraphData(currentOrgId, currentUserKey);
      setBackendStatus('ok');
      loadHealth();

      if (data?.nodes?.length > 0) {
        setHasNodes(true);
        const savedKey = storage.getUserKey();
        const savedOrgIdNum = currentOrgId;

        if (savedOrgIdNum && savedKey) {
          fetchDueNodes(savedOrgIdNum, savedKey)
            .then(ids => setDueNodeIds(new Set(ids)))
            .catch(() => {});
        }

        setRfNodes(buildFlowNodes(data.nodes, dueNodeIds, data.edges));
        setRfEdges(buildFlowEdges(data.edges));
        setTimeout(() => fitView({ duration: 800 }), 100);
      } else {
        setHasNodes(false);
      }
    } catch {
      if (attempt < RETRY_MAX_ATTEMPTS) {
        const delay = Math.min(RETRY_BASE_DELAY_MS * attempt, RETRY_MAX_DELAY_MS);
        setBackendStatus('warming');
        retryTimerRef.current = setTimeout(() => loadGraph(true), delay);
      } else {
        setBackendStatus('error');
      }
    }
  }, [setRfNodes, setRfEdges, fitView, loadHealth, dueNodeIds]);

  // Apply yellow border to due nodes after dueNodeIds updates
  useEffect(() => {
    if (dueNodeIds.size === 0) return;
    setRfNodes(prev =>
      prev.map(n => {
        const id = Number(n.id);
        if (!dueNodeIds.has(id)) return n;
        const isCompleted = (n.data.label as string).endsWith('✅');
        if (isCompleted) return n;
        return { ...n, style: { ...n.style, border: '2px solid #f59e0b' } };
      }),
    );
  }, [dueNodeIds, setRfNodes]);

  useEffect(() => {
    // ── Telegram Mini App init ────────────────────────────────────────────────
    if (isTMA()) {
      window.Telegram!.WebApp.ready();
      window.Telegram!.WebApp.expand();

      const tgUser = getTelegramUser();
      if (tgUser) {
        const key = String(tgUser.id);
        storage.setUserKey(key);
        setUserKey(key);
        const displayName = [tgUser.first_name, tgUser.last_name].filter(Boolean).join(' ')
          + (tgUser.username ? ` (@${tgUser.username})` : '');
        setTmaManagerKey(key);
        setTmaDisplayName(displayName);
      }
    }

    // Show welcome tour once to new visitors
    if (!localStorage.getItem('vyud_tour_seen')) {
      setShowTour(true);
    }

    const params = new URLSearchParams(window.location.search);
    // In TMA, invite code comes via start_param; in browser via ?invite=
    const invite = getTelegramStartParam() ?? params.get('invite');
    const savedOrgId = storage.getOrgId();
    const savedOrgName = storage.getOrgName();
    const savedKey = storage.getUserKey();

    if (savedKey) {
      setUserKey(savedKey);
      fetchStreak(savedKey).then(s => setStreakInfo(s.current_streak > 0 ? s : null)).catch(() => {});
    }

    if (savedOrgId) {
      setOrgId(savedOrgId);
      setOrgName(savedOrgName);
      loadBrand(savedOrgId);
      if (savedKey) {
        fetchOrgInfo(savedOrgId, savedKey)
          .then(info => setIsManager(info.is_manager))
          .catch(() => {});
      }
    } else if (invite) {
      setInviteCode(invite);
      setShowOrgSetup(true);
    } else {
      setWizardStep(1);
    }

    loadGraph();
    return () => { if (retryTimerRef.current) clearTimeout(retryTimerRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Brand ───────────────────────────────────────────────────────────────────

  const loadBrand = useCallback(async (id: number) => {
    try {
      const brand = await fetchOrgBrand(id);
      setOrgBrand(brand);
      // Apply brand color to TMA header if available
      if (isTMA() && brand.brand_color && window.Telegram?.WebApp?.setHeaderColor) {
        try { window.Telegram.WebApp.setHeaderColor(brand.brand_color); } catch { /* not supported */ }
      }
    } catch { /* best-effort */ }
  }, []);

  // ── Dashboard ───────────────────────────────────────────────────────────────

  const loadDashboard = useCallback(async () => {
    if (!orgId) return;
    setIsDashboardLoading(true);
    try {
      const [progress, roi] = await Promise.all([
        fetchOrgProgress(orgId, userKey),
        fetchOrgROI(orgId),
      ]);
      setDashboardData(progress);
      setRoiData(roi);
    } catch { /* best-effort */ }
    finally { setIsDashboardLoading(false); }
  }, [orgId]);

  // ── Node click → explanation ─────────────────────────────────────────────────

  const handleNodeClick = useCallback(async (
    _: React.MouseEvent,
    node: Node,
    regenerate = false,
  ) => {
    const data = node.data as FlowNode['data'];
    if (!data.isAvailable) { alert('Тема заблокирована!'); return; }
    const id = Number(node.id);
    setSelectedTopic(data.label);
    setSelectedNodeId(id);
    setIsAiLoading(true);
    setExplanation(null);
    try {
      const data = await fetchExplanation(id, regenerate);
      setExplanation(data.explanation);
      setIsCached(data.cached);
    } catch {
      setExplanation('Ошибка загрузки объяснения. Попробуйте ещё раз.');
      setIsCached(false);
    } finally {
      setIsAiLoading(false);
    }
  }, []);

  const handleReview = useCallback(async (quality: 0 | 1 | 2 | 3) => {
    if (!selectedNodeId) return;
    const key = storage.getUserKey() || 'anonymous';
    await submitReview(selectedNodeId, key, quality).catch(() => {});
    loadGraph();
    fetchStreak(key).then(s => setStreakInfo(s.current_streak > 0 ? s : null)).catch(() => {});
    setSelectedTopic(null);
  }, [selectedNodeId, loadGraph]);

  // ── Course generation ────────────────────────────────────────────────────────

  const handleGenerateCourse = useCallback(async () => {
    if (!courseTopic.trim() || backendStatus === 'error') return;
    setIsGenerating(true);
    try {
      await generateCourse(courseTopic, orgId, userKey);
      setCourseTopic('');
      loadGraph();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Ошибка генерации');
    } finally {
      setIsGenerating(false);
    }
  }, [courseTopic, backendStatus, orgId, userKey, loadGraph]);

  const handlePdfUpload = useCallback(async (file: File) => {
    const savedOrgId = storage.getOrgId();
    if (!savedOrgId) { alert('Сначала создайте или вступите в организацию'); return; }
    setIsPdfUploading(true);
    try {
      const data = await uploadCoursePdf(savedOrgId, file, courseTopic);
      loadGraph();
      showToast(`✅ Граф создан из PDF! ${data.node_count} узлов`);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Ошибка загрузки PDF');
    } finally {
      setIsPdfUploading(false);
    }
  }, [courseTopic, loadGraph]);

  // ── Org management ───────────────────────────────────────────────────────────

  const handleJoinOrg = useCallback(async (key: string) => {
    try {
      const data = await joinOrg(inviteCode, key);
      storage.setOrgId(data.org_id);
      storage.setOrgName(data.org_name);
      storage.setUserKey(key);
      setOrgId(data.org_id);
      setOrgName(data.org_name);
      setUserKey(key);
      setIsManager(false);
      setShowOrgSetup(false);
      loadBrand(data.org_id);
      loadGraph();
    } catch { alert('Неверный инвайт-код или ошибка сети.'); }
  }, [inviteCode, loadGraph, loadBrand]);

  const handleCreateOrg = useCallback(async (name: string, key: string) => {
    try {
      const data = await createOrg(name, key);
      storage.setOrgId(data.org_id);
      storage.setOrgName(data.org_name);
      storage.setUserKey(key);
      setOrgId(data.org_id);
      setOrgName(data.org_name);
      setUserKey(key);
      setIsManager(true);
      setShowOrgSetup(false);
    } catch { alert('Ошибка создания организации'); }
  }, []);

  const handleCopyInvite = useCallback(async () => {
    if (!orgId) return;
    try {
      const progress = await fetchOrgProgress(orgId, userKey);
      const url = `${window.location.origin}${window.location.pathname}?invite=${progress.invite_code}`;
      await navigator.clipboard.writeText(url);
      showToast('✅ Ссылка скопирована!');
    } catch { alert('Не удалось скопировать'); }
  }, [orgId]);

  // ── Wizard ───────────────────────────────────────────────────────────────────

  const handleWizardCreateOrg = useCallback(async (name: string, email: string) => {
    try {
      const data = await createOrg(name, email);
      storage.setOrgId(data.org_id);
      storage.setOrgName(data.org_name);
      storage.setUserKey(email);
      setOrgId(data.org_id);
      setOrgName(data.org_name);
      setUserKey(email);
      setIsManager(true);
      setWizardOrgId(data.org_id);
      setWizardStep(2);
    } catch { alert('Ошибка создания организации'); }
  }, []);

  const handleWizardGenerateCourse = useCallback(async (topic: string) => {
    if (!wizardOrgId) return;
    setIsWizardGenerating(true);
    try {
      await generateCourse(topic, wizardOrgId, storage.getUserKey());
      const progress = await fetchOrgProgress(wizardOrgId, storage.getUserKey());
      setWizardInviteCode(progress.invite_code ?? '');
      loadGraph();
      setWizardStep(3);
    } catch { alert('Ошибка генерации'); }
    finally { setIsWizardGenerating(false); }
  }, [wizardOrgId, loadGraph]);

  const handleWizardPdfUpload = useCallback(async (file: File) => {
    if (!wizardOrgId) return;
    setIsWizardGenerating(true);
    try {
      await uploadCoursePdf(wizardOrgId, file);
      const progress = await fetchOrgProgress(wizardOrgId, storage.getUserKey());
      setWizardInviteCode(progress.invite_code ?? '');
      loadGraph();
      setWizardStep(3);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Ошибка загрузки PDF');
    } finally { setIsWizardGenerating(false); }
  }, [wizardOrgId, loadGraph]);

  // ── Status banner ────────────────────────────────────────────────────────────

  const statusBanner = () => {
    const base: React.CSSProperties = {
      position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)',
      zIndex: 20, color: 'white', padding: '10px 20px', borderRadius: 8, fontSize: 14,
    };
    if (backendStatus === 'loading')
      return <div style={{ ...base, background: '#1e293b' }}>⏳ Подключаюсь к серверу...</div>;
    if (backendStatus === 'warming')
      return <div style={{ ...base, background: '#92400e' }}>🔄 Сервер просыпается. Подождите ~30 сек...</div>;
    if (backendStatus === 'error')
      return (
        <div style={{ ...base, background: '#7f1d1d', cursor: 'pointer' }} onClick={() => loadGraph()}>
          ❌ Сервер недоступен. Нажмите, чтобы повторить попытку
        </div>
      );
    if (backendStatus === 'ok' && !hasNodes)
      return <div style={{ ...base, background: '#1e3a5f' }}>✨ Введите тему выше и нажмите «Создать»!</div>;
    return null;
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#f8f9fa' }}>
      {demoSession && (
        <DemoBanner onFeedbackClick={() => setShowDemoFeedback(true)} />
      )}
      {showDemoFeedback && demoSession && (
        <DemoFeedbackModal
          session={demoSession}
          onClose={() => setShowDemoFeedback(false)}
        />
      )}
      <ControlPanel
        topic={courseTopic}
        onTopicChange={setCourseTopic}
        onGenerate={handleGenerateCourse}
        onPdfUpload={handlePdfUpload}
        isGenerating={isGenerating}
        isPdfUploading={isPdfUploading}
        backendStatus={backendStatus}
        streakInfo={streakInfo}
        orgName={orgName}
        onShowDashboard={() => { setShowDashboard(true); loadDashboard(); }}
        onShowSops={() => setShowSopList(true)}
        onShowStreak={() => setShowStreak(true)}
        onCopyInvite={handleCopyInvite}
        onCreateOrg={() => setShowOrgSetup(true)}
        onShowTour={() => setShowTour(true)}
      />

      <HealthPanel health={health} onRefresh={() => { loadGraph(); loadHealth(); }} />

      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>

      {statusBanner()}

      {selectedTopic && (
        <ExplanationPanel
          topic={selectedTopic}
          explanation={explanation}
          isLoading={isAiLoading}
          isCached={isCached}
          nodeId={selectedNodeId}
          userKey={userKey}
          masteryPct={rfNodes.find(n => n.id === String(selectedNodeId))?.data.mastery_pct as number | undefined}
          nextReview={rfNodes.find(n => n.id === String(selectedNodeId))?.data.next_review as string | null | undefined}
          onClose={() => setSelectedTopic(null)}
          onReview={handleReview}
          onRegenerate={() => {
            if (selectedNodeId && selectedTopic) {
              handleNodeClick(
                {} as React.MouseEvent,
                {
                  id: String(selectedNodeId),
                  position: { x: 0, y: 0 },
                  data: { label: selectedTopic, isAvailable: true },
                } as Node,
                true,
              );
            }
          }}
        />
      )}

      {isPdfUploading && (
        <div style={{
          position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200,
        }}>
          <div style={{
            background: 'white', borderRadius: 16, padding: '32px 48px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.2)', fontSize: 18, color: '#1e293b',
          }}>
            📄 Обрабатываю PDF...
          </div>
        </div>
      )}

      {toast && (
        <div style={{
          position: 'fixed', bottom: 80, left: '50%', transform: 'translateX(-50%)',
          background: '#16a34a', color: 'white', padding: '12px 24px',
          borderRadius: 10, fontSize: 15, zIndex: 300,
          boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
        }}>
          {toast}
        </div>
      )}

      {showDashboard && (
        <DashboardModal
          dashboardData={dashboardData}
          roiData={roiData}
          isLoading={isDashboardLoading}
          isManager={isManager}
          onClose={() => setShowDashboard(false)}
          onRefresh={loadDashboard}
          onCopyReport={() => {
            if (!roiData) return;
            const text = [
              `VYUD LMS | ${roiData.org_name} | ${new Date().toLocaleDateString('ru-RU')}`,
              `Команда: ${roiData.total_members} чел | Активных: ${roiData.active_members}`,
              `Completion Rate: ${roiData.avg_completion_rate.toFixed(1)}%`,
              `Efficiency Score: ${roiData.onboarding_efficiency_score.toFixed(1)}/100`,
              roiData.summary,
            ].join('\n');
            navigator.clipboard.writeText(text);
            showToast('✅ Скопировано для отчёта!');
          }}
          onCopyInvite={() => {
            if (!dashboardData) return;
            const url = `${window.location.origin}${window.location.pathname}?invite=${dashboardData.invite_code}`;
            navigator.clipboard.writeText(url);
            showToast('✅ Ссылка скопирована!');
          }}
          onShowBrand={() => setShowBrandSettings(true)}
        />
      )}

      {showBrandSettings && orgId && (
        <BrandSettingsModal
          orgId={orgId}
          userKey={userKey}
          orgName={orgName ?? ''}
          inviteCode={dashboardData?.invite_code ?? ''}
          initialBrand={orgBrand ?? { brand_color: null, logo_url: null, bot_username: null, display_name: null }}
          onClose={() => setShowBrandSettings(false)}
          onSaved={brand => {
            setOrgBrand(brand);
            if (isTMA() && brand.brand_color && window.Telegram?.WebApp?.setHeaderColor) {
              try { window.Telegram.WebApp.setHeaderColor(brand.brand_color); } catch { /* not supported */ }
            }
            showToast('✅ Брендинг сохранён!');
          }}
        />
      )}

      {wizardStep > 0 && (
        <WizardModal
          step={wizardStep as 1 | 2 | 3}
          inviteCode={wizardInviteCode}
          isGenerating={isWizardGenerating}
          onClose={() => setWizardStep(0)}
          onCreateOrg={handleWizardCreateOrg}
          onGenerateCourse={handleWizardGenerateCourse}
          onUploadPdf={handleWizardPdfUpload}
          onFinish={() => setWizardStep(0)}
          onCopyInvite={() => {
            const url = `${window.location.origin}?invite=${wizardInviteCode}`;
            navigator.clipboard.writeText(url);
            showToast('✅ Ссылка скопирована!');
          }}
          telegramManagerKey={tmaManagerKey}
          telegramDisplayName={tmaDisplayName}
        />
      )}

      {showOrgSetup && (
        <OrgSetupModal
          inviteCode={inviteCode}
          onJoin={handleJoinOrg}
          onCreate={handleCreateOrg}
          onClose={() => setShowOrgSetup(false)}
        />
      )}

      {showStreak && streakInfo && (
        <StreakModal
          streakInfo={streakInfo}
          onClose={() => setShowStreak(false)}
        />
      )}

      <FeedbackWidget userKey={userKey || undefined} />

      <OnboardingChecklist
        orgCreated={!!orgId}
        courseCreated={hasNodes}
        nodeCompleted={rfNodes.some(n => (n.data.label as string).endsWith('✅'))}
        onCopyInvite={handleCopyInvite}
        onCreateOrg={() => setWizardStep(1)}
        onGenerateCourse={() => setWizardStep(1)}
      />

      {showSopList && orgId && (
        <SOPListModal
          orgId={orgId}
          userKey={userKey}
          onClose={() => setShowSopList(false)}
          onSelectSop={id => { setSelectedSopId(id); setShowSopList(false); }}
          onToast={showToast}
        />
      )}

      {showTour && (
        <WelcomeTourModal
          onClose={() => {
            setShowTour(false);
            localStorage.setItem('vyud_tour_seen', '1');
          }}
          onStartWizard={() => {
            setShowTour(false);
            localStorage.setItem('vyud_tour_seen', '1');
            setWizardStep(1);
          }}
        />
      )}

      {selectedSopId && orgId && (
        <SOPViewerModal
          sopId={selectedSopId}
          userKey={userKey}
          onClose={() => setSelectedSopId(null)}
          onCompleted={(_id, score, max) => {
            showToast(max > 0 ? `✅ СОП пройден! ${score}/${max}` : '✅ СОП отмечен как пройденный');
          }}
        />
      )}
    </div>
  );
}

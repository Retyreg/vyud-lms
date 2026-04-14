'use client';

import { useState, useEffect } from 'react';

interface ChecklistState {
  orgCreated: boolean;
  courseCreated: boolean;
  memberInvited: boolean;
  nodeCompleted: boolean;
  dismissed: boolean;
}

interface Props {
  orgCreated: boolean;
  courseCreated: boolean;
  nodeCompleted: boolean;
  onCopyInvite: () => void;
  onCreateOrg: () => void;
  onGenerateCourse: () => void;
}

const STORAGE_KEY = 'vyud_onboarding';

const STEPS = [
  { key: 'orgCreated',     icon: '🏢', label: 'Создать организацию' },
  { key: 'courseCreated',  icon: '📚', label: 'Создать первый курс' },
  { key: 'memberInvited',  icon: '👥', label: 'Пригласить сотрудника' },
  { key: 'nodeCompleted',  icon: '✅', label: 'Пройти первый узел' },
] as const;

export function OnboardingChecklist({ orgCreated, courseCreated, nodeCompleted, onCopyInvite, onCreateOrg, onGenerateCourse }: Props) {
  const [state, setState] = useState<ChecklistState>({
    orgCreated: false,
    courseCreated: false,
    memberInvited: false,
    nodeCompleted: false,
    dismissed: false,
  });
  const [collapsed, setCollapsed] = useState(false);

  // Load from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) setState(JSON.parse(saved));
    } catch {}
  }, []);

  // Sync props → state (marks steps complete when they happen)
  useEffect(() => {
    setState(prev => {
      const next = {
        ...prev,
        orgCreated: prev.orgCreated || orgCreated,
        courseCreated: prev.courseCreated || courseCreated,
        nodeCompleted: prev.nodeCompleted || nodeCompleted,
      };
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, [orgCreated, courseCreated, nodeCompleted]);

  const markInvited = () => {
    onCopyInvite();
    setState(prev => {
      const next = { ...prev, memberInvited: true };
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  };

  const dismiss = () => {
    setState(prev => {
      const next = { ...prev, dismissed: true };
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  };

  const completedCount = STEPS.filter(s => state[s.key]).length;
  const allDone = completedCount === STEPS.length;

  // Hide after all done + dismissed, or just dismissed
  if (state.dismissed) return null;

  return (
    <div style={{
      position: 'fixed', bottom: 80, right: 20, zIndex: 200,
      width: 260, background: 'white', borderRadius: 12,
      boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
      border: '1px solid #e2e8f0', overflow: 'hidden',
    }}>
      {/* Header */}
      <div
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 14px', background: allDone ? '#f0fdf4' : '#eff6ff',
          cursor: 'pointer',
        }}
        onClick={() => setCollapsed(c => !c)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16 }}>{allDone ? '🎉' : '🚀'}</span>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#1e293b' }}>
              {allDone ? 'Готово к работе!' : 'Быстрый старт'}
            </div>
            <div style={{ fontSize: 11, color: '#64748b' }}>{completedCount} / {STEPS.length} шагов</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <span style={{ color: '#94a3b8', fontSize: 14 }}>{collapsed ? '▲' : '▼'}</span>
          <button
            onClick={e => { e.stopPropagation(); dismiss(); }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', fontSize: 16, lineHeight: 1 }}
          >×</button>
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 3, background: '#e2e8f0' }}>
        <div style={{
          height: '100%', background: allDone ? '#22c55e' : '#3b82f6',
          width: `${(completedCount / STEPS.length) * 100}%`,
          transition: 'width 0.4s ease',
        }} />
      </div>

      {/* Steps */}
      {!collapsed && (
        <div style={{ padding: '8px 0' }}>
          {STEPS.map(({ key, icon, label }) => {
            const done = state[key];
            return (
              <div
                key={key}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '7px 14px',
                  background: done ? '#f8fafc' : 'white',
                }}
              >
                <div style={{
                  width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
                  background: done ? '#22c55e' : '#f1f5f9',
                  border: done ? 'none' : '1px solid #e2e8f0',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11,
                }}>
                  {done ? '✓' : icon}
                </div>
                <span style={{ fontSize: 13, color: done ? '#94a3b8' : '#334155', flex: 1, textDecoration: done ? 'line-through' : 'none' }}>
                  {label}
                </span>
                {/* Action button for incomplete steps */}
                {!done && key === 'orgCreated' && (
                  <button onClick={onCreateOrg} style={actionBtn}>Создать</button>
                )}
                {!done && key === 'courseCreated' && orgCreated && (
                  <button onClick={onGenerateCourse} style={actionBtn}>Открыть</button>
                )}
                {!done && key === 'memberInvited' && orgCreated && (
                  <button onClick={markInvited} style={actionBtn}>Копировать</button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const actionBtn: React.CSSProperties = {
  fontSize: 11, padding: '3px 8px', borderRadius: 6,
  background: '#eff6ff', border: '1px solid #bfdbfe',
  color: '#2563eb', cursor: 'pointer', whiteSpace: 'nowrap',
};

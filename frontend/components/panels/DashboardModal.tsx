'use client';

import type { DashboardData, ROIData, WeekActivity } from '@/types';

interface Props {
  dashboardData: DashboardData | null;
  roiData: ROIData | null;
  isLoading: boolean;
  isManager?: boolean;
  onClose: () => void;
  onRefresh: () => void;
  onCopyReport: () => void;
  onCopyInvite: () => void;
  onShowBrand?: () => void;
}

function BarChart({ data }: { data: WeekActivity[] }) {
  const max = Math.max(...data.map(d => d.reviews), 1);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 60 }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
          <div style={{ fontSize: 10, color: '#94a3b8' }}>{d.reviews || ''}</div>
          <div style={{
            width: '100%', borderRadius: '3px 3px 0 0',
            background: d.reviews > 0 ? '#3b82f6' : '#e2e8f0',
            height: `${Math.max(4, (d.reviews / max) * 44)}px`,
            transition: 'height 0.3s ease',
          }} />
          <div style={{ fontSize: 9, color: '#94a3b8', whiteSpace: 'nowrap' }}>{d.week_label}</div>
        </div>
      ))}
    </div>
  );
}

function KpiCard({ value, label, color = '#3b82f6' }: { value: string; label: string; color?: string }) {
  return (
    <div style={{
      background: '#f8fafc', borderRadius: 10, padding: '12px 14px',
      border: '1px solid #e2e8f0', textAlign: 'center',
    }}>
      <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 3 }}>{label}</div>
    </div>
  );
}

function medalFor(rank: number): string {
  if (rank === 0) return '🥇';
  if (rank === 1) return '🥈';
  if (rank === 2) return '🥉';
  return `${rank + 1}.`;
}

function barColor(pct: number): string {
  if (pct >= 80) return '#22c55e';
  if (pct >= 50) return '#f59e0b';
  return '#ef4444';
}

export function DashboardModal({
  dashboardData,
  roiData,
  isLoading,
  isManager,
  onClose,
  onRefresh,
  onCopyReport,
  onCopyInvite,
  onShowBrand,
}: Props) {
  const inviteUrl = typeof window !== 'undefined' && dashboardData
    ? `${window.location.origin}${window.location.pathname}?invite=${dashboardData.invite_code}`
    : '';

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200, padding: 16,
    }}>
      <div style={{
        background: 'white', borderRadius: 16, padding: 24,
        width: '100%', maxWidth: 580, maxHeight: '88vh', overflowY: 'auto',
        boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
      }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 17, color: '#1e293b' }}>
              📊 {dashboardData?.org_name ?? 'Дашборд'}
            </h2>
            {roiData && (
              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                {roiData.active_members} из {roiData.total_members} участников активны
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {isManager && onShowBrand && (
              <button onClick={onShowBrand} style={btnGhost} title="Брендинг">🎨</button>
            )}
            <button onClick={onRefresh} disabled={isLoading} style={btnGhost}>
              {isLoading ? '⏳' : '🔄'}
            </button>
            <button onClick={onClose} style={{ ...btnGhost, fontSize: 18 }}>✕</button>
          </div>
        </div>

        {/* KPI row */}
        {roiData && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 20 }}>
            <KpiCard
              value={`${roiData.avg_completion_rate.toFixed(0)}%`}
              label="Completion Rate"
              color={barColor(roiData.avg_completion_rate)}
            />
            <KpiCard
              value={`${roiData.onboarding_efficiency_score.toFixed(0)}/100`}
              label="Efficiency Score"
              color="#8b5cf6"
            />
            <KpiCard
              value={roiData.avg_days_to_first_completion !== null
                ? `${roiData.avg_days_to_first_completion.toFixed(1)} дн.`
                : '—'}
              label="Ср. дней онбординга"
              color="#f59e0b"
            />
          </div>
        )}

        {/* Weekly activity */}
        {roiData && roiData.weekly_activity.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8, fontWeight: 600 }}>
              Активность по неделям (повторения)
            </div>
            <BarChart data={roiData.weekly_activity} />
          </div>
        )}

        {/* Invite bar */}
        {dashboardData && (
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            <div style={{
              flex: 1, background: '#f8fafc', border: '1px solid #e2e8f0',
              borderRadius: 8, padding: '8px 12px', fontSize: 12, color: '#334155',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {inviteUrl}
            </div>
            <button onClick={onCopyInvite} style={btnBlue}>📋 Пригласить</button>
          </div>
        )}

        {/* Leaderboard */}
        {isLoading && !dashboardData ? (
          <div style={{ textAlign: 'center', padding: '32px 0', color: '#64748b' }}>⏳ Загрузка...</div>
        ) : dashboardData && dashboardData.members.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px 0', color: '#64748b', fontSize: 14 }}>
            Пока никто не вступил. Поделитесь инвайт-ссылкой!
          </div>
        ) : dashboardData ? (
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8, fontWeight: 600 }}>
              Лидерборд
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {dashboardData.members.map((m, i) => (
                <div key={m.user_key} style={{
                  padding: '10px 14px', background: i === 0 ? '#fefce8' : '#f8fafc',
                  border: `1px solid ${i === 0 ? '#fde68a' : '#e2e8f0'}`, borderRadius: 10,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 16 }}>{medalFor(i)}</span>
                      <span style={{ fontSize: 13, fontWeight: 500, color: '#1e293b' }}>
                        {m.user_key}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      {m.current_streak > 0 && (
                        <span style={{ fontSize: 12, color: '#f59e0b' }}>🔥 {m.current_streak}</span>
                      )}
                      <span style={{ fontSize: 12, color: '#64748b' }}>
                        {m.completed_count}/{m.total_count} · {m.percent.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  {/* Progress bar */}
                  <div style={{ background: '#e2e8f0', borderRadius: 999, height: 6, overflow: 'hidden' }}>
                    <div style={{
                      width: `${m.percent}%`, height: '100%',
                      background: barColor(m.percent), borderRadius: 999,
                      transition: 'width 0.4s ease',
                    }} />
                  </div>
                  {m.avg_mastery_pct > 0 && (
                    <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                      Мастерство: {m.avg_mastery_pct}%
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {/* ROI summary */}
        {roiData && (
          <div style={{
            background: '#eff6ff', borderLeft: '3px solid #3b82f6',
            borderRadius: 8, padding: '12px 16px',
          }}>
            <div style={{ fontSize: 13, color: '#1e40af', marginBottom: 10 }}>
              {roiData.summary}
              {roiData.fastest_member && (
                <span style={{ display: 'block', marginTop: 4, color: '#2563eb' }}>
                  🏆 Лидер: {roiData.fastest_member}
                </span>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={onCopyReport} style={btnBlue}>📋 Скопировать отчёт</button>
              <span style={{ fontSize: 11, color: '#64748b', alignSelf: 'center' }}>
                {roiData.total_reviews} повторений всего · стрик {roiData.avg_streak.toFixed(1)} дн.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const btnGhost: React.CSSProperties = {
  background: 'none', border: 'none', cursor: 'pointer',
  fontSize: 14, color: '#94a3b8', padding: '4px 8px', borderRadius: 6,
};

const btnBlue: React.CSSProperties = {
  padding: '6px 12px', background: '#dbeafe', border: '1px solid #93c5fd',
  borderRadius: 6, cursor: 'pointer', fontSize: 12, color: '#1d4ed8',
  whiteSpace: 'nowrap',
};

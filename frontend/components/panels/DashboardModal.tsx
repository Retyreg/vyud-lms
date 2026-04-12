'use client';

import type { DashboardData, ROIData } from '@/types';

interface Props {
  dashboardData: DashboardData | null;
  roiData: ROIData | null;
  isLoading: boolean;
  onClose: () => void;
  onRefresh: () => void;
  onCopyReport: () => void;
  onCopyInvite: () => void;
}

export function DashboardModal({
  dashboardData,
  roiData,
  isLoading,
  onClose,
  onRefresh,
  onCopyReport,
  onCopyInvite,
}: Props) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200,
    }}>
      <div style={{
        background: 'white', borderRadius: 16, padding: 32,
        width: '100%', maxWidth: 560, maxHeight: '80vh', overflowY: 'auto',
        boxShadow: '0 8px 32px rgba(0,0,0,0.25)', position: 'relative',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 18, color: '#1e293b' }}>
            📊 Прогресс команды{dashboardData ? ` — ${dashboardData.org_name}` : ''}
          </h2>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20, color: '#94a3b8', lineHeight: 1 }}
          >✕</button>
        </div>

        {dashboardData && (
          <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              flex: 1, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8,
              padding: '8px 12px', fontSize: 12, color: '#334155', wordBreak: 'break-all',
            }}>
              {`${typeof window !== 'undefined' ? window.location.origin : ''}${typeof window !== 'undefined' ? window.location.pathname : ''}?invite=${dashboardData.invite_code}`}
            </div>
            <button
              onClick={onCopyInvite}
              style={{
                padding: '8px 12px', background: '#f1f5f9', border: '1px solid #e2e8f0',
                borderRadius: 8, cursor: 'pointer', fontSize: 12, whiteSpace: 'nowrap',
              }}
            >📋 Копировать</button>
          </div>
        )}

        <button
          onClick={onRefresh}
          disabled={isLoading}
          style={{
            marginBottom: 16, padding: '6px 14px', background: '#f1f5f9',
            border: '1px solid #e2e8f0', borderRadius: 8,
            cursor: isLoading ? 'not-allowed' : 'pointer', fontSize: 13, color: '#475569',
          }}
        >
          {isLoading ? '⏳ Загрузка...' : '🔄 Обновить'}
        </button>

        {isLoading && !dashboardData ? (
          <div style={{ textAlign: 'center', padding: '32px 0', color: '#64748b', fontSize: 14 }}>
            <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
            Загрузка данных...
          </div>
        ) : dashboardData && dashboardData.members.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 0', color: '#64748b', fontSize: 14 }}>
            Пока никто не вступил. Поделитесь инвайт-ссылкой!
          </div>
        ) : dashboardData ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {dashboardData.members.map(member => {
              const barColor =
                member.percent <= 30 ? '#ef4444' :
                member.percent <= 70 ? '#f59e0b' : '#22c55e';
              return (
                <div key={member.user_key} style={{
                  padding: '12px 16px', background: '#f8fafc',
                  border: '1px solid #e2e8f0', borderRadius: 10,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 500, color: '#1e293b' }}>{member.user_key}</span>
                    <span style={{ fontSize: 12, color: '#64748b' }}>
                      {member.completed_count} / {member.total_count} узлов ({member.percent.toFixed(0)}%)
                    </span>
                  </div>
                  <div style={{ background: '#e2e8f0', borderRadius: 999, height: 8, overflow: 'hidden' }}>
                    <div style={{
                      width: `${member.percent}%`, height: '100%',
                      background: barColor, borderRadius: 999,
                      transition: 'width 0.4s ease',
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        ) : null}

        {roiData && (
          <div style={{ marginTop: 24 }}>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#1e293b', marginBottom: 12 }}>
              📈 ROI &amp; Аналитика
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
              {[
                { value: `${roiData.avg_completion_rate.toFixed(1)}%`, label: '🎯 Completion Rate' },
                { value: `${roiData.onboarding_efficiency_score.toFixed(1)} / 100`, label: '⚡ Efficiency Score' },
                {
                  value: roiData.avg_days_to_first_completion !== null
                    ? roiData.avg_days_to_first_completion.toFixed(1) : '—',
                  label: '📅 Ср. дней онбординга',
                },
                { value: `${roiData.avg_streak.toFixed(1)} дн`, label: '🔥 Ср. Streak' },
              ].map(({ value, label }) => (
                <div key={label} style={{
                  background: '#f8fafc', borderRadius: 10, padding: 14, border: '1px solid #e2e8f0',
                }}>
                  <div style={{ fontSize: 24, fontWeight: 700, color: '#3b82f6' }}>{value}</div>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>{label}</div>
                </div>
              ))}
            </div>
            <div style={{
              background: '#eff6ff', borderLeft: '3px solid #3b82f6',
              borderRadius: 8, padding: '12px 16px',
            }}>
              <div style={{ fontSize: 13, color: '#1e40af', marginBottom: 10 }}>{roiData.summary}</div>
              <button
                onClick={onCopyReport}
                style={{
                  padding: '6px 12px', background: '#dbeafe', border: '1px solid #93c5fd',
                  borderRadius: 6, cursor: 'pointer', fontSize: 12, color: '#1d4ed8',
                }}
              >
                📋 Скопировать для отчёта
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

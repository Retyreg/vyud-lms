'use client';

import React, { useMemo } from 'react';
import type { StreakInfo } from '@/types';

interface Props {
  streakInfo: StreakInfo;
  onClose: () => void;
}

const CELL_SIZE = 12;
const CELL_GAP = 3;
const WEEKS = 15;
const DAYS = 7;

/** Build a set of active date strings for O(1) lookup */
function useActivitySet(dates: string[]): Set<string> {
  return useMemo(() => new Set(dates), [dates]);
}

/** Return ISO date string for a cell at (weekIndex, dayIndex) counting back from today */
function cellDate(today: Date, weekIdx: number, dayIdx: number): string {
  const totalDaysBack = (WEEKS - 1 - weekIdx) * 7 + (6 - dayIdx);
  const d = new Date(today);
  d.setDate(d.getDate() - totalDaysBack);
  return d.toISOString().slice(0, 10);
}

const DAY_LABELS = ['Пн', '', 'Ср', '', 'Пт', '', 'Вс'];

export function StreakModal({ streakInfo, onClose }: Props) {
  const today = useMemo(() => new Date(), []);
  const activitySet = useActivitySet(streakInfo.activity_dates);

  const { current_streak, longest_streak, total_days_active, badge, achievements, next_milestone } = streakInfo;

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 300, padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#1a1a2e', borderRadius: 16, padding: 24, maxWidth: 480,
          width: '100%', color: '#fff', boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 40, lineHeight: 1 }}>{current_streak > 0 ? '🔥' : '💤'}</div>
            <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4 }}>
              {current_streak} {current_streak === 1 ? 'день' : current_streak >= 2 && current_streak <= 4 ? 'дня' : 'дней'}
            </div>
            <div style={{ fontSize: 13, color: '#9ca3af', marginTop: 2 }}>
              {badge ?? 'Начни учиться сегодня'}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent', border: 'none', color: '#9ca3af',
              fontSize: 22, cursor: 'pointer', lineHeight: 1,
            }}
          >×</button>
        </div>

        {/* Stats row */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 20,
        }}>
          {[
            { label: 'Текущая серия', value: `${current_streak} дн.` },
            { label: 'Рекорд', value: `${longest_streak} дн.` },
            { label: 'Всего дней', value: total_days_active },
          ].map(({ label, value }) => (
            <div key={label} style={{
              background: '#16213e', borderRadius: 10, padding: '10px 12px', textAlign: 'center',
            }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#f59e0b' }}>{value}</div>
              <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Heatmap */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 8 }}>Активность за 15 недель</div>
          <div style={{ display: 'flex', gap: CELL_GAP }}>
            {/* Day labels */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: CELL_GAP, marginRight: 4 }}>
              {DAY_LABELS.map((label, i) => (
                <div key={i} style={{
                  height: CELL_SIZE, fontSize: 9, color: '#6b7280',
                  display: 'flex', alignItems: 'center',
                }}>{label}</div>
              ))}
            </div>
            {/* Grid */}
            {Array.from({ length: WEEKS }, (_, wi) => (
              <div key={wi} style={{ display: 'flex', flexDirection: 'column', gap: CELL_GAP }}>
                {Array.from({ length: DAYS }, (_, di) => {
                  const iso = cellDate(today, wi, di);
                  const active = activitySet.has(iso);
                  const isToday = iso === today.toISOString().slice(0, 10);
                  return (
                    <div
                      key={di}
                      title={iso}
                      style={{
                        width: CELL_SIZE,
                        height: CELL_SIZE,
                        borderRadius: 2,
                        background: active ? '#f59e0b' : '#2d2d4e',
                        border: isToday ? '1px solid #f59e0b' : '1px solid transparent',
                        opacity: active ? 1 : 0.5,
                      }}
                    />
                  );
                })}
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: '#2d2d4e', opacity: 0.5 }} />
            <span style={{ fontSize: 10, color: '#6b7280' }}>Нет активности</span>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: '#f59e0b', marginLeft: 8 }} />
            <span style={{ fontSize: 10, color: '#6b7280' }}>Активный день</span>
          </div>
        </div>

        {/* Achievements */}
        {achievements.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 8 }}>Достижения</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {achievements.map(a => (
                <span key={a.id} style={{
                  background: '#16213e', borderRadius: 20, padding: '4px 10px',
                  fontSize: 12, color: '#f59e0b', border: '1px solid #374151',
                }}>
                  {a.label}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Next milestone */}
        {next_milestone && (
          <div style={{
            background: '#16213e', borderRadius: 10, padding: '10px 14px',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{ fontSize: 12, color: '#9ca3af' }}>Следующее достижение</div>
              <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>{next_milestone.label}</div>
            </div>
            <div style={{
              background: '#f59e0b', color: '#000', borderRadius: 20,
              padding: '4px 10px', fontSize: 12, fontWeight: 700,
            }}>
              ещё {next_milestone.days_left} дн.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

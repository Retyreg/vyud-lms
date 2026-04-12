'use client';

import { useState } from 'react';
import type { HealthInfo } from '@/types';

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}с`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}мин`;
  return `${Math.floor(seconds / 3600)}ч ${Math.floor((seconds % 3600) / 60)}мин`;
}

function HealthRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, color: '#334155' }}>
      <span style={{ color: '#64748b' }}>{label}</span>
      <span>{value}</span>
    </div>
  );
}

interface Props {
  health: HealthInfo | null;
  onRefresh: () => void;
}

export function HealthPanel({ health, onRefresh }: Props) {
  const [open, setOpen] = useState(false);

  const dotColor =
    health === null ? '#94a3b8' :
    health.status === 'ok' ? '#22c55e' :
    health.status === 'degraded' ? '#f59e0b' : '#ef4444';

  const statusLabel =
    health === null ? 'Проверка...' :
    health.status === 'ok' ? 'Система работает' :
    health.status === 'degraded' ? 'Частичный сбой' : 'Ошибка';

  return (
    <div style={{ position: 'absolute', top: 20, right: 20, zIndex: 10 }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
          background: 'white', border: '1px solid #e2e8f0', borderRadius: 20,
          cursor: 'pointer', fontSize: 13, color: '#475569',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
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
              <HealthRow
                label="Сервер"
                value={health.status === 'ok' ? '✅ Работает' : health.status === 'degraded' ? '⚠️ Частично' : '❌ Ошибка'}
              />
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
              <HealthRow label="AI (Groq)" value={health.ai_groq === 'configured' ? '✅ Настроен' : '⚠️ Не настроен'} />
              <HealthRow label="AI (Gemini)" value={health.ai_gemini === 'configured' ? '✅ Настроен' : '⚠️ Не настроен'} />
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

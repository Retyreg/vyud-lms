'use client';

import { useEffect, useState } from 'react';
import { API_BASE_URL } from '@/lib/api';

interface DemoUserRow {
  id: string;
  email: string;
  full_name: string;
  company: string;
  role: string;
  industry: string;
  created_at: string;
  session_days_left: number;
  archived: boolean;
  ai_calls_today: number;
  feedback_count: number;
  wants_pilot: boolean;
}

interface FeedbackRow {
  id: string;
  demo_user_email: string;
  company: string;
  rating: number;
  message: string | null;
  wants_pilot: boolean;
  created_at: string;
}

export default function AdminDemoPage() {
  const [adminEmail, setAdminEmail] = useState('');
  const [authed, setAuthed] = useState(false);
  const [users, setUsers] = useState<DemoUserRow[]>([]);
  const [feedback, setFeedback] = useState<FeedbackRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<'users' | 'feedback'>('users');

  async function load(email: string) {
    setLoading(true);
    setError('');
    try {
      const [usersRes, fbRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/admin/demo/users`, {
          headers: { 'X-Admin-Email': email },
        }),
        fetch(`${API_BASE_URL}/api/v1/admin/demo/feedback`, {
          headers: { 'X-Admin-Email': email },
        }),
      ]);
      if (!usersRes.ok) throw new Error('Нет доступа или неверный email');
      setUsers(await usersRes.json());
      setFeedback(await fbRes.json());
      setAuthed(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ошибка');
    } finally {
      setLoading(false);
    }
  }

  if (!authed) {
    return (
      <div style={pageStyle}>
        <div style={cardStyle}>
          <h1 style={h1}>Демо-дашборд</h1>
          <p style={sub}>Только для @Retyreg</p>
          <input
            style={inputStyle}
            type="email"
            placeholder="Admin email"
            value={adminEmail}
            onChange={e => setAdminEmail(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && load(adminEmail)}
          />
          {error && <p style={{ color: '#DC2626', fontSize: 13 }}>{error}</p>}
          <button style={btnStyle} onClick={() => load(adminEmail)} disabled={loading}>
            {loading ? 'Загружаем...' : 'Войти'}
          </button>
        </div>
      </div>
    );
  }

  const pilotCount = users.filter(u => u.wants_pilot).length;
  const activeCount = users.filter(u => !u.archived).length;
  const avgRating = feedback.length
    ? (feedback.reduce((s, f) => s + f.rating, 0) / feedback.length).toFixed(1)
    : '—';

  return (
    <div style={pageStyle}>
      <div style={{ maxWidth: 1100, width: '100%' }}>
        <h1 style={{ ...h1, marginBottom: 4 }}>Демо-пользователи</h1>
        <p style={sub}>Только чтение · Обновить: <button style={refreshBtn} onClick={() => load(adminEmail)}>↻</button></p>

        {/* Stats */}
        <div style={statsRow}>
          {[
            { label: 'Всего зарегистрировано', value: users.length },
            { label: 'Активных сессий', value: activeCount },
            { label: 'Хотят пилот', value: pilotCount },
            { label: 'Отзывов', value: feedback.length },
            { label: 'Средний рейтинг', value: avgRating },
          ].map(({ label, value }) => (
            <div key={label} style={statCard}>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#0F172A' }}>{value}</div>
              <div style={{ fontSize: 11, color: '#6B7280' }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div style={tabRow}>
          {(['users', 'feedback'] as const).map(t => (
            <button
              key={t}
              style={{ ...tabBtn, ...(tab === t ? tabActive : {}) }}
              onClick={() => setTab(t)}
            >
              {t === 'users' ? `Пользователи (${users.length})` : `Отзывы (${feedback.length})`}
            </button>
          ))}
        </div>

        {tab === 'users' && (
          <div style={tableWrap}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  {['Имя', 'Email', 'Компания', 'Роль', 'Отрасль', 'Дата', 'Сессия', 'AI сегодня', 'Отзывов', 'Пилот'].map(h => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id} style={{ opacity: u.archived ? 0.5 : 1 }}>
                    <td style={td}>{u.full_name}</td>
                    <td style={td}>{u.email}</td>
                    <td style={td}>{u.company}</td>
                    <td style={td}>{u.role}</td>
                    <td style={td}>{u.industry}</td>
                    <td style={td}>{u.created_at ? new Date(u.created_at).toLocaleDateString('ru') : '—'}</td>
                    <td style={td}>{u.archived ? 'Архив' : `${u.session_days_left}ч`}</td>
                    <td style={{ ...td, textAlign: 'center' }}>{u.ai_calls_today}</td>
                    <td style={{ ...td, textAlign: 'center' }}>{u.feedback_count}</td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      {u.wants_pilot ? <span style={pilotBadge}>✓ Да</span> : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'feedback' && (
          <div style={tableWrap}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  {['Email', 'Компания', 'Оценка', 'Сообщение', 'Пилот', 'Дата'].map(h => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {feedback.map(f => (
                  <tr key={f.id}>
                    <td style={td}>{f.demo_user_email}</td>
                    <td style={td}>{f.company}</td>
                    <td style={{ ...td, textAlign: 'center' }}>{'★'.repeat(f.rating)}{'☆'.repeat(5 - f.rating)}</td>
                    <td style={{ ...td, maxWidth: 300 }}>{f.message || '—'}</td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      {f.wants_pilot ? <span style={pilotBadge}>✓ Да</span> : '—'}
                    </td>
                    <td style={td}>{f.created_at ? new Date(f.created_at).toLocaleDateString('ru') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  minHeight: '100vh',
  background: '#F8FAFC',
  padding: '32px 16px',
  display: 'flex',
  justifyContent: 'center',
  fontFamily: 'Inter, system-ui, sans-serif',
};
const cardStyle: React.CSSProperties = {
  background: 'white',
  borderRadius: 12,
  padding: 32,
  width: '100%',
  maxWidth: 360,
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
  boxShadow: '0 4px 6px -1px rgba(0,0,0,0.07)',
};
const h1: React.CSSProperties = { fontSize: 22, fontWeight: 800, color: '#0F172A', margin: 0 };
const sub: React.CSSProperties = { fontSize: 13, color: '#6B7280', margin: 0 };
const inputStyle: React.CSSProperties = {
  border: '1px solid #E5E7EB',
  borderRadius: 8,
  padding: '10px 12px',
  fontSize: 14,
  outline: 'none',
};
const btnStyle: React.CSSProperties = {
  background: '#4F46E5',
  color: 'white',
  border: 'none',
  borderRadius: 8,
  padding: '11px 16px',
  fontSize: 14,
  fontWeight: 700,
  cursor: 'pointer',
};
const refreshBtn: React.CSSProperties = {
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  color: '#4F46E5',
  fontSize: 16,
};
const statsRow: React.CSSProperties = {
  display: 'flex',
  gap: 12,
  flexWrap: 'wrap',
  margin: '20px 0',
};
const statCard: React.CSSProperties = {
  background: 'white',
  border: '1px solid #E5E7EB',
  borderRadius: 10,
  padding: '14px 20px',
  minWidth: 140,
};
const tabRow: React.CSSProperties = { display: 'flex', gap: 8, marginBottom: 16 };
const tabBtn: React.CSSProperties = {
  background: 'white',
  border: '1px solid #E5E7EB',
  borderRadius: 8,
  padding: '8px 16px',
  fontSize: 13,
  cursor: 'pointer',
  color: '#374151',
};
const tabActive: React.CSSProperties = {
  background: '#EEF2FF',
  border: '1.5px solid #4F46E5',
  color: '#4338CA',
  fontWeight: 600,
};
const tableWrap: React.CSSProperties = {
  overflowX: 'auto',
  background: 'white',
  borderRadius: 10,
  border: '1px solid #E5E7EB',
};
const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: 13,
};
const th: React.CSSProperties = {
  textAlign: 'left',
  padding: '10px 14px',
  background: '#F8FAFC',
  borderBottom: '1px solid #E5E7EB',
  fontWeight: 600,
  color: '#374151',
  whiteSpace: 'nowrap',
};
const td: React.CSSProperties = {
  padding: '10px 14px',
  borderBottom: '1px solid #F1F5F9',
  color: '#1E293B',
  verticalAlign: 'top',
};
const pilotBadge: React.CSSProperties = {
  background: '#DCFCE7',
  color: '#15803D',
  borderRadius: 4,
  padding: '2px 8px',
  fontSize: 11,
  fontWeight: 600,
};

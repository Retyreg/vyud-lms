'use client';

import { useState } from 'react';
import { API_BASE_URL } from '@/lib/api';

const ROLES = ['Manager', 'L&D', 'Owner', 'Other'];
const INDUSTRIES = ['HoReCa', 'Retail', 'FMCG', 'Other'];

const INDUSTRY_LABELS: Record<string, string> = {
  HoReCa: 'HoReCa (кофейни, рестораны, отели)',
  Retail: 'Розничные сети',
  FMCG: 'FMCG / Дистрибуция',
  Other: 'Другое',
};

const ROLE_LABELS: Record<string, string> = {
  Manager: 'Менеджер / Руководитель',
  'L&D': 'L&D / HR',
  Owner: 'Владелец',
  Other: 'Другое',
};

type Step = 'form' | 'done';

export default function DemoPage() {
  const [step, setStep] = useState<Step>('form');
  const [magicLink, setMagicLink] = useState('');
  const [showOnScreen, setShowOnScreen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    company: '',
    role: '',
    industry: '',
  });

  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.role || !form.industry) {
      setError('Выберите роль и отрасль');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/demo/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Ошибка регистрации');
      }
      const data = await res.json();
      setMagicLink(data.magic_link);
      setShowOnScreen(data.show_on_screen);
      setStep('done');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Что-то пошло не так');
    } finally {
      setLoading(false);
    }
  }

  if (step === 'done') {
    return (
      <div style={styles.page}>
        <div style={styles.card}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>✅</div>
          <h1 style={styles.heading}>Готово! Доступ создан</h1>
          {showOnScreen ? (
            <>
              <p style={styles.subtext}>
                Используйте ссылку ниже для входа в демо. Сохраните её — она действительна 24 часа.
              </p>
              <div style={styles.linkBox}>
                <a href={magicLink} style={styles.link}>{magicLink}</a>
              </div>
              <button
                style={styles.btn}
                onClick={() => window.location.href = magicLink}
              >
                Войти сейчас →
              </button>
            </>
          ) : (
            <p style={styles.subtext}>
              Ссылка для входа отправлена на {form.email}. Проверьте почту.
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      {/* Hero */}
      <div style={styles.hero}>
        <div style={styles.badge}>Демо-доступ · Бесплатно</div>
        <h1 style={styles.heroTitle}>Попробуйте VYUD LMS за 2 минуты</h1>
        <p style={styles.heroSub}>
          Граф знаний, AI-объяснения и SM-2 повторения — прямо в браузере.
          Без установки. Без карты.
        </p>
        <div style={styles.featureGrid}>
          {[
            { icon: '🧠', text: 'Граф знаний по вашей отрасли' },
            { icon: '🤖', text: 'AI объясняет каждый шаг' },
            { icon: '🔁', text: 'SM-2 интервальные повторения' },
            { icon: '📊', text: 'Прогресс и аналитика' },
          ].map(({ icon, text }) => (
            <div key={text} style={styles.feature}>
              <span style={{ fontSize: 24 }}>{icon}</span>
              <span style={{ fontSize: 13, color: '#334155' }}>{text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Form */}
      <div style={styles.card}>
        <h2 style={styles.formTitle}>Создать демо-доступ</h2>
        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label style={styles.label}>Имя и фамилия *</label>
            <input
              style={styles.input}
              value={form.full_name}
              onChange={e => set('full_name', e.target.value)}
              placeholder="Иван Петров"
              required
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Рабочий email *</label>
            <input
              style={styles.input}
              type="email"
              value={form.email}
              onChange={e => set('email', e.target.value)}
              placeholder="ivan@company.ru"
              required
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Компания *</label>
            <input
              style={styles.input}
              value={form.company}
              onChange={e => set('company', e.target.value)}
              placeholder="ООО Ромашка"
              required
            />
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Ваша роль *</label>
            <div style={styles.radioGroup}>
              {ROLES.map(r => (
                <label key={r} style={{ ...styles.radioLabel, ...(form.role === r ? styles.radioSelected : {}) }}>
                  <input
                    type="radio"
                    name="role"
                    value={r}
                    checked={form.role === r}
                    onChange={() => set('role', r)}
                    style={{ display: 'none' }}
                  />
                  {ROLE_LABELS[r]}
                </label>
              ))}
            </div>
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Отрасль *</label>
            <div style={styles.radioGroup}>
              {INDUSTRIES.map(i => (
                <label key={i} style={{ ...styles.radioLabel, ...(form.industry === i ? styles.radioSelected : {}) }}>
                  <input
                    type="radio"
                    name="industry"
                    value={i}
                    checked={form.industry === i}
                    onChange={() => set('industry', i)}
                    style={{ display: 'none' }}
                  />
                  {INDUSTRY_LABELS[i]}
                </label>
              ))}
            </div>
          </div>

          {error && <p style={styles.error}>{error}</p>}

          <button type="submit" style={styles.btn} disabled={loading}>
            {loading ? 'Создаём доступ...' : 'Получить доступ →'}
          </button>

          <p style={styles.disclaimer}>
            Демо-период 14 дней. Данные не сохраняются после истечения.
            Никакого спама — только ваша ссылка для входа.
          </p>
        </form>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#f8fafc',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '40px 16px 60px',
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  hero: {
    maxWidth: 600,
    width: '100%',
    textAlign: 'center',
    marginBottom: 32,
  },
  badge: {
    display: 'inline-block',
    background: '#eff6ff',
    color: '#2563eb',
    fontSize: 12,
    fontWeight: 600,
    padding: '4px 12px',
    borderRadius: 20,
    marginBottom: 16,
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
  },
  heroTitle: {
    fontSize: 32,
    fontWeight: 800,
    color: '#0f172a',
    margin: '0 0 12px',
    lineHeight: 1.2,
  },
  heroSub: {
    fontSize: 16,
    color: '#475569',
    margin: '0 0 24px',
    lineHeight: 1.6,
  },
  featureGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 12,
    textAlign: 'left',
  },
  feature: {
    background: 'white',
    border: '1px solid #e2e8f0',
    borderRadius: 10,
    padding: '12px 16px',
    display: 'flex',
    gap: 10,
    alignItems: 'center',
  },
  card: {
    background: 'white',
    borderRadius: 16,
    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.07)',
    padding: '32px 28px',
    width: '100%',
    maxWidth: 520,
  },
  formTitle: {
    fontSize: 20,
    fontWeight: 700,
    color: '#0f172a',
    margin: '0 0 24px',
  },
  form: { display: 'flex', flexDirection: 'column', gap: 20 },
  field: { display: 'flex', flexDirection: 'column', gap: 6 },
  label: { fontSize: 13, fontWeight: 600, color: '#374151' },
  input: {
    border: '1px solid #d1d5db',
    borderRadius: 8,
    padding: '10px 12px',
    fontSize: 14,
    outline: 'none',
    color: '#111827',
  },
  radioGroup: { display: 'flex', flexDirection: 'column', gap: 8 },
  radioLabel: {
    border: '1px solid #e2e8f0',
    borderRadius: 8,
    padding: '10px 14px',
    fontSize: 13,
    color: '#374151',
    cursor: 'pointer',
    userSelect: 'none',
    transition: 'all 0.15s',
  },
  radioSelected: {
    border: '1.5px solid #4f46e5',
    background: '#eef2ff',
    color: '#4338ca',
    fontWeight: 600,
  },
  btn: {
    background: '#4f46e5',
    color: 'white',
    border: 'none',
    borderRadius: 8,
    padding: '13px 20px',
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
    width: '100%',
  },
  error: { color: '#dc2626', fontSize: 13, margin: 0 },
  disclaimer: { fontSize: 11, color: '#9ca3af', textAlign: 'center', margin: 0 },
  heading: { fontSize: 22, fontWeight: 700, color: '#0f172a', margin: '0 0 12px' },
  subtext: { fontSize: 14, color: '#475569', margin: '0 0 20px', lineHeight: 1.6 },
  linkBox: {
    background: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
    padding: '12px 16px',
    marginBottom: 20,
    wordBreak: 'break-all',
  },
  link: { color: '#4f46e5', fontSize: 13, textDecoration: 'none' },
};

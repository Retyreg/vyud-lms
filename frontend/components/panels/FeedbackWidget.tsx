'use client';

import { useState } from 'react';
import { submitFeedback } from '@/lib/api';

interface Props {
  userKey?: string;
}

const FEATURE_IDEAS = [
  'Мобильное приложение',
  'Интеграция с Telegram',
  'Тесты и квизы',
  'Видео-уроки',
  'Сертификаты',
  'Групповые чаты',
  'Уведомления о повторении',
  'Экспорт прогресса в PDF',
];

export function FeedbackWidget({ userKey }: Props) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<'form' | 'done'>('form');
  const [rating, setRating] = useState<number | null>(null);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const [liked, setLiked] = useState('');
  const [missing, setMissing] = useState('');
  const [feature, setFeature] = useState('');
  const [selectedFeature, setSelectedFeature] = useState<string | null>(null);
  const [contact, setContact] = useState('');
  const [sending, setSending] = useState(false);

  function reset() {
    setStep('form');
    setRating(null);
    setHoverRating(null);
    setLiked('');
    setMissing('');
    setFeature('');
    setSelectedFeature(null);
    setContact('');
  }

  function handleFeatureChip(f: string) {
    setSelectedFeature(f === selectedFeature ? null : f);
    setFeature(f === selectedFeature ? '' : f);
  }

  async function handleSubmit() {
    if (!rating) return;
    setSending(true);
    try {
      await submitFeedback({
        user_key: userKey,
        rating,
        liked: liked.trim() || undefined,
        missing: missing.trim() || undefined,
        feature: (feature.trim() || selectedFeature) ?? undefined,
        contact: contact.trim() || undefined,
        page: typeof window !== 'undefined' ? window.location.pathname : undefined,
      });
      setStep('done');
    } catch {
      // best-effort
      setStep('done');
    } finally {
      setSending(false);
    }
  }

  const STARS = [1, 2, 3, 4, 5];
  const displayed = hoverRating ?? rating;

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => { setOpen(true); reset(); }}
        title="Оставить отзыв"
        style={{
          position: 'fixed', bottom: 24, left: 24, zIndex: 250,
          width: 48, height: 48, borderRadius: '50%',
          background: '#3b82f6', border: 'none', cursor: 'pointer',
          boxShadow: '0 4px 14px rgba(59,130,246,0.45)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20, color: 'white',
          transition: 'transform 0.15s ease',
        }}
        onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.1)')}
        onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
      >
        💬
      </button>

      {/* Modal */}
      {open && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
          display: 'flex', alignItems: 'flex-end', justifyContent: 'flex-start',
          zIndex: 400, padding: 24,
        }}>
          <div style={{
            background: 'white', borderRadius: 16, padding: 24,
            width: '100%', maxWidth: 420,
            boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
          }}>

            {step === 'done' ? (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>🙏</div>
                <h3 style={{ margin: '0 0 8px', color: '#1e293b' }}>Спасибо за отзыв!</h3>
                <p style={{ color: '#64748b', fontSize: 14, margin: '0 0 20px' }}>
                  Ваше мнение помогает нам стать лучше.
                </p>
                <button onClick={() => setOpen(false)} style={btnBlue}>Закрыть</button>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <h3 style={{ margin: 0, fontSize: 16, color: '#1e293b' }}>💬 Ваш отзыв</h3>
                  <button onClick={() => setOpen(false)} style={btnClose}>✕</button>
                </div>

                {/* Stars */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>
                    Оцените продукт <span style={{ color: '#ef4444' }}>*</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {STARS.map(s => (
                      <button
                        key={s}
                        onClick={() => setRating(s)}
                        onMouseEnter={() => setHoverRating(s)}
                        onMouseLeave={() => setHoverRating(null)}
                        style={{
                          fontSize: 28, background: 'none', border: 'none',
                          cursor: 'pointer', padding: '2px 4px',
                          filter: displayed && s <= displayed ? 'none' : 'grayscale(1) opacity(0.3)',
                          transition: 'filter 0.1s, transform 0.1s',
                          transform: displayed && s <= displayed ? 'scale(1.1)' : 'scale(1)',
                        }}
                      >⭐</button>
                    ))}
                  </div>
                  {rating && (
                    <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                      {['', 'Очень плохо', 'Плохо', 'Нормально', 'Хорошо', 'Отлично!'][rating]}
                    </div>
                  )}
                </div>

                {/* Liked */}
                <Field label="Что понравилось?">
                  <textarea
                    value={liked}
                    onChange={e => setLiked(e.target.value)}
                    placeholder="Удобный граф, AI-объяснения, быстрая генерация..."
                    rows={2}
                    style={textareaStyle}
                  />
                </Field>

                {/* Missing */}
                <Field label="Чего не хватает?">
                  <textarea
                    value={missing}
                    onChange={e => setMissing(e.target.value)}
                    placeholder="Мобильное приложение, уведомления, ..."
                    rows={2}
                    style={textareaStyle}
                  />
                </Field>

                {/* Feature request */}
                <Field label="Какой функционал хотели бы добавить?">
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                    {FEATURE_IDEAS.map(f => (
                      <button
                        key={f}
                        onClick={() => handleFeatureChip(f)}
                        style={{
                          padding: '4px 10px', borderRadius: 20, fontSize: 12,
                          background: selectedFeature === f ? '#3b82f6' : '#f1f5f9',
                          color: selectedFeature === f ? 'white' : '#475569',
                          border: selectedFeature === f ? '1px solid #3b82f6' : '1px solid #e2e8f0',
                          cursor: 'pointer',
                        }}
                      >{f}</button>
                    ))}
                  </div>
                  <input
                    value={feature}
                    onChange={e => { setFeature(e.target.value); setSelectedFeature(null); }}
                    placeholder="Или напишите свою идею..."
                    style={inputStyle}
                  />
                </Field>

                {/* Contact */}
                <Field label="Контакт для связи (необязательно)">
                  <input
                    value={contact}
                    onChange={e => setContact(e.target.value)}
                    placeholder="email или @telegram"
                    style={inputStyle}
                  />
                </Field>

                <button
                  onClick={handleSubmit}
                  disabled={!rating || sending}
                  style={{
                    ...btnBlue,
                    width: '100%',
                    opacity: !rating ? 0.5 : 1,
                    cursor: !rating ? 'not-allowed' : 'pointer',
                  }}
                >
                  {sending ? '⏳ Отправляем...' : '📨 Отправить отзыв'}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 5, fontWeight: 600 }}>{label}</div>
      {children}
    </div>
  );
}

const textareaStyle: React.CSSProperties = {
  width: '100%', padding: '8px 10px', fontSize: 13,
  border: '1px solid #e2e8f0', borderRadius: 8, outline: 'none',
  color: '#1e293b', resize: 'none', boxSizing: 'border-box',
  fontFamily: 'inherit',
};

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 10px', fontSize: 13,
  border: '1px solid #e2e8f0', borderRadius: 8, outline: 'none',
  color: '#1e293b', boxSizing: 'border-box',
};

const btnBlue: React.CSSProperties = {
  padding: '10px 20px', background: '#3b82f6', border: 'none',
  borderRadius: 8, cursor: 'pointer', fontSize: 14, color: 'white',
  fontWeight: 600,
};

const btnClose: React.CSSProperties = {
  background: 'none', border: 'none', cursor: 'pointer',
  fontSize: 18, color: '#94a3b8', lineHeight: 1,
};

'use client';

import { useState } from 'react';
import { API_BASE_URL } from '@/lib/api';
import { demoHeaders, type DemoSession } from '@/lib/demo';

interface Props {
  session: DemoSession;
  onClose: () => void;
  /** When true, shows "Вы изучили всё — что думаете?" heading */
  afterCompletion?: boolean;
}

export function DemoFeedbackModal({ session, onClose, afterCompletion }: Props) {
  const [rating, setRating] = useState(0);
  const [message, setMessage] = useState('');
  const [wantsPilot, setWantsPilot] = useState(false);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit() {
    if (!rating) { setError('Поставьте оценку'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/demo/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...demoHeaders(session) },
        body: JSON.stringify({ rating, message: message || null, wants_pilot: wantsPilot }),
      });
      if (!res.ok) throw new Error('Ошибка отправки');
      setDone(true);
    } catch {
      setError('Не удалось отправить. Попробуйте ещё раз.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={overlayStyle} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={modalStyle}>
        <button style={closeBtn} onClick={onClose}>×</button>

        {done ? (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🙏</div>
            <h3 style={titleStyle}>Спасибо за отзыв!</h3>
            {wantsPilot && (
              <p style={{ color: '#475569', fontSize: 13, marginTop: 8 }}>
                Мы свяжемся с вами для обсуждения пилота.
              </p>
            )}
            <button style={primaryBtn} onClick={onClose}>Закрыть</button>
          </div>
        ) : (
          <>
            <h3 style={titleStyle}>
              {afterCompletion ? 'Вы изучили всё — что думаете?' : '💬 Оставить отзыв'}
            </h3>
            <p style={subStyle}>Помогите улучшить VYUD LMS</p>

            <div style={starRow}>
              {[1, 2, 3, 4, 5].map(n => (
                <button
                  key={n}
                  style={{ ...starBtn, color: n <= rating ? '#F59E0B' : '#D1D5DB' }}
                  onClick={() => setRating(n)}
                >
                  ★
                </button>
              ))}
            </div>
            {rating > 0 && (
              <p style={{ fontSize: 11, color: '#6B7280', textAlign: 'center', margin: '-8px 0 8px' }}>
                {['', 'Не понравилось', 'Слабо', 'Неплохо', 'Хорошо', 'Отлично!'][rating]}
              </p>
            )}

            <textarea
              style={textareaStyle}
              placeholder="Что понравилось? Чего не хватает?"
              value={message}
              onChange={e => setMessage(e.target.value)}
              rows={3}
            />

            <label style={checkboxLabel}>
              <input
                type="checkbox"
                checked={wantsPilot}
                onChange={e => setWantsPilot(e.target.checked)}
                style={{ marginRight: 8 }}
              />
              Хочу обсудить пилот для своей компании
            </label>

            {error && <p style={{ color: '#DC2626', fontSize: 12, margin: 0 }}>{error}</p>}

            <button style={primaryBtn} onClick={handleSubmit} disabled={loading}>
              {loading ? 'Отправляем...' : 'Отправить отзыв'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.45)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 2000,
  padding: 16,
};

const modalStyle: React.CSSProperties = {
  background: 'white',
  borderRadius: 16,
  padding: '28px 24px',
  width: '100%',
  maxWidth: 400,
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
  fontFamily: 'Inter, system-ui, sans-serif',
};

const closeBtn: React.CSSProperties = {
  position: 'absolute',
  top: 12,
  right: 14,
  background: 'none',
  border: 'none',
  fontSize: 22,
  color: '#9CA3AF',
  cursor: 'pointer',
  lineHeight: 1,
};

const titleStyle: React.CSSProperties = {
  fontSize: 17,
  fontWeight: 700,
  color: '#0F172A',
  margin: 0,
};

const subStyle: React.CSSProperties = {
  fontSize: 13,
  color: '#6B7280',
  margin: 0,
};

const starRow: React.CSSProperties = {
  display: 'flex',
  gap: 4,
  justifyContent: 'center',
};

const starBtn: React.CSSProperties = {
  background: 'none',
  border: 'none',
  fontSize: 36,
  cursor: 'pointer',
  padding: 0,
  lineHeight: 1,
  transition: 'color 0.1s',
};

const textareaStyle: React.CSSProperties = {
  border: '1px solid #E5E7EB',
  borderRadius: 8,
  padding: '10px 12px',
  fontSize: 13,
  resize: 'vertical',
  fontFamily: 'inherit',
  color: '#111827',
};

const checkboxLabel: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  fontSize: 13,
  color: '#374151',
  cursor: 'pointer',
};

const primaryBtn: React.CSSProperties = {
  background: '#4F46E5',
  color: 'white',
  border: 'none',
  borderRadius: 8,
  padding: '11px 16px',
  fontSize: 14,
  fontWeight: 700,
  cursor: 'pointer',
  width: '100%',
};

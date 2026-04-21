'use client';

import { useState, useEffect } from 'react';
import { getDemoSession, type DemoSession } from '@/lib/demo';

interface Props {
  onFeedbackClick: () => void;
}

export function DemoBanner({ onFeedbackClick }: Props) {
  const [session, setSession] = useState<DemoSession | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setSession(getDemoSession());
  }, []);

  if (!session || dismissed) return null;

  const expiresAt = new Date(session.expires_at);
  const now = new Date();
  const hoursLeft = Math.max(0, Math.round((expiresAt.getTime() - now.getTime()) / 3_600_000));

  return (
    <div style={bannerStyle}>
      <div style={contentStyle}>
        <span style={iconStyle}>🔔</span>
        <span style={textStyle}>
          <strong>Демо-режим.</strong>{' '}
          {hoursLeft > 0
            ? `Сессия истекает через ${hoursLeft} ч.`
            : 'Сессия скоро истечёт.'}{' '}
          Создание, экспорт и приглашение команды доступны в пилоте.
        </span>
      </div>
      <div style={actionsStyle}>
        <button style={feedbackBtnStyle} onClick={onFeedbackClick}>
          💬 Оставить отзыв
        </button>
        <button
          style={dismissBtnStyle}
          onClick={() => setDismissed(true)}
          aria-label="Скрыть баннер"
        >
          ×
        </button>
      </div>
    </div>
  );
}

const bannerStyle: React.CSSProperties = {
  position: 'sticky',
  top: 0,
  zIndex: 1000,
  background: '#FEF3C7',
  borderBottom: '1px solid #F59E0B',
  padding: '10px 16px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 12,
  flexWrap: 'wrap',
};

const contentStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  flex: 1,
  minWidth: 0,
};

const iconStyle: React.CSSProperties = { fontSize: 16, flexShrink: 0 };

const textStyle: React.CSSProperties = {
  fontSize: 13,
  color: '#92400E',
  lineHeight: 1.4,
};

const actionsStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  flexShrink: 0,
};

const feedbackBtnStyle: React.CSSProperties = {
  background: '#F59E0B',
  color: 'white',
  border: 'none',
  borderRadius: 6,
  padding: '6px 12px',
  fontSize: 12,
  fontWeight: 600,
  cursor: 'pointer',
};

const dismissBtnStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  color: '#92400E',
  fontSize: 20,
  lineHeight: 1,
  cursor: 'pointer',
  padding: '0 4px',
};

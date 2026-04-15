'use client';

import { useState } from 'react';

interface Props {
  onClose: () => void;
  onStartWizard: () => void;
}

const SLIDES = [
  {
    emoji: '🎓',
    title: 'Добро пожаловать в VYUD LMS',
    body: 'Это AI-система для обучения команды. За 30 секунд создаёт персональную карту знаний по любой теме — и помогает каждому сотруднику освоить её в своём темпе.',
    visual: (
      <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
        {['Python', 'Продажи', 'Ваш PDF'].map((t, i) => (
          <div key={i} style={{
            padding: '6px 12px', background: '#eff6ff', border: '1px solid #bfdbfe',
            borderRadius: 20, fontSize: 12, color: '#2563eb', fontWeight: 500,
          }}>{t}</div>
        ))}
      </div>
    ),
  },
  {
    emoji: '🚀',
    title: 'Как начать за 3 шага',
    body: null,
    visual: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
        {[
          { n: '1', icon: '🏢', text: 'Нажмите «Создать организацию» — введите название и email' },
          { n: '2', icon: '📝', text: 'Введите тему курса (или загрузите PDF) и нажмите «Создать»' },
          { n: '3', icon: '🔗', text: 'Скопируйте инвайт-ссылку и отправьте сотрудникам' },
        ].map(({ n, icon, text }) => (
          <div key={n} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%', background: '#3b82f6',
              color: 'white', fontWeight: 700, fontSize: 14,
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>{n}</div>
            <div style={{ fontSize: 13, color: '#334155', lineHeight: 1.5 }}>
              <span style={{ marginRight: 4 }}>{icon}</span>{text}
            </div>
          </div>
        ))}
      </div>
    ),
  },
  {
    emoji: '🧠',
    title: 'Как работает граф знаний',
    body: null,
    visual: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
        {[
          { color: '#3b82f6', border: '2px solid #3b82f6', label: 'Синяя рамка', desc: '— тема доступна. Нажмите, чтобы получить AI-объяснение' },
          { color: '#f3f4f6', border: '2px dashed #ccc', label: 'Серая пунктирная', desc: '— заблокирована. Сначала пройдите предыдущие темы' },
          { color: '#4ADE80', border: '2px solid #16a34a', label: 'Зелёная', desc: '— тема освоена. Система вернёт её на повторение в нужный момент' },
          { color: 'white', border: '2px solid #f59e0b', label: 'Жёлтая рамка', desc: '— пора повторить сегодня (интервальное повторение)' },
        ].map(({ color, border, label, desc }, i) => (
          <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div style={{ width: 36, height: 22, borderRadius: 6, background: color, border, flexShrink: 0 }} />
            <div style={{ fontSize: 12, color: '#475569', lineHeight: 1.4 }}>
              <strong>{label}</strong> {desc}
            </div>
          </div>
        ))}
      </div>
    ),
  },
  {
    emoji: '📊',
    title: 'Для руководителя',
    body: null,
    visual: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
        {[
          { icon: '📊', title: 'Дашборд', desc: 'Прогресс каждого сотрудника, лидерборд, недельная активность' },
          { icon: '📋', title: 'СОП', desc: 'Загрузите регламенты PDF — система создаст тест с квизом' },
          { icon: '🎨', title: 'Брендинг', desc: 'Свои цвета, логотип и название в Telegram Mini App' },
          { icon: '🔥', title: 'Стрики', desc: 'Геймификация: серии дней, достижения, лидерборд мотивируют команду' },
        ].map(({ icon, title, desc }) => (
          <div key={title} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <span style={{ fontSize: 18, flexShrink: 0 }}>{icon}</span>
            <div style={{ fontSize: 12, color: '#475569', lineHeight: 1.4 }}>
              <strong style={{ color: '#1e293b' }}>{title}</strong> — {desc}
            </div>
          </div>
        ))}
      </div>
    ),
  },
];

export function WelcomeTourModal({ onClose, onStartWizard }: Props) {
  const [slide, setSlide] = useState(0);
  const isLast = slide === SLIDES.length - 1;
  const s = SLIDES[slide];

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 400, padding: 16,
    }}>
      <div style={{
        background: 'white', borderRadius: 20, padding: 28,
        width: '100%', maxWidth: 460,
        boxShadow: '0 12px 40px rgba(0,0,0,0.25)',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* Dot nav */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginBottom: 20 }}>
          {SLIDES.map((_, i) => (
            <div
              key={i}
              onClick={() => setSlide(i)}
              style={{
                width: i === slide ? 20 : 8, height: 8, borderRadius: 4,
                background: i === slide ? '#3b82f6' : '#e2e8f0',
                cursor: 'pointer', transition: 'all 0.25s ease',
              }}
            />
          ))}
        </div>

        {/* Emoji + title */}
        <div style={{ textAlign: 'center', marginBottom: 8 }}>
          <div style={{ fontSize: 40, marginBottom: 8 }}>{s.emoji}</div>
          <h2 style={{ margin: 0, fontSize: 18, color: '#1e293b', fontWeight: 700 }}>{s.title}</h2>
          {s.body && (
            <p style={{ fontSize: 14, color: '#475569', marginTop: 10, lineHeight: 1.6 }}>{s.body}</p>
          )}
        </div>

        {/* Visual */}
        <div style={{ minHeight: 120 }}>{s.visual}</div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: 10, marginTop: 24, justifyContent: 'space-between' }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px', background: 'none', border: '1px solid #e2e8f0',
              borderRadius: 8, cursor: 'pointer', fontSize: 13, color: '#94a3b8',
            }}
          >
            Пропустить
          </button>

          <div style={{ display: 'flex', gap: 8 }}>
            {slide > 0 && (
              <button
                onClick={() => setSlide(s => s - 1)}
                style={{
                  padding: '8px 16px', background: '#f8fafc', border: '1px solid #e2e8f0',
                  borderRadius: 8, cursor: 'pointer', fontSize: 13, color: '#475569',
                }}
              >
                ← Назад
              </button>
            )}
            {isLast ? (
              <button
                onClick={() => { onClose(); onStartWizard(); }}
                style={{
                  padding: '8px 20px', background: '#3b82f6', border: 'none',
                  borderRadius: 8, cursor: 'pointer', fontSize: 13, color: 'white', fontWeight: 600,
                }}
              >
                🚀 Начать →
              </button>
            ) : (
              <button
                onClick={() => setSlide(s => s + 1)}
                style={{
                  padding: '8px 20px', background: '#3b82f6', border: 'none',
                  borderRadius: 8, cursor: 'pointer', fontSize: 13, color: 'white', fontWeight: 600,
                }}
              >
                Далее →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

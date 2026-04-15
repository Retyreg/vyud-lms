'use client';

import { useState } from 'react';
import { fetchNodeAsk } from '@/lib/api';

interface Props {
  topic: string;
  explanation: string | null;
  isLoading: boolean;
  isCached: boolean;
  nodeId: number | null;
  userKey: string;
  masteryPct?: number;
  nextReview?: string | null;
  onClose: () => void;
  onReview: (quality: 0 | 1 | 2 | 3) => void;
  onRegenerate: () => void;
}

const REVIEW_BUTTONS = [
  { quality: 0, label: '😕 Не помню', bg: '#fef2f2', color: '#b91c1c' },
  { quality: 1, label: '🤔 С трудом',  bg: '#fffbeb', color: '#b45309' },
  { quality: 2, label: '🙂 Помню',     bg: '#f0fdf4', color: '#15803d' },
  { quality: 3, label: '😊 Легко',     bg: '#eff6ff', color: '#1d4ed8' },
] as const;

const INDUSTRIES = [
  { id: 'IT',           label: '💻 IT' },
  { id: 'Продажи',      label: '📈 Продажи' },
  { id: 'HR',           label: '👥 HR' },
  { id: 'Финансы',      label: '💰 Финансы' },
  { id: 'Маркетинг',    label: '📣 Маркетинг' },
  { id: 'Медицина',     label: '🏥 Медицина' },
  { id: 'Производство', label: '🏭 Производство' },
  { id: 'Образование',  label: '🎓 Образование' },
];

function masteryColor(pct: number): string {
  if (pct === 0) return '#94a3b8';
  if (pct < 40)  return '#f59e0b';
  if (pct < 70)  return '#f97316';
  if (pct < 100) return '#22c55e';
  return '#16a34a';
}

function formatNextReview(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.ceil((d.getTime() - now.getTime()) / 86400000);
  if (diffDays <= 0) return 'сегодня';
  if (diffDays === 1) return 'завтра';
  return `через ${diffDays} дн.`;
}

/**
 * Parse structured explanation into blocks.
 * Expected format: "📌 Суть: ...\n💼 Кейс: ...\n🎯 Почему важно: ..."
 * Falls back to plain text if format not detected.
 */
function parseExplanation(text: string): { icon: string; label: string; body: string }[] | null {
  const patterns = [
    { icon: '📌', label: 'Суть', prefix: /📌\s*Суть\s*:?\s*/i },
    { icon: '💼', label: 'Кейс', prefix: /💼\s*Кейс\s*:?\s*/i },
    { icon: '🎯', label: 'Почему важно', prefix: /🎯\s*Почему важно\s*:?\s*/i },
  ];

  const hasStructure = patterns.some(p => p.prefix.test(text));
  if (!hasStructure) return null;

  const blocks: { icon: string; label: string; body: string }[] = [];
  for (let i = 0; i < patterns.length; i++) {
    const { icon, label, prefix } = patterns[i];
    const start = text.search(prefix);
    if (start === -1) continue;
    const bodyStart = start + text.slice(start).match(prefix)![0].length;
    const nextStart = i < patterns.length - 1
      ? text.search(patterns[i + 1].prefix)
      : -1;
    const body = (nextStart > bodyStart ? text.slice(bodyStart, nextStart) : text.slice(bodyStart)).trim();
    if (body) blocks.push({ icon, label, body });
  }
  return blocks.length >= 2 ? blocks : null;
}

export function ExplanationPanel({
  topic,
  explanation,
  isLoading,
  isCached,
  nodeId,
  masteryPct = 0,
  nextReview,
  onClose,
  onReview,
  onRegenerate,
}: Props) {
  const nextReviewLabel = formatNextReview(nextReview);

  // Follow-up ask state
  const [selectedIndustry, setSelectedIndustry] = useState<string | null>(null);
  const [customQuestion, setCustomQuestion] = useState('');
  const [askAnswer, setAskAnswer] = useState<string | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const [showAsk, setShowAsk] = useState(false);

  async function handleAsk(question: string, industry?: string) {
    if (!nodeId || !question.trim()) return;
    setIsAsking(true);
    setAskAnswer(null);
    try {
      const { answer } = await fetchNodeAsk(nodeId, question, industry);
      setAskAnswer(answer);
    } catch {
      setAskAnswer('Ошибка — попробуйте ещё раз.');
    } finally {
      setIsAsking(false);
    }
  }

  function handleIndustryClick(id: string) {
    setSelectedIndustry(id);
    setAskAnswer(null);
    handleAsk(`Как «${topic.replace(' ✅', '').split('\n')[0]}» применяется в моей работе?`, id);
  }

  const blocks = explanation ? parseExplanation(explanation) : null;

  return (
    <div style={{
      position: 'absolute', top: 80, right: 20, width: 370,
      background: 'white', padding: 20, borderRadius: 12,
      boxShadow: '0 4px 20px rgba(0,0,0,0.15)', zIndex: 100,
      maxHeight: 'calc(100vh - 110px)', overflowY: 'auto',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <h3 style={{ margin: 0, fontSize: 16, color: '#1e293b', paddingRight: 8 }}>
          {topic.replace(' ✅', '').split('\n')[0]}
        </h3>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: '#94a3b8', lineHeight: 1, flexShrink: 0 }}
        >✕</button>
      </div>

      {/* Mastery bar */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: '#64748b' }}>Мастерство</span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {nextReviewLabel && (
              <span style={{ fontSize: 11, color: '#94a3b8' }}>повтор: {nextReviewLabel}</span>
            )}
            <span style={{ fontSize: 12, fontWeight: 600, color: masteryColor(masteryPct) }}>
              {masteryPct}%
            </span>
          </div>
        </div>
        <div style={{ height: 6, background: '#f1f5f9', borderRadius: 3 }}>
          <div style={{
            height: '100%', borderRadius: 3,
            width: `${masteryPct}%`,
            background: masteryColor(masteryPct),
            transition: 'width 0.4s ease',
          }} />
        </div>
      </div>

      {isLoading ? (
        <p style={{ color: '#64748b', fontSize: 14 }}>🤖 Думаю...</p>
      ) : (
        <>
          {/* Explanation — structured or plain */}
          {blocks ? (
            <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
              {blocks.map(({ icon, label, body }) => (
                <div key={label} style={{
                  background: label === 'Кейс' ? '#f0fdf4' : label === 'Суть' ? '#eff6ff' : '#fafafa',
                  borderRadius: 8, padding: '10px 12px',
                  borderLeft: `3px solid ${label === 'Кейс' ? '#22c55e' : label === 'Суть' ? '#3b82f6' : '#e2e8f0'}`,
                }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>
                    {icon} {label}
                  </div>
                  <div style={{ fontSize: 13, color: '#334155', lineHeight: 1.6 }}>{body}</div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: 14, lineHeight: 1.6, color: '#334155', margin: '0 0 16px' }}>
              {explanation}
            </p>
          )}

          {isCached && (
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 10 }}>из кэша</div>
          )}

          {/* Review */}
          <div style={{ marginBottom: 8, fontSize: 12, color: '#64748b' }}>Как усвоил?</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 10 }}>
            {REVIEW_BUTTONS.map(({ quality, label, bg, color }) => (
              <button
                key={quality}
                onClick={() => onReview(quality)}
                style={{
                  padding: '8px 4px', background: bg, color,
                  border: `1px solid ${color}33`, borderRadius: 8,
                  cursor: 'pointer', fontSize: 13, fontWeight: 500,
                }}
              >
                {label}
              </button>
            ))}
          </div>

          <button
            onClick={onRegenerate}
            style={{
              width: '100%', padding: '7px 0', background: '#f1f5f9',
              color: '#475569', border: 'none', borderRadius: 8,
              cursor: 'pointer', fontSize: 13, marginBottom: 14,
            }}
          >
            Иначе ↺
          </button>

          {/* Follow-up: apply to industry */}
          <div style={{
            borderTop: '1px solid #f1f5f9', paddingTop: 14,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#64748b' }}>
                🏢 Применить к своей сфере
              </div>
              <button
                onClick={() => { setShowAsk(v => !v); setAskAnswer(null); setSelectedIndustry(null); }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, color: '#94a3b8' }}
              >
                {showAsk ? '▲ скрыть' : '▼ показать'}
              </button>
            </div>

            {/* Industry chips — always visible */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
              {INDUSTRIES.map(({ id, label }) => (
                <button
                  key={id}
                  onClick={() => handleIndustryClick(id)}
                  disabled={isAsking}
                  style={{
                    padding: '4px 10px', borderRadius: 20, fontSize: 12,
                    background: selectedIndustry === id ? '#3b82f6' : '#f1f5f9',
                    color: selectedIndustry === id ? 'white' : '#475569',
                    border: selectedIndustry === id ? '1px solid #3b82f6' : '1px solid #e2e8f0',
                    cursor: isAsking ? 'not-allowed' : 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Custom question */}
            {showAsk && (
              <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
                <input
                  value={customQuestion}
                  onChange={e => setCustomQuestion(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && customQuestion.trim()) {
                      setSelectedIndustry(null);
                      handleAsk(customQuestion, selectedIndustry ?? undefined);
                    }
                  }}
                  placeholder="Свой вопрос..."
                  style={{
                    flex: 1, padding: '6px 10px', fontSize: 12,
                    border: '1px solid #e2e8f0', borderRadius: 8, outline: 'none',
                    color: '#334155',
                  }}
                />
                <button
                  onClick={() => {
                    if (customQuestion.trim()) {
                      setSelectedIndustry(null);
                      handleAsk(customQuestion, selectedIndustry ?? undefined);
                    }
                  }}
                  disabled={isAsking || !customQuestion.trim()}
                  style={{
                    padding: '6px 12px', background: '#3b82f6', color: 'white',
                    border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 12,
                  }}
                >
                  →
                </button>
              </div>
            )}

            {/* Answer */}
            {isAsking && (
              <div style={{ fontSize: 13, color: '#64748b', padding: '8px 0' }}>🤖 Думаю...</div>
            )}
            {askAnswer && !isAsking && (
              <div style={{
                background: '#fafafa', border: '1px solid #e2e8f0',
                borderRadius: 8, padding: '10px 12px',
                fontSize: 13, color: '#334155', lineHeight: 1.6,
              }}>
                {askAnswer}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

'use client';

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

export function ExplanationPanel({
  topic,
  explanation,
  isLoading,
  isCached,
  masteryPct = 0,
  nextReview,
  onClose,
  onReview,
  onRegenerate,
}: Props) {
  const nextReviewLabel = formatNextReview(nextReview);
  return (
    <div style={{
      position: 'absolute', top: 80, right: 20, width: 350,
      background: 'white', padding: 25, borderRadius: 12,
      boxShadow: '0 4px 20px rgba(0,0,0,0.15)', zIndex: 100,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <h3 style={{ margin: 0, fontSize: 16, color: '#1e293b' }}>{topic.replace(' ✅', '').split('\n')[0]}</h3>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: '#94a3b8', lineHeight: 1 }}
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
          <p style={{ fontSize: 14, lineHeight: 1.6, color: '#334155', margin: '0 0 16px' }}>
            {explanation}
          </p>
          {isCached && (
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 10 }}>из кэша</div>
          )}

          <div style={{ marginBottom: 8, fontSize: 12, color: '#64748b' }}>Как усвоил?</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
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
              width: '100%', padding: '8px 0', background: '#f1f5f9',
              color: '#475569', border: 'none', borderRadius: 8,
              cursor: 'pointer', fontSize: 13,
            }}
          >
            Иначе ↺
          </button>
        </>
      )}
    </div>
  );
}

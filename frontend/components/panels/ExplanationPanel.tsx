'use client';

interface Props {
  topic: string;
  explanation: string | null;
  isLoading: boolean;
  isCached: boolean;
  nodeId: number | null;
  userKey: string;
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

export function ExplanationPanel({
  topic,
  explanation,
  isLoading,
  isCached,
  onClose,
  onReview,
  onRegenerate,
}: Props) {
  return (
    <div style={{
      position: 'absolute', top: 80, right: 20, width: 350,
      background: 'white', padding: 25, borderRadius: 12,
      boxShadow: '0 4px 20px rgba(0,0,0,0.15)', zIndex: 100,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 16, color: '#1e293b' }}>{topic.replace(' ✅', '')}</h3>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: '#94a3b8', lineHeight: 1 }}
        >✕</button>
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

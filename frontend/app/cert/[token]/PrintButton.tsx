'use client';

export function PrintButton() {
  return (
    <button
      onClick={() => window.print()}
      style={{
        padding: '8px 16px', borderRadius: 8, border: '1px solid #E5E7EB',
        background: 'white', color: '#374151', fontSize: 13, fontWeight: 600,
        cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
      }}
    >
      🖨️ Распечатать
    </button>
  );
}

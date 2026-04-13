'use client';

import { useEffect, useRef, useState } from 'react';
import { fetchOrgSops, uploadSopPdf } from '@/lib/api';
import type { SOPListItem } from '@/types';

interface Props {
  orgId: number;
  userKey: string;
  onClose: () => void;
  onSelectSop: (id: number) => void;
  onToast: (msg: string) => void;
}

export function SOPListModal({ orgId, userKey, onClose, onSelectSop, onToast }: Props) {
  const [sops, setSops] = useState<SOPListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const pdfRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchOrgSops(orgId, userKey)
      .then(setSops)
      .catch(() => setSops([]))
      .finally(() => setIsLoading(false));
  }, [orgId, userKey]);

  const handlePdf = async (file: File) => {
    setIsUploading(true);
    try {
      const data = await uploadSopPdf(orgId, file, userKey);
      onToast(`✅ СОП создан! ${data.steps_count} шагов, ${data.quiz_count} вопросов`);
      const updated = await fetchOrgSops(orgId, userKey);
      setSops(updated);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Ошибка загрузки PDF');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200,
    }}>
      <div style={{
        background: 'white', borderRadius: 16, padding: 32,
        width: '100%', maxWidth: 520, maxHeight: '80vh',
        display: 'flex', flexDirection: 'column',
        boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 18, color: '#1e293b' }}>📋 Стандартные процедуры</h2>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20, color: '#94a3b8' }}
          >✕</button>
        </div>

        {/* Upload PDF */}
        <button
          onClick={() => pdfRef.current?.click()}
          disabled={isUploading}
          style={{
            marginBottom: 16, padding: '10px 16px', borderRadius: 8, border: 'none',
            background: isUploading ? '#94a3b8' : '#f59e0b', color: 'white',
            fontWeight: 600, fontSize: 14, cursor: isUploading ? 'not-allowed' : 'pointer',
          }}
        >
          {isUploading ? '⏳ Генерирую СОП...' : '📄 Загрузить PDF → СОП'}
        </button>
        <input
          ref={pdfRef}
          type="file"
          accept=".pdf"
          style={{ display: 'none' }}
          onChange={e => { const f = e.target.files?.[0]; if (f) handlePdf(f); }}
        />

        {/* List */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#64748b', fontSize: 14 }}>
              ⏳ Загрузка...
            </div>
          ) : sops.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#94a3b8', fontSize: 14 }}>
              СОП пока нет. Загрузите PDF, чтобы создать первый.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {sops.map(sop => (
                <div
                  key={sop.id}
                  onClick={() => onSelectSop(sop.id)}
                  style={{
                    padding: '14px 16px', borderRadius: 10, cursor: 'pointer',
                    border: `1px solid ${sop.is_completed ? '#bbf7d0' : '#e2e8f0'}`,
                    background: sop.is_completed ? '#f0fdf4' : '#f8fafc',
                    transition: 'box-shadow 0.15s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)')}
                  onMouseLeave={e => (e.currentTarget.style.boxShadow = 'none')}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14, color: '#1e293b', marginBottom: 4 }}>
                        {sop.title}
                      </div>
                      <div style={{ fontSize: 12, color: '#64748b' }}>
                        {sop.steps_count} шагов
                      </div>
                    </div>
                    <div style={{
                      fontSize: 11, fontWeight: 600, padding: '3px 8px', borderRadius: 999,
                      background: sop.is_completed ? '#dcfce7' : '#f1f5f9',
                      color: sop.is_completed ? '#15803d' : '#64748b',
                      whiteSpace: 'nowrap',
                    }}>
                      {sop.is_completed ? '✅ Пройден' : '→ Открыть'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

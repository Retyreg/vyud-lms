'use client';

import { useRef } from 'react';
import type { BackendStatus, StreakInfo } from '@/types';

interface Props {
  topic: string;
  onTopicChange: (v: string) => void;
  onGenerate: () => void;
  onPdfUpload: (file: File) => void;
  isGenerating: boolean;
  isPdfUploading: boolean;
  backendStatus: BackendStatus;
  streakInfo: StreakInfo | null;
  orgName: string | null;
  onShowDashboard: () => void;
  onShowSops: () => void;
  onShowStreak: () => void;
  onCopyInvite: () => void;
  onCreateOrg: () => void;
  onShowTour: () => void;
}

export function ControlPanel({
  topic,
  onTopicChange,
  onGenerate,
  onPdfUpload,
  isGenerating,
  isPdfUploading,
  backendStatus,
  streakInfo,
  orgName,
  onShowDashboard,
  onShowSops,
  onShowStreak,
  onCopyInvite,
  onCreateOrg,
  onShowTour,
}: Props) {
  const pdfInputRef = useRef<HTMLInputElement>(null);
  const isBlocked = backendStatus === 'loading' || backendStatus === 'warming';

  return (
    <div style={{
      position: 'absolute', top: 20, left: 20, zIndex: 10,
      background: 'white', padding: 20, borderRadius: 12,
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ fontWeight: 600, fontSize: 16, color: '#1e293b' }}>🎓 VYUD LMS</div>
        <button
          onClick={onShowTour}
          title="Как пользоваться?"
          style={{
            width: 22, height: 22, borderRadius: '50%',
            background: '#f1f5f9', border: '1px solid #e2e8f0',
            cursor: 'pointer', fontSize: 12, color: '#64748b',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, flexShrink: 0,
          }}
        >?</button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <input
          value={topic}
          onChange={(e) => onTopicChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onGenerate()}
          placeholder="Тема курса (напр. Python, React...)"
          title="Введите тему — AI построит граф знаний за ~30 сек"
          style={{ padding: 8, border: '1px solid #ddd', borderRadius: 6, width: 200 }}
        />
        <button
          onClick={onGenerate}
          disabled={isGenerating || isBlocked}
          title="Сгенерировать граф знаний по теме с помощью AI"
          style={{
            padding: '8px 16px',
            background: isGenerating || isBlocked ? '#94a3b8' : '#3b82f6',
            color: 'white', border: 'none', borderRadius: 6,
            cursor: isGenerating || isBlocked ? 'not-allowed' : 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          {isGenerating ? 'Генерация...' : 'Создать'}
        </button>
        <button
          onClick={() => pdfInputRef.current?.click()}
          disabled={isPdfUploading}
          title="Загрузить PDF — AI извлечёт темы и создаст граф из документа"
          style={{
            padding: '8px 12px',
            background: isPdfUploading ? '#94a3b8' : '#f59e0b',
            color: 'white', border: 'none', borderRadius: 6,
            cursor: isPdfUploading ? 'not-allowed' : 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          {isPdfUploading ? '⏳ Загружаю...' : '📄 PDF'}
        </button>
      </div>
      <input
        ref={pdfInputRef}
        type="file"
        accept=".pdf"
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onPdfUpload(file);
        }}
      />

      {streakInfo && (
        <button
          onClick={onShowStreak}
          style={{
            marginTop: 10, width: '100%', padding: '8px 12px', textAlign: 'left',
            background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          <div style={{ fontSize: 14, fontWeight: 600, color: '#c2410c' }}>
            {streakInfo.badge
              ? `${streakInfo.badge} · ${streakInfo.current_streak} дней`
              : `🔥 ${streakInfo.current_streak} дней`}
          </div>
          <div style={{ fontSize: 11, color: '#9a3412', marginTop: 2 }}>
            Рекорд: {streakInfo.longest_streak} дн. · Всего: {streakInfo.total_days_active} дн.
          </div>
        </button>
      )}

      {orgName ? (
        <div style={{ marginTop: 10, fontSize: 12, color: '#64748b' }}>
          Org: <strong>{orgName}</strong>
          <button
            onClick={onCopyInvite}
            title="Скопировать ссылку для приглашения сотрудников в организацию"
            style={{
              marginLeft: 8, fontSize: 11, padding: '2px 8px',
              background: '#f1f5f9', border: '1px solid #e2e8f0',
              borderRadius: 4, cursor: 'pointer',
            }}
          >
            Скопировать инвайт
          </button>
          <button
            onClick={onShowDashboard}
            title="Прогресс команды, лидерборд, ROI-метрики"
            style={{
              marginLeft: 6, fontSize: 11, padding: '2px 8px',
              background: '#eff6ff', border: '1px solid #bfdbfe',
              borderRadius: 4, cursor: 'pointer',
            }}
          >
            📊 Дашборд
          </button>
          <button
            onClick={onShowSops}
            title="Стандартные операционные процедуры — загрузите регламент PDF, система создаст тест"
            style={{
              marginLeft: 6, fontSize: 11, padding: '2px 8px',
              background: '#f0fdf4', border: '1px solid #bbf7d0',
              borderRadius: 4, cursor: 'pointer',
            }}
          >
            📋 СОП
          </button>
        </div>
      ) : (
        <button
          onClick={onCreateOrg}
          style={{
            marginTop: 8, width: '100%', padding: '6px 0',
            background: '#f8fafc', border: '1px dashed #cbd5e1',
            borderRadius: 6, cursor: 'pointer', fontSize: 12, color: '#64748b',
          }}
        >
          + Создать организацию
        </button>
      )}
    </div>
  );
}

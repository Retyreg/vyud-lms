'use client';

import { useRef, useState } from 'react';

interface Props {
  step: 1 | 2 | 3;
  inviteCode: string;
  isGenerating: boolean;
  onClose: () => void;
  onCreateOrg: (name: string, email: string) => void;
  onGenerateCourse: (topic: string) => void;
  onUploadPdf: (file: File) => void;
  onFinish: () => void;
  onCopyInvite: () => void;
  /** When set (TMA mode): hides the email field and uses this value as manager key */
  telegramManagerKey?: string;
  /** Display name shown instead of email placeholder in TMA mode */
  telegramDisplayName?: string;
}

export function WizardModal({
  step,
  inviteCode,
  isGenerating,
  onClose,
  onCreateOrg,
  onGenerateCourse,
  onUploadPdf,
  onFinish,
  onCopyInvite,
  telegramManagerKey,
  telegramDisplayName,
}: Props) {
  const [orgName, setOrgName] = useState('');
  const [email, setEmail] = useState('');
  const isTMA = !!telegramManagerKey;
  const [topic, setTopic] = useState('');
  const [mode, setMode] = useState<'topic' | 'pdf'>('topic');
  const pdfRef = useRef<HTMLInputElement>(null);

  const inviteUrl = typeof window !== 'undefined' ? `${window.location.origin}?invite=${inviteCode}` : '';

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 300,
    }}>
      <div style={{
        background: 'white', borderRadius: 16, padding: 32,
        width: '100%', maxWidth: 480,
        boxShadow: '0 8px 32px rgba(0,0,0,0.25)', position: 'relative',
      }}>
        {/* Progress dots */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 24 }}>
          {[1, 2, 3].map(s => (
            <div key={s} style={{
              width: 10, height: 10, borderRadius: '50%',
              background: s <= step ? '#3b82f6' : '#e2e8f0',
            }} />
          ))}
        </div>

        {step === 1 && (
          <button
            onClick={onClose}
            style={{
              position: 'absolute', top: 16, right: 16,
              background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 18, color: '#94a3b8', lineHeight: 1,
            }}
          >✕</button>
        )}

        {/* Step 1 */}
        {step === 1 && (
          <>
            <h2 style={{ margin: '0 0 8px', color: '#1e293b', fontSize: 22, textAlign: 'center' }}>
              👋 Добро пожаловать в VYUD LMS
            </h2>
            <p style={{ margin: '0 0 20px', color: '#64748b', fontSize: 14, textAlign: 'center' }}>
              Создайте организацию для вашей команды
            </p>
            <input
              value={orgName}
              onChange={e => setOrgName(e.target.value)}
              placeholder="Название компании *"
              style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 10, boxSizing: 'border-box', fontSize: 14 }}
            />
            {isTMA ? (
              <div style={{
                width: '100%', padding: 10, borderRadius: 8, border: '1px solid #e2e8f0',
                marginBottom: 20, boxSizing: 'border-box' as const, fontSize: 14,
                background: '#f8fafc', color: '#64748b', display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <span>✈️</span>
                <span>{telegramDisplayName ?? 'Telegram пользователь'}</span>
              </div>
            ) : (
              <input
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="Email менеджера *"
                type="email"
                style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 20, boxSizing: 'border-box', fontSize: 14 }}
              />
            )}
            <button
              onClick={() => onCreateOrg(orgName, isTMA ? telegramManagerKey! : email)}
              disabled={!orgName.trim() || (!isTMA && !email.trim())}
              style={{
                width: '100%', padding: 12, fontSize: 15, fontWeight: 600,
                background: !orgName.trim() || (!isTMA && !email.trim()) ? '#94a3b8' : '#3b82f6',
                color: 'white', border: 'none', borderRadius: 8,
                cursor: !orgName.trim() || (!isTMA && !email.trim()) ? 'not-allowed' : 'pointer',
              }}
            >
              Создать →
            </button>
          </>
        )}

        {/* Step 2 */}
        {step === 2 && (
          <>
            <h2 style={{ margin: '0 0 8px', color: '#1e293b', fontSize: 22, textAlign: 'center' }}>
              📚 Создайте первый курс
            </h2>
            <p style={{ margin: '0 0 16px', color: '#64748b', fontSize: 14, textAlign: 'center' }}>
              Загрузите PDF или введите тему вручную
            </p>
            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              {(['topic', 'pdf'] as const).map(m => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  style={{
                    flex: 1, padding: '8px 0', borderRadius: 8, border: 'none',
                    background: mode === m ? '#3b82f6' : '#f1f5f9',
                    color: mode === m ? 'white' : '#64748b',
                    cursor: 'pointer', fontSize: 14, fontWeight: 500,
                  }}
                >
                  {m === 'topic' ? '✍️ По теме' : '📄 Из PDF'}
                </button>
              ))}
            </div>

            {mode === 'topic' ? (
              <>
                <input
                  value={topic}
                  onChange={e => setTopic(e.target.value)}
                  placeholder="Тема курса (напр. Python, React...)"
                  style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 12, boxSizing: 'border-box', fontSize: 14 }}
                />
                <button
                  onClick={() => onGenerateCourse(topic)}
                  disabled={isGenerating || !topic.trim()}
                  style={{
                    width: '100%', padding: 12, fontSize: 15, fontWeight: 600,
                    background: isGenerating || !topic.trim() ? '#94a3b8' : '#3b82f6',
                    color: 'white', border: 'none', borderRadius: 8,
                    cursor: isGenerating || !topic.trim() ? 'not-allowed' : 'pointer',
                  }}
                >
                  {isGenerating ? '⏳ Генерирую...' : 'Сгенерировать'}
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => pdfRef.current?.click()}
                  disabled={isGenerating}
                  style={{
                    width: '100%', padding: 12, fontSize: 15, fontWeight: 600,
                    background: isGenerating ? '#94a3b8' : '#f59e0b',
                    color: 'white', border: 'none', borderRadius: 8,
                    cursor: isGenerating ? 'not-allowed' : 'pointer',
                  }}
                >
                  {isGenerating ? '⏳ Загружаю...' : '📄 Выбрать PDF (до 20MB)'}
                </button>
                <input
                  ref={pdfRef}
                  type="file"
                  accept=".pdf"
                  style={{ display: 'none' }}
                  onChange={e => {
                    const file = e.target.files?.[0];
                    if (file) onUploadPdf(file);
                  }}
                />
              </>
            )}
          </>
        )}

        {/* Step 3 */}
        {step === 3 && (
          <>
            <h2 style={{ margin: '0 0 8px', color: '#1e293b', fontSize: 22, textAlign: 'center' }}>
              🎉 Курс создан!
            </h2>
            <p style={{ margin: '0 0 16px', color: '#64748b', fontSize: 14, textAlign: 'center' }}>
              Отправьте эту ссылку сотрудникам — они сразу попадут в курс
            </p>
            <div style={{
              background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8,
              padding: '10px 12px', marginBottom: 16, fontSize: 13, color: '#334155',
              wordBreak: 'break-all',
            }}>
              {inviteUrl}
            </div>
            <button
              onClick={onCopyInvite}
              style={{
                width: '100%', padding: 12, fontSize: 15, fontWeight: 600,
                background: '#3b82f6', color: 'white', border: 'none', borderRadius: 8,
                cursor: 'pointer', marginBottom: 10,
              }}
            >
              📋 Скопировать ссылку
            </button>
            <button
              onClick={onFinish}
              style={{
                width: '100%', padding: 12, fontSize: 14,
                background: '#f1f5f9', color: '#475569', border: 'none', borderRadius: 8,
                cursor: 'pointer',
              }}
            >
              Открыть граф →
            </button>
          </>
        )}
      </div>
    </div>
  );
}

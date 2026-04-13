'use client';

import { useEffect, useState } from 'react';
import { completeSop, fetchSop } from '@/lib/api';
import type { SOPDetail, SOPQuizQuestion } from '@/types';

interface Props {
  sopId: number;
  userKey: string;
  onClose: () => void;
  onCompleted: (sopId: number, score: number, maxScore: number) => void;
}

type Screen = 'steps' | 'quiz' | 'result';

export function SOPViewerModal({ sopId, userKey, onClose, onCompleted }: Props) {
  const [sop, setSop] = useState<SOPDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [screen, setScreen] = useState<Screen>('steps');
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [score, setScore] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchSop(sopId)
      .then(setSop)
      .catch(() => setSop(null))
      .finally(() => setIsLoading(false));
  }, [sopId]);

  const quiz: SOPQuizQuestion[] = sop?.quiz_json ?? [];
  const hasQuiz = quiz.length > 0;

  const handleSubmitQuiz = async () => {
    const correct = quiz.filter((q, i) => answers[i] === q.correct_answer).length;
    setScore(correct);
    setIsSubmitting(true);
    try {
      await completeSop(sopId, userKey, correct, quiz.length);
      onCompleted(sopId, correct, quiz.length);
    } catch { /* best-effort */ }
    finally {
      setIsSubmitting(false);
      setScreen('result');
    }
  };

  const handleSkipQuiz = async () => {
    setIsSubmitting(true);
    try {
      await completeSop(sopId, userKey, 0, 0);
      onCompleted(sopId, 0, 0);
    } catch { /* best-effort */ }
    finally {
      setIsSubmitting(false);
      setScreen('result');
    }
  };

  if (isLoading || !sop) {
    return (
      <div style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 250,
      }}>
        <div style={{
          background: 'white', borderRadius: 16, padding: 48,
          fontSize: 18, color: '#1e293b',
        }}>
          {isLoading ? '⏳ Загрузка...' : '❌ Не удалось загрузить СОП'}
        </div>
      </div>
    );
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 250,
    }}>
      <div style={{
        background: 'white', borderRadius: 16, padding: 32,
        width: '100%', maxWidth: 580, maxHeight: '85vh',
        display: 'flex', flexDirection: 'column',
        boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
          <div>
            <h2 style={{ margin: '0 0 4px', fontSize: 18, color: '#1e293b' }}>{sop.title}</h2>
            {sop.description && (
              <div style={{ fontSize: 13, color: '#64748b' }}>{sop.description}</div>
            )}
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20, color: '#94a3b8', flexShrink: 0, marginLeft: 12 }}
          >✕</button>
        </div>

        {/* Tab indicator */}
        {screen !== 'result' && (
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            {(['steps', ...(hasQuiz ? ['quiz'] : [])] as Screen[]).map(s => (
              <div key={s} style={{
                padding: '4px 12px', borderRadius: 999, fontSize: 12, fontWeight: 500,
                background: screen === s ? '#3b82f6' : '#f1f5f9',
                color: screen === s ? 'white' : '#64748b',
              }}>
                {s === 'steps' ? `Шаги (${sop.steps.length})` : `Тест (${quiz.length})`}
              </div>
            ))}
          </div>
        )}

        {/* Content area */}
        <div style={{ flex: 1, overflowY: 'auto' }}>

          {/* ── Steps screen ── */}
          {screen === 'steps' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {sop.steps.map(step => (
                <div key={step.step_number} style={{
                  display: 'flex', gap: 14, padding: '14px 16px',
                  background: '#f8fafc', borderRadius: 10, border: '1px solid #e2e8f0',
                }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                    background: '#3b82f6', color: 'white',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 700, fontSize: 13,
                  }}>
                    {step.step_number}
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14, color: '#1e293b', marginBottom: 4 }}>
                      {step.title}
                    </div>
                    <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.5 }}>
                      {step.content}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Quiz screen ── */}
          {screen === 'quiz' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {quiz.map((q, i) => (
                <div key={i}>
                  <div style={{ fontWeight: 600, fontSize: 14, color: '#1e293b', marginBottom: 10 }}>
                    {i + 1}. {q.question}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {q.options.map(opt => (
                      <label key={opt} style={{
                        display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
                        borderRadius: 8, cursor: 'pointer',
                        border: `1px solid ${answers[i] === opt ? '#3b82f6' : '#e2e8f0'}`,
                        background: answers[i] === opt ? '#eff6ff' : '#f8fafc',
                        fontSize: 13, color: '#334155',
                      }}>
                        <input
                          type="radio"
                          name={`q${i}`}
                          value={opt}
                          checked={answers[i] === opt}
                          onChange={() => setAnswers(prev => ({ ...prev, [i]: opt }))}
                          style={{ accentColor: '#3b82f6' }}
                        />
                        {opt}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Result screen ── */}
          {screen === 'result' && (
            <div style={{ textAlign: 'center', padding: '16px 0' }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>
                {quiz.length === 0 ? '✅' : score === quiz.length ? '🏆' : score >= quiz.length / 2 ? '👍' : '📚'}
              </div>
              {quiz.length > 0 ? (
                <>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#1e293b', marginBottom: 8 }}>
                    {score} / {quiz.length} правильных ответов
                  </div>
                  <div style={{ fontSize: 14, color: '#64748b', marginBottom: 24 }}>
                    {score === quiz.length
                      ? 'Отлично! Вы знаете эту процедуру.'
                      : score >= quiz.length / 2
                      ? 'Хороший результат. Изучите пропущенные шаги.'
                      : 'Рекомендуем перечитать шаги ещё раз.'}
                  </div>
                </>
              ) : (
                <div style={{ fontSize: 16, color: '#64748b', marginBottom: 24 }}>
                  СОП отмечен как пройденный.
                </div>
              )}
              <button
                onClick={onClose}
                style={{
                  padding: '10px 28px', background: '#3b82f6', color: 'white',
                  border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 15, cursor: 'pointer',
                }}
              >
                Закрыть
              </button>
            </div>
          )}
        </div>

        {/* Footer actions */}
        {screen === 'steps' && (
          <div style={{ marginTop: 20, display: 'flex', gap: 10 }}>
            {hasQuiz ? (
              <button
                onClick={() => setScreen('quiz')}
                style={{
                  flex: 1, padding: 12, background: '#3b82f6', color: 'white',
                  border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 15, cursor: 'pointer',
                }}
              >
                Пройти тест →
              </button>
            ) : (
              <button
                onClick={handleSkipQuiz}
                disabled={isSubmitting}
                style={{
                  flex: 1, padding: 12, background: '#22c55e', color: 'white',
                  border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 15,
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                }}
              >
                {isSubmitting ? '⏳ Сохраняю...' : '✅ Отметить как пройденный'}
              </button>
            )}
          </div>
        )}

        {screen === 'quiz' && (
          <div style={{ marginTop: 20, display: 'flex', gap: 10 }}>
            <button
              onClick={() => setScreen('steps')}
              style={{
                padding: '10px 16px', background: '#f1f5f9', color: '#475569',
                border: 'none', borderRadius: 8, fontSize: 14, cursor: 'pointer',
              }}
            >
              ← Шаги
            </button>
            <button
              onClick={handleSubmitQuiz}
              disabled={Object.keys(answers).length < quiz.length || isSubmitting}
              style={{
                flex: 1, padding: 12, fontWeight: 600, fontSize: 15, border: 'none', borderRadius: 8,
                background: Object.keys(answers).length < quiz.length || isSubmitting ? '#94a3b8' : '#3b82f6',
                color: 'white',
                cursor: Object.keys(answers).length < quiz.length || isSubmitting ? 'not-allowed' : 'pointer',
              }}
            >
              {isSubmitting ? '⏳ Проверяю...' : `Отправить ответы (${Object.keys(answers).length}/${quiz.length})`}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

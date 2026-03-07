"use client";

import React, { useEffect, useState } from 'react';
import { ReactFlow, Background, Controls } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const fallbackNodes = [
  { id: 'test-1', position: { x: 100, y: 100 }, data: { label: 'Тестовый узел 1' }, style: { background: '#fff', border: '2px solid red', padding: '10px' } },
  { id: 'test-2', position: { x: 400, y: 100 }, data: { label: 'Тестовый узел 2' }, style: { background: '#fff', border: '2px solid red', padding: '10px' } }
];
const fallbackEdges = [{ id: 'e-test', source: 'test-1', target: 'test-2', animated: true }];

export default function Page() {
  const [nodes, setNodes] = useState(fallbackNodes);
  const [edges, setEdges] = useState(fallbackEdges);
  
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  
  // Выбор модели
  const [selectedModel, setSelectedModel] = useState<string>("gemini/gemini-3-flash");

  // Состояния для квиза
  const [quizQuestions, setQuizQuestions] = useState<any[]>([]);
  const [isQuizLoading, setIsQuizLoading] = useState(false);
  const [showQuiz, setShowQuiz] = useState(false);
  const [userAnswers, setUserAnswers] = useState<{[key: number]: string}>({});

  const onNodeClick = async (event: any, node: any) => {
    if (!node.data?.label) return;
    
    // Проверка доступности узла
    if (node.data?.isAvailable === false) {
      alert("Сначала изучи предыдущие темы!");
      return;
    }

    const topic = node.data.label;
    setSelectedTopic(topic);
    setSelectedNodeId(node.id);
    setExplanation(null);
    setIsAiLoading(true);
    
    // Сбрасываем состояние квиза при выборе новой темы
    setShowQuiz(false);
    setQuizQuestions([]);
    setUserAnswers({});

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/explain/${encodeURIComponent(topic)}?model=${selectedModel}`);
      if (!res.ok) {
        setExplanation("Ошибка получения данных от API");
      } else {
        const data = await res.json();
        setExplanation(data.explanation);
      }
    } catch (err) {
      console.error(err);
      setExplanation("Не удалось получить объяснение. Попробуйте позже.");
    } finally {
      setIsAiLoading(false);
    }
  };

  const loadQuiz = async () => {
    if (!selectedTopic) return;
    setIsQuizLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/quiz/${encodeURIComponent(selectedTopic)}?model=${selectedModel}`);
      if (res.ok) {
        const data = await res.json();
        setQuizQuestions(data.questions || []);
        setShowQuiz(true);
      }
    } catch (err) {
      console.error("Ошибка загрузки теста:", err);
    } finally {
      setIsQuizLoading(false);
    }
  };

  const handleAnswerClick = (qIndex: number, option: string) => {
    // Если уже ответили на этот вопрос, не даем менять (или можно разрешить, зависит от логики)
    if (userAnswers[qIndex]) return;
    
    setUserAnswers(prev => ({
      ...prev,
      [qIndex]: option
    }));
  };

  const handleComplete = async () => {
    if (!selectedNodeId) return;

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/nodes/${selectedNodeId}/toggle-complete`, {
        method: 'POST'
      });
      
      if (res.ok) {
        const data = await res.json();
        const isCompleted = data.is_completed;

        setNodes((nds) =>
          nds.map((node) => {
            if (node.id === selectedNodeId) {
              const bg = isCompleted ? '#4ADE80' : '#fff';
              const border = isCompleted ? '2px solid #166534' : '2px solid blue';
              
              return {
                ...node,
                style: { 
                  ...node.style, 
                  background: bg, 
                  border: border
                },
                data: { ...node.data, isCompleted: isCompleted }
              };
            }
            return node;
          })
        );
      }
    } catch (err) {
      console.error("Ошибка сохранения прогресса:", err);
    }
  };

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/knowledge-graph')
      .then(res => res.json())
      .then(data => {
        console.log("СЫРЫЕ ДАННЫЕ:", data);
        
        if (data && data.nodes && data.nodes.length > 0) {
          const formattedNodes = data.nodes.map((node, index) => {
            const safeY = (node.level || 1) * 150;
            const safeX = index * 250 + 100;

            const isCompleted = node.is_completed;
            const isAvailable = node.is_available;
            
            let bg = '#fff';
            let border = '2px solid blue';
            let opacity = 1;
            let color = '#000';

            if (isCompleted) {
              bg = '#4ADE80';
              border = '2px solid #166534';
            } else if (!isAvailable) {
              bg = '#e5e7eb'; // серый
              border = '2px dashed #9ca3af'; // пунктир
              opacity = 0.7;
              color = '#6b7280';
            }

            return {
              id: String(node.id),
              position: { x: safeX, y: safeY },
              data: { label: node.label || "Без названия", isCompleted, isAvailable },
              style: { background: bg, border: border, padding: '15px', borderRadius: '8px', color: color, opacity: opacity }
            };
          });

          const formattedEdges = data.edges.map(edge => ({
            id: `e${edge.source}-${edge.target}`,
            source: String(edge.source),
            target: String(edge.target),
            animated: true,
            style: { stroke: '#555', strokeWidth: 2 }
          }));

          console.log("ОТФОРМАТИРОВАННЫЕ УЗЛЫ:", formattedNodes);
          setNodes(formattedNodes);
          setEdges(formattedEdges);
        }
      })
      .catch(err => console.error("Ошибка сети:", err));
  }, []);

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#f8f9fa', position: 'relative' }}>
      <ReactFlow 
        nodes={nodes} 
        edges={edges} 
        fitView 
        onNodeClick={onNodeClick}
      >
        <Background />
        <Controls />
      </ReactFlow>

      {/* Всплывающее окно с ИИ-уроком */}
      {selectedTopic && (
        <div style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          width: '350px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          padding: '20px',
          background: 'white',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
          borderRadius: '8px',
          zIndex: 10,
          border: '1px solid #e5e7eb',
          color: '#333'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
            <h3 style={{ fontWeight: 'bold', margin: 0 }}>{selectedTopic}</h3>
            <button 
              onClick={() => setSelectedTopic(null)}
              style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '16px' }}
            >
              ✕
            </button>
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label style={{ fontSize: '12px', color: '#666', display: 'block', marginBottom: '4px' }}>AI Модель:</label>
            <select 
              value={selectedModel} 
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #ddd', fontSize: '13px' }}
            >
              <option value="gemini/gemini-3-flash">Gemini 3 Flash (Актуальная)</option>
              <option value="anthropic/claude-3-5-sonnet-20240620">Claude 3.5 Sonnet (Лучший текст)</option>
              <option value="groq/llama-3.1-70b-versatile">Llama 3.1 70B (Groq - Мгновенно)</option>
              <option value="huggingface/Qwen/Qwen2.5-72B-Instruct">Qwen 2.5 72B (Hugging Face)</option>
            </select>
          </div>
          
          {isAiLoading ? (
            <p style={{ color: '#6b7280', fontStyle: 'italic' }}>🤖 Генерирую урок...</p>
          ) : (
            <div style={{ maxHeight: '80vh', overflowY: 'auto' }}>
              {!showQuiz ? (
                <>
                  <p style={{ lineHeight: '1.5', fontSize: '14px', marginBottom: '15px' }}>{explanation}</p>
                  <div style={{ display: 'flex', gap: '10px', flexDirection: 'column' }}>
                    <button 
                      onClick={loadQuiz}
                      disabled={isQuizLoading}
                      style={{
                        width: '100%',
                        padding: '8px',
                        background: '#3b82f6',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        opacity: isQuizLoading ? 0.7 : 1
                      }}
                    >
                      {isQuizLoading ? "Генерирую тест..." : "Проверить знания"}
                    </button>
                    
                    <button 
                      onClick={handleComplete}
                      style={{
                        width: '100%',
                        padding: '8px',
                        background: '#10b981',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      ✅ Я всё понял! (Завершить/Отменить)
                    </button>
                  </div>
                </>
              ) : (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <h4 style={{ margin: 0, fontSize: '16px' }}>Тест</h4>
                    <button 
                      onClick={() => setShowQuiz(false)}
                      style={{ fontSize: '12px', background: '#e5e7eb', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', color: '#333' }}
                    >
                      Назад
                    </button>
                  </div>
                  
                  {quizQuestions.map((q, idx) => {
                    const userAnswer = userAnswers[idx];
                    const isAnswered = userAnswer !== undefined;
                    
                    return (
                      <div key={idx} style={{ marginBottom: '20px', paddingBottom: '10px', borderBottom: '1px solid #eee' }}>
                        <p style={{ fontWeight: 'bold', fontSize: '14px', marginBottom: '8px' }}>{idx + 1}. {q.question}</p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                          {q.options.map((opt: string) => {
                            let bgColor = '#f3f4f6'; // серый по умолчанию
                            let textColor = '#000';
                            
                            if (isAnswered) {
                              if (opt === q.answer) {
                                bgColor = '#dcfce7'; // зеленый (правильный)
                                textColor = '#166534';
                              } else if (opt === userAnswer && userAnswer !== q.answer) {
                                bgColor = '#fee2e2'; // красный (ошибка пользователя)
                                textColor = '#991b1b';
                              }
                            }

                            return (
                              <button
                                key={opt}
                                onClick={() => handleAnswerClick(idx, opt)}
                                disabled={isAnswered}
                                style={{
                                  padding: '6px',
                                  textAlign: 'left',
                                  background: bgColor,
                                  color: textColor,
                                  border: '1px solid #ddd',
                                  borderRadius: '4px',
                                  cursor: isAnswered ? 'default' : 'pointer',
                                  fontSize: '13px'
                                }}
                              >
                                {opt}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

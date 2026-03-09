"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, ReactFlowProvider, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const fallbackNodes = [
  { id: 'test-1', position: { x: 100, y: 100 }, data: { label: 'Тестовый узел 1' }, style: { background: '#fff', border: '2px solid red', padding: '10px' } },
  { id: 'test-2', position: { x: 400, y: 100 }, data: { label: 'Тестовый узел 2' }, style: { background: '#fff', border: '2px solid red', padding: '10px' } }
];
const fallbackEdges = [{ id: 'e-test', source: 'test-1', target: 'test-2', animated: true }];

function Flow() {
  const [nodes, setNodes, onNodesChange] = useNodesState(fallbackNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(fallbackEdges);
  const { fitView } = useReactFlow();
  
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  
  // Генерация курса
  const [newCourseTopic, setNewCourseTopic] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  // Выбор модели
  const [selectedModel, setSelectedModel] = useState<string>("groq/llama-3.3-70b-versatile");

  // Состояния для квиза
  const [quizQuestions, setQuizQuestions] = useState<any[]>([]);
  const [isQuizLoading, setIsQuizLoading] = useState(false);
  const [showQuiz, setShowQuiz] = useState(false);
  // Храним индекс выбранного ответа: { [questionIndex]: optionIndex }
  const [userAnswers, setUserAnswers] = useState<{[key: number]: number}>({});

  const onNodeClick = useCallback(async (event: any, node: any) => {
    if (!node.data?.label) return;
    
    // Проверка доступности узла
    if (node.data?.isAvailable === false) {
      alert("Сначала изучи предыдущие темы!");
      return;
    }

    // Зум на узел
    fitView({ nodes: [{ id: node.id }], duration: 800, padding: 2 });

    const topic = node.data.label;
    setSelectedTopic(topic);
    setSelectedNodeId(node.id);
    setExplanation(null);
    setIsAiLoading(true);
    
    // Обновляем стили узлов для подсветки активного
    setNodes((nds) => nds.map((n) => {
      const isSelected = n.id === node.id;
      return {
        ...n,
        style: {
          ...n.style,
          boxShadow: isSelected ? '0 0 15px 2px rgba(59, 130, 246, 0.6)' : 'none',
          transform: isSelected ? 'scale(1.05)' : 'scale(1)',
          transition: 'all 0.3s ease',
          zIndex: isSelected ? 1000 : 1
        }
      };
    }));
    
    // Сбрасываем состояние квиза при выборе новой темы
    setShowQuiz(false);
    setQuizQuestions([]);
    setUserAnswers({});

    try {
      const res = await fetch(`${API_BASE_URL}/api/explain/${encodeURIComponent(topic)}?model=${selectedModel}`);
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
  }, [fitView, selectedModel, setNodes]);

  // Функция расширения (Expand)
  const onExpandNode = async (event: React.MouseEvent, nodeId: string, label: string) => {
    event.stopPropagation(); // Чтобы не срабатывал onNodeClick
    
    const confirmExpand = window.confirm(`Сгенерировать подтемы для "${label}"?`);
    if (!confirmExpand) return;

    try {
        // Реальный запрос к бэкенду
        const res = await fetch(`${API_BASE_URL}/api/nodes/${nodeId}/subtopics`, {
            method: 'POST'
        });

        if (!res.ok) {
            alert("Ошибка генерации подтем");
            return;
        }

        const data = await res.json();
        const subtopics = data.subtopics; // ожидаем массив [{id, label}, ...]

        if (!subtopics || subtopics.length === 0) {
            alert("Не удалось сгенерировать подтемы");
            return;
        }

        // Добавляем новые узлы, сохраняя старые
        setNodes((nds) => {
            const parentNode = nds.find(n => n.id === nodeId);
            if (!parentNode) return nds;
            
            const baseX = parentNode.position.x;
            const baseY = parentNode.position.y; // Используем координаты родителя как базу

            const createdNodes = subtopics.map((sub: any, i: number) => ({
                id: String(sub.id),
                // Позиционируем относительно родителя (смещение вниз и в стороны)
                position: { x: (i - 1) * 220, y: 250 }, 
                data: { 
                    label: sub.label, 
                    isCompleted: false, 
                    isAvailable: true 
                },
                style: { 
                    background: '#fff', 
                    border: '2px solid #8b5cf6', // фиолетовый для подтем
                    padding: '10px', 
                    borderRadius: '12px', 
                    width: 180,
                    fontSize: '13px',
                    textAlign: 'center',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                },
                draggable: true,
                parentNode: nodeId, // Привязка к родителю (если ReactFlow поддерживает группировку, иначе просто логическая связь)
                extent: 'parent' // Ограничение перемещения (опционально, можно убрать)
            }));
            
            // Если мы не используем Group Nodes в React Flow, то parentNode может вести себя как группа.
            // Для простой визуализации "дерева" лучше задавать абсолютные координаты, если parentNode не настроен как группа.
            // Но чтобы новые узлы не улетали, зададим им абсолютные координаты относительно мира, если parentNode не работает как ожидается.
            
            const absoluteCreatedNodes = subtopics.map((sub: any, i: number) => ({
                id: String(sub.id),
                position: { x: baseX + (i - 1) * 220, y: baseY + 200 },
                data: { label: sub.label, isCompleted: false, isAvailable: true },
                style: { 
                    background: '#fff', 
                    border: '2px solid #8b5cf6', 
                    padding: '10px', 
                    borderRadius: '12px', 
                    width: 180,
                    fontSize: '13px',
                    textAlign: 'center',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                },
                draggable: true
            }));

            return nds.concat(absoluteCreatedNodes);
        });

        // Добавляем ребра
        setEdges((eds) => {
            const newEdges = subtopics.map((sub: any) => ({
                id: `e-${nodeId}-${sub.id}`,
                source: nodeId,
                target: String(sub.id),
                animated: true,
                style: { stroke: '#8b5cf6', strokeWidth: 2, strokeDasharray: '5,5' }
            }));
            return eds.concat(newEdges);
        });

    } catch (e) {
        console.error(e);
        alert("Ошибка расширения темы");
    }
  };

  const loadQuiz = async () => {
    if (!selectedTopic) return;
    setIsQuizLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/quiz/${encodeURIComponent(selectedTopic)}?model=${selectedModel}`);
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

  const handleAnswerClick = (qIndex: number, optionIndex: number) => {
    // Если уже ответили на этот вопрос, не даем менять
    if (userAnswers[qIndex] !== undefined) return;
    
    setUserAnswers(prev => ({
      ...prev,
      [qIndex]: optionIndex
    }));
  };

  const handleComplete = async () => {
    if (!selectedNodeId) return;
    
    // Если тест не открыт или нет вопросов, просто закрываем (или можно оставить старую логику toggle)
    if (!showQuiz || quizQuestions.length === 0) {
        setSelectedTopic(null);
        return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/nodes/${selectedNodeId}/check-quiz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            answers: userAnswers,
            questions: quizQuestions
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        
        if (data.passed) {
            alert(`🎉 Поздравляем! Тест пройден (${data.score}). Узел отмечен как изученный.`);
            const isCompleted = true;

            // Обновляем текущий узел и перезапрашиваем граф для обновления доступности следующих узлов
            // Но для мгновенного эффекта обновим локально текущий узел сразу
            setNodes((nds) =>
              nds.map((node) => {
                if (node.id === selectedNodeId) {
                  return {
                    ...node,
                    style: { 
                      ...node.style, 
                      background: '#4ADE80', 
                      border: '2px solid #166534',
                      color: '#000'
                    },
                    data: { 
                        ...node.data, 
                        isCompleted: true,
                        label: (
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px' }}>
                                {node.data.label as string} <span>✅</span>
                            </div>
                        )
                    }
                  };
                }
                return node;
              })
            );
            
            // Перезагружаем граф полностью, чтобы открыть следующие узлы (бэкенд пересчитает is_available)
            setTimeout(() => {
                fetchGraph();
            }, 1000);
            
            setSelectedTopic(null); // Закрываем окно

        } else {
            alert(`❌ Тест не пройден. Ваш результат: ${data.score}. Попробуйте еще раз!`);
        }
      } else {
          alert("Ошибка проверки теста");
      }
    } catch (err) {
      console.error("Ошибка сохранения прогресса:", err);
    }
  };

  const fetchGraph = useCallback(() => {
    fetch(`${API_BASE_URL}/api/knowledge-graph`)
      .then(res => res.json())
      .then(data => {
        console.log("СЫРЫЕ ДАННЫЕ:", data);
        
        if (data && data.nodes && data.nodes.length > 0) {
          const formattedNodes = data.nodes.map((node: any, index: number) => {
            const safeY = (node.level || 1) * 150;
            const safeX = index * 250 + 100;

            const isCompleted = node.is_completed;
            const isAvailable = node.is_available;
            
            let bg = '#fff';
            let border = '2px solid #3b82f6'; // синий по дефолту
            let opacity = 1;
            let color = '#000';
            let cursor = 'pointer';

            if (isCompleted) {
              bg = '#4ADE80'; // Зеленый
              border = '2px solid #166534';
            } else if (!isAvailable) {
              bg = '#f3f4f6'; // серый
              border = '2px dashed #d1d5db'; // пунктир
              opacity = 0.6;
              color = '#9ca3af';
              cursor = 'not-allowed';
            } else {
                // Доступен, но не пройден (белый фон)
                bg = '#fff';
            }

            return {
              id: String(node.id),
              position: { x: safeX, y: safeY },
              data: { 
                  label: isCompleted ? (
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px' }}>
                          {node.label} <span>✅</span>
                      </div>
                  ) : node.label || "Без названия", 
                  isCompleted, 
                  isAvailable
              },
              style: { 
                  background: bg, 
                  border: border, 
                  padding: '10px', 
                  borderRadius: '12px', 
                  color: color, 
                  opacity: opacity,
                  width: 200,
                  fontSize: '14px',
                  textAlign: 'center',
                  boxShadow: isAvailable ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
                  transition: 'all 0.5s ease',
                  cursor: cursor
              },
              draggable: true 
            };
          });

          const formattedEdges = data.edges.map((edge: any) => ({
            id: `e${edge.source}-${edge.target}`,
            source: String(edge.source),
            target: String(edge.target),
            animated: true,
            style: { stroke: '#9ca3af', strokeWidth: 2 }
          }));

          setNodes(formattedNodes);
          setEdges(formattedEdges);
        }
      })
      .catch(err => console.error("Ошибка сети:", err));
  }, [setNodes, setEdges]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);


  const handleGenerateCourse = async () => {
    if (!newCourseTopic.trim()) return;
    setIsGenerating(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/courses/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: newCourseTopic })
      });
      if (res.ok) {
        alert("Курс успешно сгенерирован! Обновляем граф...");
        setNewCourseTopic("");
        // Перезагружаем страницу или заново фетчим граф
        window.location.reload(); 
      } else {
        alert("Ошибка генерации курса");
      }
    } catch (e) {
      console.error(e);
      alert("Ошибка сети");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#f8f9fa', position: 'relative' }}>
      {/* Панель генерации курса */}
      <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 10, background: 'white', padding: 15, borderRadius: 8, boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: 16 }}>Создать новый курс</h3>
        <input 
          type="text" 
          value={newCourseTopic}
          onChange={(e) => setNewCourseTopic(e.target.value)}
          placeholder="Например: Основы маркетинга"
          style={{ padding: '8px', width: '200px', marginRight: '10px', border: '1px solid #ddd', borderRadius: 4 }}
        />
        <button 
          onClick={handleGenerateCourse}
          disabled={isGenerating}
          style={{ padding: '8px 15px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer', opacity: isGenerating ? 0.7 : 1 }}
        >
          {isGenerating ? "Генерация..." : "Сгенерировать"}
        </button>
      </div>

      <ReactFlow 
        nodes={nodes} 
        edges={edges} 
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView 
        onNodeClick={onNodeClick}
        attributionPosition="bottom-left"
      >
        <Background color="#f1f1f1" gap={16} />
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
            <div style={{ display: 'flex', gap: '5px' }}>
              <button 
                onClick={(e) => selectedNodeId && onExpandNode(e, selectedNodeId, selectedTopic)}
                style={{ border: 'none', background: '#3b82f6', color: '#fff', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', padding: '2px 8px' }}
                title="Сгенерировать подтемы"
              >
                + Подтемы
              </button>
              <button 
                onClick={() => setSelectedTopic(null)}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '16px' }}
              >
                ✕
              </button>
            </div>
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label style={{ fontSize: '12px', color: '#666', display: 'block', marginBottom: '4px' }}>AI Модель:</label>
            <select 
              value={selectedModel} 
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #ddd', fontSize: '13px' }}
            >
              <option value="groq/llama-3.3-70b-versatile">Llama 3.3 70B (Groq - Стабильно)</option>
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
                    
                    {/* Кнопка завершения убрана, теперь завершение только через тест */}
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
                    const userAnswerIdx = userAnswers[idx];
                    
                    return (
                      <div key={idx} style={{ marginBottom: '20px', paddingBottom: '10px', borderBottom: '1px solid #eee' }}>
                        <p style={{ fontWeight: 'bold', fontSize: '14px', marginBottom: '8px' }}>{idx + 1}. {q.question}</p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                          {q.options.map((opt: string, optIdx: number) => {
                            // Пока не показываем правильность, проверка в конце
                            const isSelected = userAnswerIdx === optIdx;
                            const bgColor = isSelected ? '#bfdbfe' : '#f3f4f6'; // синий если выбран
                            const borderColor = isSelected ? '#2563eb' : '#ddd';

                            return (
                              <button
                                key={optIdx}
                                onClick={() => handleAnswerClick(idx, optIdx)}
                                style={{
                                  padding: '8px',
                                  textAlign: 'left',
                                  background: bgColor,
                                  color: '#000',
                                  border: `1px solid ${borderColor}`,
                                  borderRadius: '4px',
                                  cursor: 'pointer',
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
                  
                  <button 
                    onClick={handleComplete}
                    style={{
                      width: '100%',
                      padding: '10px',
                      background: '#16a34a',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontWeight: 'bold',
                      marginTop: '10px'
                    }}
                  >
                    Проверить ответы и завершить
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Page() {
  return (
    <ReactFlowProvider>
      <Flow />
    </ReactFlowProvider>
  );
}

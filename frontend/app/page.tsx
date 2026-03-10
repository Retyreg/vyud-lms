"use client";

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { BookOpen, ChevronRight, CheckCircle2, AlertCircle, Loader2, Plus, X, RefreshCw } from 'lucide-react';

// Хардкод адреса для стабильности в облаке
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://vyud-lms-backend.onrender.com";

/**
 * Кастомный компонент Графа (замена ReactFlow для работы в данной среде)
 */
const SimpleGraph = ({ nodes, edges, onNodeClick, onExpandNode }) => {
  const containerRef = useRef(null);

  // Отрисовка связей (линий) между узлами
  const renderEdges = () => {
    return edges.map((edge) => {
      const sourceNode = nodes.find(n => n.id === edge.source);
      const targetNode = nodes.find(n => n.id === edge.target);

      if (!sourceNode || !targetNode) return null;

      const x1 = sourceNode.position.x + 100; // Центр узла (ширина 200)
      const y1 = sourceNode.position.y + 25;  // Центр узла (высота ~50)
      const x2 = targetNode.position.x + 100;
      const y2 = targetNode.position.y + 25;

      return (
        <line
          key={edge.id}
          x1={x1}
          y1={y1}
          x2={x2}
          y2={y2}
          stroke="#9ca3af"
          strokeWidth="2"
          strokeDasharray={edge.animated ? "5,5" : "0"}
          className={edge.animated ? "animate-pulse" : ""}
        />
      );
    });
  };

  return (
    <div 
      ref={containerRef}
      className="relative w-full h-full overflow-auto bg-slate-50 cursor-grab active:cursor-grabbing"
      style={{ minHeight: '600px' }}
    >
      <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ minWidth: '2000px', minHeight: '2000px' }}>
        {renderEdges()}
      </svg>
      
      {nodes.map((node) => (
        <div
          key={node.id}
          onClick={(e) => onNodeClick(e, node)}
          className={`absolute flex flex-col items-center justify-center p-3 rounded-xl border-2 transition-all duration-300 cursor-pointer select-none
            ${node.data.isCompleted ? 'bg-green-50 border-green-600 text-green-900 shadow-sm' : 
              node.data.isAvailable ? 'bg-white border-blue-500 text-slate-800 shadow-md hover:scale-105 hover:shadow-lg' : 
              'bg-gray-100 border-gray-300 text-gray-400 opacity-60 cursor-not-allowed'}`}
          style={{
            left: node.position.x,
            top: node.position.y,
            width: '200px',
            zIndex: 10
          }}
        >
          <div className="text-sm font-semibold text-center mb-1">
            {node.data.label}
          </div>
          {node.data.isCompleted && <CheckCircle2 className="w-4 h-4 text-green-600" />}
          {!node.data.isAvailable && !node.data.isCompleted && <AlertCircle className="w-4 h-4 text-gray-400" />}
        </div>
      ))}
    </div>
  );
};

function Flow() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  
  const [newCourseTopic, setNewCourseTopic] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedModel, setSelectedModel] = useState("groq/llama-3.3-70b-versatile");

  const [quizQuestions, setQuizQuestions] = useState([]);
  const [isQuizLoading, setIsQuizLoading] = useState(false);
  const [showQuiz, setShowQuiz] = useState(false);
  const [userAnswers, setUserAnswers] = useState({});

  // Функция загрузки графа из БД
  const fetchGraph = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/courses/latest`);
      if (!res.ok) throw new Error("Course not found or DB empty");
      
      const data = await res.json();
      if (data && data.nodes && data.nodes.length > 0) {
        const formattedNodes = data.nodes.map((node, index) => {
          const safeY = (node.level || 1) * 150;
          const safeX = index * 250 + 100;

          return {
            id: String(node.id),
            position: { x: safeX, y: safeY },
            data: { 
              label: node.label || "Без названия", 
              isCompleted: node.is_completed, 
              isAvailable: node.is_available 
            }
          };
        });

        const formattedEdges = data.edges.map((edge) => ({
          id: `e${edge.source}-${edge.target}`,
          source: String(edge.source),
          target: String(edge.target),
          animated: true
        }));

        setNodes(formattedNodes);
        setEdges(formattedEdges);
      }
    } catch (err) {
      console.log("Status: ", err.message);
      // Если база пуста, показываем пустой экран или дефолтные узлы
      setNodes([]);
    }
  }, []);

  // Первичная загрузка
  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // Клик по узлу
  const onNodeClick = async (event, node) => {
    if (node.data.isAvailable === false && !node.data.isCompleted) {
      return; // Узел заблокирован
    }

    const topic = node.data.label;
    setSelectedTopic(topic);
    setSelectedNodeId(node.id);
    setExplanation(null);
    setIsAiLoading(true);
    setShowQuiz(false);
    setQuizQuestions([]);
    setUserAnswers({});

    try {
      const res = await fetch(`${API_BASE_URL}/api/explain/${encodeURIComponent(topic)}?model=${selectedModel}`);
      if (res.ok) {
        const data = await res.json();
        setExplanation(data.explanation);
      } else {
        setExplanation("Ошибка получения объяснения от ИИ.");
      }
    } catch (err) {
      setExplanation("Не удалось связаться с сервером.");
    } finally {
      setIsAiLoading(false);
    }
  };

  // Генерация подтем
  const onExpandNode = async (nodeId, label) => {
    if (!window.confirm(`Развернуть тему "${label}"?`)) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/nodes/${nodeId}/subtopics`, { method: 'POST' });
      if (res.ok) {
        alert("Подтемы созданы! Обновляем граф...");
        fetchGraph();
      }
    } catch (e) {
      alert("Ошибка сети при создании подтем");
    }
  };

  // Загрузка квиза
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
      console.error(err);
    } finally {
      setIsQuizLoading(false);
    }
  };

  const handleAnswerClick = (qIndex, optionIndex) => {
    if (userAnswers[qIndex] !== undefined) return;
    setUserAnswers(prev => ({ ...prev, [qIndex]: optionIndex }));
  };

  const handleComplete = async () => {
    if (!selectedNodeId) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/nodes/${selectedNodeId}/check-quiz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers: userAnswers, questions: quizQuestions })
      });
      
      if (res.ok) {
        const data = await res.json();
        if (data.passed) {
          alert("🎉 Тест пройден успешно!");
          setSelectedTopic(null);
          fetchGraph();
        } else {
          alert(`❌ Попробуйте еще раз. Ваш результат: ${data.score}`);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

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
        alert("Курс успешно сгенерирован в базе данных!");
        setNewCourseTopic("");
        fetchGraph();
      }
    } catch (e) {
      alert("Ошибка при генерации курса");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex flex-col w-full h-screen bg-slate-50 font-sans text-slate-900">
      {/* Шапка / Панель управления */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200 shadow-sm z-20">
        <div className="flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-blue-600" />
          <h1 className="text-xl font-bold tracking-tight">VYUD LMS</h1>
        </div>
        
        <div className="flex items-center gap-3">
          <input 
            type="text" 
            value={newCourseTopic} 
            onChange={(e) => setNewCourseTopic(e.target.value)} 
            placeholder="Тема курса..." 
            className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
          />
          <button 
            onClick={handleGenerateCourse} 
            disabled={isGenerating}
            className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            {isGenerating ? "Создаем..." : "Создать курс"}
          </button>
          <button onClick={fetchGraph} className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg transition-colors">
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </header>

      <main className="relative flex-1 overflow-hidden">
        {/* Интерактивный граф */}
        {nodes.length > 0 ? (
          <SimpleGraph 
            nodes={nodes} 
            edges={edges} 
            onNodeClick={onNodeClick} 
            onExpandNode={onExpandNode}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-4">
            <AlertCircle className="w-12 h-12 opacity-20" />
            <p className="text-lg">Введите тему выше, чтобы сгенерировать ваш первый курс</p>
          </div>
        )}

        {/* Сайдбар с уроком */}
        {selectedTopic && (
          <div className="absolute top-4 right-4 bottom-4 w-96 bg-white shadow-2xl rounded-2xl border border-slate-200 z-30 flex flex-col animate-in slide-in-from-right duration-300">
            <div className="flex items-center justify-between p-5 border-b border-slate-100">
              <h2 className="text-lg font-bold truncate pr-4">{selectedTopic}</h2>
              <button onClick={() => setSelectedTopic(null)} className="p-1 hover:bg-slate-100 rounded-full">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {isAiLoading ? (
                <div className="flex flex-col items-center justify-center h-40 gap-3">
                  <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                  <p className="text-sm text-slate-500 italic">ИИ готовит материал...</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {!showQuiz ? (
                    <>
                      <div className="prose prose-slate prose-sm max-w-none">
                        <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">{explanation}</p>
                      </div>
                      
                      <div className="space-y-3 pt-4 border-t border-slate-100">
                        <button 
                          onClick={loadQuiz} 
                          disabled={isQuizLoading}
                          className="w-full py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
                        >
                          {isQuizLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
                          Проверить знания
                        </button>
                        
                        <button 
                          onClick={() => onExpandNode(selectedNodeId, selectedTopic)}
                          className="w-full py-3 border-2 border-slate-200 text-slate-600 font-semibold rounded-xl hover:bg-slate-50 transition-colors"
                        >
                          Развернуть подтемы
                        </button>
                      </div>
                    </>
                  ) : (
                    <div className="space-y-6 animate-in fade-in duration-300">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-bold text-slate-800">Мини-тест</h3>
                        <button onClick={() => setShowQuiz(false)} className="text-xs text-blue-600 font-medium">К теории</button>
                      </div>
                      
                      {quizQuestions.map((q, idx) => (
                        <div key={idx} className="space-y-3">
                          <p className="text-sm font-bold text-slate-800 leading-snug">{idx + 1}. {q.question}</p>
                          <div className="grid gap-2">
                            {q.options.map((opt, optIdx) => (
                              <button 
                                key={optIdx} 
                                onClick={() => handleAnswerClick(idx, optIdx)} 
                                className={`text-left p-3 text-sm rounded-lg border transition-all
                                  ${userAnswers[idx] === optIdx ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium' : 'border-slate-200 hover:border-slate-300 bg-white'}`}
                              >
                                {opt}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                      
                      <button 
                        onClick={handleComplete} 
                        className="w-full py-4 bg-green-600 text-white font-bold rounded-xl hover:bg-green-700 shadow-lg shadow-green-100 transition-all active:scale-95"
                      >
                        Завершить урок
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function Page() {
  return (
    <Flow />
  );
}

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { 
  BookOpen, 
  ChevronRight, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Plus, 
  X, 
  RefreshCw,
  Zap,
  Layout
} from 'lucide-react';

// Адрес бэкенда
const API_BASE_URL = "https://vyud-lms-backend.onrender.com";

/**
 * Упрощенный компонент графа на SVG и Tailwind.
 * Заменяет ReactFlow для стабильной работы в Canvas.
 */
const InteractiveGraph = ({ nodes, edges, onNodeClick }) => {
  const containerRef = useRef(null);

  // Рисуем линии между узлами
  const renderConnections = () => {
    return edges.map((edge) => {
      const source = nodes.find(n => n.id === edge.source);
      const target = nodes.find(n => n.id === edge.target);

      if (!source || !target) return null;

      const x1 = source.position.x + 100; // Центр узла (w-200 / 2)
      const y1 = source.position.y + 40;  // Центр узла (h-80 / 2)
      const x2 = target.position.x + 100;
      const y2 = target.position.y + 40;

      return (
        <line
          key={edge.id}
          x1={x1}
          y1={y1}
          x2={x2}
          y2={y2}
          stroke="#cbd5e1"
          strokeWidth="2"
          strokeDasharray="5,5"
        />
      );
    });
  };

  return (
    <div className="relative w-full h-full overflow-auto bg-slate-50 p-20 min-h-[800px]">
      <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ minWidth: '2000px', minHeight: '2000px' }}>
        {renderConnections()}
      </svg>
      
      {nodes.map((node) => (
        <div
          key={node.id}
          onClick={() => onNodeClick(node)}
          className={`absolute w-52 h-20 flex flex-col items-center justify-center p-4 rounded-2xl border-2 transition-all duration-300 cursor-pointer select-none shadow-sm
            ${node.data.isCompleted 
              ? 'bg-green-50 border-green-500 text-green-900 shadow-green-100' 
              : node.data.isAvailable 
                ? 'bg-white border-blue-500 text-slate-800 hover:scale-105 hover:shadow-lg' 
                : 'bg-slate-100 border-slate-200 text-slate-400 grayscale opacity-60 cursor-not-allowed'}`}
          style={{
            left: node.position.x,
            top: node.position.y,
            zIndex: 10
          }}
        >
          <div className="text-xs font-bold text-center leading-tight mb-1 line-clamp-2">
            {node.data.label}
          </div>
          <div className="flex items-center gap-1">
            {node.data.isCompleted ? (
              <CheckCircle2 className="w-4 h-4 text-green-600" />
            ) : node.data.isAvailable ? (
              <Zap className="w-4 h-4 text-blue-500" />
            ) : (
              <AlertCircle className="w-4 h-4 text-slate-300" />
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

const App = () => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  
  const [newCourseTopic, setNewCourseTopic] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  const [quizQuestions, setQuizQuestions] = useState([]);
  const [isQuizLoading, setIsQuizLoading] = useState(false);
  const [showQuiz, setShowQuiz] = useState(false);
  const [userAnswers, setUserAnswers] = useState({});

  // Загрузка графа из БД
  const fetchGraph = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/courses/latest`);
      if (!res.ok) throw new Error("Course not found");
      
      const data = await res.json();
      if (data && data.nodes && data.nodes.length > 0) {
        const formattedNodes = data.nodes.map((node, index) => {
          // Улучшенное распределение узлов по сетке
          const row = node.level || 1;
          const col = index % 4;
          return {
            id: String(node.id),
            position: { x: col * 260 + 100, y: row * 180 },
            data: { 
              label: node.label, 
              isCompleted: node.is_completed, 
              isAvailable: node.is_available 
            }
          };
        });

        const formattedEdges = data.edges.map((edge) => ({
          id: `e${edge.source}-${edge.target}`,
          source: String(edge.source),
          target: String(edge.target)
        }));

        setNodes(formattedNodes);
        setEdges(formattedEdges);
      }
    } catch (err) {
      console.log("Status: ", err.message);
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const onNodeClick = async (node) => {
    if (!node.data.isAvailable && !node.data.isCompleted) {
      return; 
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
      const res = await fetch(`${API_BASE_URL}/api/explain/${encodeURIComponent(topic)}`);
      if (res.ok) {
        const data = await res.json();
        setExplanation(data.explanation);
      } else {
        setExplanation("Не удалось загрузить содержание урока.");
      }
    } catch (err) {
      setExplanation("Ошибка подключения к серверу.");
    } finally {
      setIsAiLoading(false);
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
        setNewCourseTopic("");
        fetchGraph();
      } else {
        const err = await res.json();
        alert(`Ошибка: ${err.detail || "Не удалось создать курс"}`);
      }
    } catch (e) {
      alert("Ошибка сети. Убедитесь, что бэкенд на Render активен.");
    } finally {
      setIsGenerating(false);
    }
  };

  const loadQuiz = async () => {
    setIsQuizLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/quiz/${encodeURIComponent(selectedTopic)}`);
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
          alert("🎉 Отлично! Тест пройден. Ваш прогресс сохранен.");
          setSelectedTopic(null);
          fetchGraph();
        } else {
          alert(`❌ Нужно подтянуть знания. Результат: ${data.score}`);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex flex-col w-full h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Навигация */}
      <header className="flex items-center justify-between px-8 py-4 bg-white border-b border-slate-200 z-50 sticky top-0 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg">
            <BookOpen className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-xl font-black tracking-tight text-slate-800">VYUD <span className="text-blue-600">LMS</span></h1>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="relative">
            <input 
              type="text" 
              value={newCourseTopic} 
              onChange={(e) => setNewCourseTopic(e.target.value)} 
              placeholder="Введите тему курса (например, JTBD)" 
              className="pl-4 pr-10 py-2.5 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none w-80 text-sm transition-all shadow-inner"
            />
          </div>
          <button 
            onClick={handleGenerateCourse} 
            disabled={isGenerating}
            className="flex items-center gap-2 px-6 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl transition-all active:scale-95 disabled:opacity-50"
          >
            {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            {isGenerating ? "Генерация..." : "Создать"}
          </button>
          <button 
            onClick={fetchGraph} 
            className="p-2.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all"
            title="Обновить прогресс"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </header>

      <main className="relative flex-1 overflow-hidden">
        {/* Граф обучения */}
        {nodes.length > 0 ? (
          <InteractiveGraph 
            nodes={nodes} 
            edges={edges} 
            onNodeClick={onNodeClick} 
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full bg-slate-50 text-center p-10 animate-in fade-in zoom-in duration-500">
            <div className="w-24 h-24 bg-white rounded-3xl shadow-xl flex items-center justify-center mb-6">
              <Layout className="w-10 h-10 text-slate-200" />
            </div>
            <h2 className="text-2xl font-bold text-slate-800 mb-2">Ваша база обучения пуста</h2>
            <p className="text-slate-500 max-w-sm leading-relaxed">
              Введите интересующую вас тему в поле выше, и наш ИИ построит персональную дорожную карту обучения.
            </p>
          </div>
        )}

        {/* Панель урока */}
        {selectedTopic && (
          <div className="absolute top-6 right-6 bottom-6 w-[420px] bg-white shadow-2xl rounded-3xl border border-slate-200 z-[100] flex flex-col overflow-hidden animate-in slide-in-from-right duration-300">
            <div className="flex items-center justify-between p-6 border-b border-slate-100 bg-slate-50/50">
              <div className="flex items-center gap-2 overflow-hidden">
                <Zap className="w-4 h-4 text-blue-500 flex-shrink-0" />
                <h2 className="text-lg font-bold text-slate-800 truncate">{selectedTopic}</h2>
              </div>
              <button onClick={() => setSelectedTopic(null)} className="p-2 hover:bg-white rounded-full transition-colors shadow-sm">
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-8">
              {isAiLoading ? (
                <div className="flex flex-col items-center justify-center h-64 gap-4">
                  <div className="relative">
                    <div className="w-12 h-12 border-4 border-blue-100 border-t-blue-600 rounded-full animate-spin"></div>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Zap className="w-4 h-4 text-blue-600 animate-pulse" />
                    </div>
                  </div>
                  <p className="text-sm font-medium text-slate-400 italic">ИИ анализирует тему...</p>
                </div>
              ) : (
                <div className="space-y-8">
                  {!showQuiz ? (
                    <div className="animate-in fade-in duration-500">
                      <div className="prose prose-slate prose-sm max-w-none">
                        <div className="bg-blue-50/50 p-6 rounded-2xl border border-blue-100 mb-6">
                           <p className="text-slate-700 leading-relaxed text-base italic">
                            «{explanation}»
                           </p>
                        </div>
                        <h4 className="font-bold text-slate-800 mb-2 uppercase text-xs tracking-widest">Проверка знаний</h4>
                        <p className="text-slate-500 text-sm mb-6">
                          Чтобы открыть следующие темы курса, вам необходимо пройти небольшой проверочный тест.
                        </p>
                      </div>
                      
                      <button 
                        onClick={loadQuiz} 
                        disabled={isQuizLoading}
                        className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl transition-all flex items-center justify-center gap-3 shadow-lg shadow-blue-100 active:scale-[0.98]"
                      >
                        {isQuizLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ChevronRight className="w-5 h-5" />}
                        {isQuizLoading ? "Загружаем вопросы..." : "Начать тест"}
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-8 animate-in slide-in-from-bottom-4 duration-500">
                      <div className="flex items-center gap-2 mb-4">
                         <div className="h-1 flex-1 bg-slate-100 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-blue-500 transition-all duration-500" 
                              style={{ width: `${(Object.keys(userAnswers).length / quizQuestions.length) * 100}%` }}
                            ></div>
                         </div>
                         <span className="text-[10px] font-bold text-slate-400 uppercase">Прогресс</span>
                      </div>
                      
                      {quizQuestions.map((q, idx) => (
                        <div key={idx} className="space-y-4">
                          <p className="text-sm font-black text-slate-800 leading-tight">
                            <span className="text-blue-500 mr-2">0{idx + 1}.</span> {q.question}
                          </p>
                          <div className="grid gap-2">
                            {q.options.map((opt, optIdx) => (
                              <button 
                                key={optIdx} 
                                onClick={() => handleAnswerClick(idx, optIdx)} 
                                className={`text-left p-4 text-sm rounded-xl border-2 transition-all duration-200
                                  ${userAnswers[idx] === optIdx 
                                    ? 'border-blue-600 bg-blue-50 text-blue-700 font-bold shadow-md' 
                                    : 'border-slate-100 hover:border-slate-300 bg-white text-slate-600'}`}
                              >
                                {opt}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                      
                      <button 
                        onClick={handleComplete} 
                        className="w-full py-5 bg-slate-900 hover:bg-slate-800 text-white font-black rounded-2xl shadow-xl transition-all active:scale-[0.98] mt-4"
                      >
                        Завершить урок
                      </button>
                      <button 
                        onClick={() => setShowQuiz(false)} 
                        className="w-full py-2 text-slate-400 text-xs font-bold uppercase hover:text-slate-600 transition-colors"
                      >
                        Вернуться к теории
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
};

export default App;

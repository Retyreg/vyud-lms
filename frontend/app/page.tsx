"use client";

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, ReactFlowProvider, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://vyud-lms-backend.onrender.com";

const RETRY_MAX_ATTEMPTS = 6;
const RETRY_BASE_DELAY_MS = 5000;
const RETRY_MAX_DELAY_MS = 20000;

type BackendStatus = 'loading' | 'warming' | 'ok' | 'error';

interface ApiNode {
  id: number;
  label: string;
  level: number;
  is_completed: boolean;
  is_available: boolean;
}

interface ApiEdge {
  source: number;
  target: number;
}

interface FlowNode {
  id: string;
  data: { label: string; isAvailable: boolean };
}

function Flow() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { fitView } = useReactFlow();
  
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [newCourseTopic, setNewCourseTopic] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('loading');
  const [hasNodes, setHasNodes] = useState(false);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);

  const fetchGraph = useCallback(async (isRetry = false) => {
    if (!isRetry) {
      attemptRef.current = 0;
    }
    attemptRef.current += 1;
    const attempt = attemptRef.current;

    if (attempt > 1) {
      setBackendStatus('warming');
    } else {
      setBackendStatus('loading');
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/courses/latest`);

      if (!res.ok) {
        // 503 = DB not configured, still show the UI
        if (res.status === 503) {
          setBackendStatus('ok');
          return;
        }
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      setBackendStatus('ok');

      if (data?.nodes?.length > 0) {
        setHasNodes(true);
        const formattedNodes = data.nodes.map((node: ApiNode, idx: number) => ({
          id: String(node.id),
          position: { x: idx * 250, y: (node.level || 1) * 150 },
          data: { label: node.is_completed ? `${node.label} ✅` : node.label, isAvailable: node.is_available },
          style: { 
            background: node.is_completed ? '#4ADE80' : node.is_available ? '#fff' : '#f3f4f6',
            border: node.is_available ? '2px solid #3b82f6' : '2px dashed #ccc',
            borderRadius: '12px', width: 200, padding: '10px', textAlign: 'center' as const
          }
        }));

        const formattedEdges = data.edges.map((e: ApiEdge) => ({
          id: `e${e.source}-${e.target}`,
          source: String(e.source),
          target: String(e.target),
          animated: true
        }));

        setNodes(formattedNodes);
        setEdges(formattedEdges);
        setTimeout(() => fitView({ duration: 800 }), 100);
      } else {
        setHasNodes(false);
      }
    } catch {
      // Server may be sleeping (free-tier cold start) — retry with growing delay
      if (attempt < RETRY_MAX_ATTEMPTS) {
        const delay = Math.min(RETRY_BASE_DELAY_MS * attempt, RETRY_MAX_DELAY_MS);
        setBackendStatus('warming');
        retryTimerRef.current = setTimeout(() => fetchGraph(true), delay);
      } else {
        setBackendStatus('error');
      }
    }
  }, [setNodes, setEdges, fitView]);

  useEffect(() => {
    fetchGraph();
    return () => {
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    };
  }, [fetchGraph]);

  const handleGenerateCourse = async () => {
    if (!newCourseTopic.trim()) return;
    if (backendStatus === 'error') {
      alert("Сервер временно недоступен. Попробуйте позже.");
      return;
    }
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
        const error = await res.json();
        alert(`Ошибка: ${error.detail || "Что-то пошло не так"}`);
      }
    } catch {
      const msg = backendStatus === 'warming'
        ? "Сервер ещё не запустился — подождите немного и попробуйте снова."
        : "Ошибка сети. Сервер временно недоступен.";
      alert(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  const onNodeClick = async (_: React.MouseEvent, node: FlowNode) => {
    if (!node.data.isAvailable) return alert("Тема заблокирована!");
    setSelectedTopic(node.data.label);
    setIsAiLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/explain/${encodeURIComponent(node.data.label.replace(' ✅',''))}`);
      const data = await res.json();
      setExplanation(data.explanation);
    } catch {
      setExplanation("Ошибка загрузки текста.");
    } finally {
      setIsAiLoading(false);
    }
  };

  const statusBanner = () => {
    if (backendStatus === 'loading') {
      return (
        <div style={{ position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)', zIndex: 20, background: '#1e293b', color: 'white', padding: '10px 20px', borderRadius: 8, fontSize: 14 }}>
          ⏳ Подключаюсь к серверу...
        </div>
      );
    }
    if (backendStatus === 'warming') {
      return (
        <div style={{ position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)', zIndex: 20, background: '#92400e', color: 'white', padding: '10px 20px', borderRadius: 8, fontSize: 14 }}>
          🔄 Сервер просыпается (Render free tier). Подождите ~30 сек...
        </div>
      );
    }
    if (backendStatus === 'error') {
      return (
        <div style={{ position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)', zIndex: 20, background: '#7f1d1d', color: 'white', padding: '10px 20px', borderRadius: 8, fontSize: 14, cursor: 'pointer' }}
          onClick={() => fetchGraph()}>
          ❌ Сервер недоступен. Нажмите, чтобы повторить попытку
        </div>
      );
    }
    if (backendStatus === 'ok' && !hasNodes) {
      return (
        <div style={{ position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)', zIndex: 20, background: '#1e3a5f', color: 'white', padding: '10px 20px', borderRadius: 8, fontSize: 14 }}>
          ✨ Введите тему выше и нажмите «Создать», чтобы сгенерировать курс!
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#f8f9fa' }}>
      <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 10, background: 'white', padding: 20, borderRadius: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        <div style={{ marginBottom: 8, fontWeight: 600, fontSize: 16, color: '#1e293b' }}>🎓 VYUD LMS</div>
        <input 
          value={newCourseTopic} 
          onChange={(e) => setNewCourseTopic(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleGenerateCourse()}
          placeholder="Тема курса (напр. Python, React...)" 
          style={{ padding: '8px', border: '1px solid #ddd', borderRadius: 6, marginRight: 10, width: 220 }}
        />
        <button
          onClick={handleGenerateCourse}
          disabled={isGenerating || backendStatus === 'loading' || backendStatus === 'warming'}
          style={{ padding: '8px 16px', background: isGenerating ? '#94a3b8' : '#3b82f6', color: 'white', border: 'none', borderRadius: 6, cursor: isGenerating ? 'not-allowed' : 'pointer' }}
        >
          {isGenerating ? "Генерация..." : "Создать"}
        </button>
      </div>
      <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onNodeClick={onNodeClick} fitView>
        <Background />
        <Controls />
      </ReactFlow>
      {statusBanner()}
      {selectedTopic && (
        <div style={{ position: 'absolute', top: 20, right: 20, width: 350, background: 'white', padding: 25, borderRadius: 12, boxShadow: '0 4px 20px rgba(0,0,0,0.15)', zIndex: 100 }}>
          <h3 style={{ marginTop: 0 }}>{selectedTopic}</h3>
          {isAiLoading ? <p>🤖 Пишу урок...</p> : <p>{explanation}</p>}
          <button onClick={() => setSelectedTopic(null)} style={{ width: '100%', padding: 10, background: '#f3f4f6', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Закрыть</button>
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

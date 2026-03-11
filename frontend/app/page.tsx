"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, ReactFlowProvider, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://vyud-lms-backend.onrender.com";

function Flow() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { fitView } = useReactFlow();
  
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [newCourseTopic, setNewCourseTopic] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  const fetchGraph = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/courses/latest`);
      if (!res.ok) return;
      const data = await res.json();
      
      if (data?.nodes?.length > 0) {
        const formattedNodes = data.nodes.map((node: any, idx: number) => ({
          id: String(node.id),
          position: { x: idx * 250, y: (node.level || 1) * 150 },
          data: { label: node.is_completed ? `${node.label} ✅` : node.label, isAvailable: node.is_available },
          style: { 
            background: node.is_completed ? '#4ADE80' : node.is_available ? '#fff' : '#f3f4f6',
            border: node.is_available ? '2px solid #3b82f6' : '2px dashed #ccc',
            borderRadius: '12px', width: 200, padding: '10px', textAlign: 'center'
          }
        }));

        const formattedEdges = data.edges.map((e: any) => ({
          id: `e${e.source}-${e.target}`,
          source: String(e.source),
          target: String(e.target),
          animated: true
        }));

        setNodes(formattedNodes);
        setEdges(formattedEdges);
        setTimeout(() => fitView({ duration: 800 }), 100);
      }
    } catch (err) {
      console.error("Load error:", err);
    }
  }, [setNodes, setEdges, fitView]);

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
        alert("Курс создан!");
        setNewCourseTopic("");
        fetchGraph();
      } else {
        const error = await res.json();
        alert(`Ошибка: ${error.detail || "Что-то пошло не так"}`);
      }
    } catch (e) {
      alert("Ошибка сети. Проверьте Render.");
    } finally {
      setIsGenerating(false);
    }
  };

  const onNodeClick = async (_: any, node: any) => {
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

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#f8f9fa' }}>
      <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 10, background: 'white', padding: 20, borderRadius: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        <input 
          value={newCourseTopic} 
          onChange={(e) => setNewCourseTopic(e.target.value)} 
          placeholder="Тема курса..." 
          style={{ padding: '8px', border: '1px solid #ddd', borderRadius: 6, marginRight: 10 }}
        />
        <button onClick={handleGenerateCourse} disabled={isGenerating} style={{ padding: '8px 16px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
          {isGenerating ? "Генерация..." : "Создать"}
        </button>
      </div>
      <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onNodeClick={onNodeClick} fitView>
        <Background />
        <Controls />
      </ReactFlow>
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

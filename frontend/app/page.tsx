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
  const [explanation, setExplanation] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);

  const onNodeClick = async (event: any, node: any) => {
    if (!node.data?.label) return;

    const topic = node.data.label;
    setSelectedTopic(topic);
    setExplanation(null);
    setIsAiLoading(true);

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/explain/${encodeURIComponent(topic)}`);
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

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/knowledge-graph')
      .then(res => res.json())
      .then(data => {
        console.log("СЫРЫЕ ДАННЫЕ:", data);
        
        if (data && data.nodes && data.nodes.length > 0) {
          const formattedNodes = data.nodes.map((node, index) => {
            const safeY = (node.level || 1) * 150;
            const safeX = index * 250 + 100;
            return {
              id: String(node.id),
              position: { x: safeX, y: safeY },
              data: { label: node.label || "Без названия" },
              style: { background: '#fff', border: '2px solid blue', padding: '15px', borderRadius: '8px', color: '#000' }
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
          width: '300px',
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
          
          {isAiLoading ? (
            <p style={{ color: '#6b7280', fontStyle: 'italic' }}>🤖 Генерирую урок...</p>
          ) : (
            <p style={{ lineHeight: '1.5', fontSize: '14px' }}>{explanation}</p>
          )}
        </div>
      )}
    </div>
  );
}

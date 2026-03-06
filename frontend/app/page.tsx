"use client";

import React, { useEffect, useState } from 'react';
import { ReactFlow, Background, Controls } from '@xyflow/react';
import '@xyflow/react/dist/style.css'; // Тот самый недостающий импорт стилей!

export default function Page() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);

  useEffect(() => {
    // Стучимся в наш FastAPI бэкенд
    fetch('http://127.0.0.1:8000/api/knowledge-graph')
      .then(res => res.json())
      .then(data => {
        console.log("Данные с бэкенда:", data);
        
        // Преобразуем узлы для React Flow (добавляем координаты X и Y)
        const formattedNodes = data.nodes.map((node: any, index: number) => ({
          id: node.id.toString(),
          position: { x: 250 * index + 100, y: node.level * 150 },
          data: { label: node.label },
          style: { border: '1px solid #222', padding: 10, borderRadius: 8, background: '#fff' }
        }));
        
        // Преобразуем связи
        const formattedEdges = data.edges.map((edge: any) => ({
          id: `e${edge.source}-${edge.target}`,
          source: edge.source.toString(),
          target: edge.target.toString(),
          animated: true, // Делаем связи анимированными для красоты
        }));

        setNodes(formattedNodes);
        setEdges(formattedEdges);
      })
      .catch(err => console.error("Ошибка загрузки:", err));
  }, []);

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#f8f9fa' }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
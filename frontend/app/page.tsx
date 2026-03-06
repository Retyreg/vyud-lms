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
    <div style={{ width: '100vw', height: '100vh', background: '#f8f9fa' }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

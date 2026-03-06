"use client";

import { useEffect, useState, useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  Connection,
  addEdge,
} from "reactflow";
import "reactflow/dist/style.css";

interface ApiNode {
  id: number;
  label: string;
  level: number;
}

interface ApiEdge {
  source: number;
  target: number;
}

interface GraphResponse {
  nodes: ApiNode[];
  edges: ApiEdge[];
}

const initialNodes: Node[] = [];
const initialEdges: Edge[] = [];

export default function Home() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/api/knowledge-graph");
        if (!res.ok) {
          throw new Error("Failed to fetch graph data");
        }
        const data: GraphResponse = await res.json();

        // Преобразование узлов API в формат ReactFlow
        // Простой алгоритм расстановки: группируем по уровням (level)
        // position.x = уровень * 250
        // position.y = индекс_в_группе * 100
        const levelCounts: Record<number, number> = {};
        
        const flowNodes: Node[] = data.nodes.map((node) => {
          const lvl = node.level || 1;
          const count = levelCounts[lvl] || 0;
          levelCounts[lvl] = count + 1;

          return {
            id: node.id.toString(),
            data: { label: node.label },
            position: { x: (lvl - 1) * 250, y: count * 100 },
            sourcePosition: "right" as any,
            targetPosition: "left" as any,
          };
        });

        // Преобразование ребер API в формат ReactFlow
        const flowEdges: Edge[] = data.edges.map((edge) => ({
          id: `e${edge.source}-${edge.target}`,
          source: edge.source.toString(),
          target: edge.target.toString(),
          animated: true,
        }));

        setNodes(flowNodes);
        setEdges(flowEdges);
      } catch (error) {
        console.error("Error fetching knowledge graph:", error);
      }
    };

    fetchGraph();
  }, [setNodes, setEdges]);

  return (
    <div className="h-screen w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

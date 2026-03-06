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
  const [loading, setLoading] = useState(true);

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
        console.log("Fetched data:", data);

        // Преобразование узлов API в формат ReactFlow
        // position.x = index * 200 (чтобы не накладывались по горизонтали)
        // position.y = level * 100 (уровни по вертикали)
        const flowNodes: Node[] = data.nodes.map((node, index) => {
          return {
            id: node.id.toString(),
            data: { label: node.label },
            position: { x: index * 200, y: (node.level || 1) * 100 },
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

        console.log("Nodes:", flowNodes);
        setNodes(flowNodes);
        setEdges(flowEdges);
      } catch (error) {
        console.error("Error fetching knowledge graph:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchGraph();
  }, [setNodes, setEdges]);

  if (loading) {
    return <div className="flex h-screen w-full items-center justify-center">Загрузка графа...</div>;
  }

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

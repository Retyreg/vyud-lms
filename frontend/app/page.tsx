import { ReactFlowProvider } from '@xyflow/react';
import { KnowledgeGraph } from '@/components/graph/KnowledgeGraph';

export default function Page() {
  return (
    <ReactFlowProvider>
      <KnowledgeGraph />
    </ReactFlowProvider>
  );
}

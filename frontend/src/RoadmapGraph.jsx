import { useCallback, useMemo } from "react";
import { Background, Controls, Position, ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const IMPORTANCE_COLOR = {
  CRITICAL: "#22d3ee",
  IMPORTANT: "#a78bfa",
  OPTIONAL: "#8992b3",
};

const HORIZONTAL_GAP = 210;
const VERTICAL_GAP = 110;

/**
 * Layout phân tầng đơn giản (không cần dagre/elkjs): level(node) = 0 nếu không có
 * khái niệm tiên quyết (không có cạnh trỏ vào), ngược lại = 1 + max(level của các
 * tiên quyết). Cùng 1 level xếp ngang, căn giữa theo level rộng nhất -- cho ra đúng
 * hiệu ứng "chảy từ trên xuống, phân nhánh" kiểu roadmap.sh.
 */
function computeLayout(roadmap, edges) {
  const nodeIds = roadmap.map((n) => n.node_id);
  const incoming = Object.fromEntries(nodeIds.map((id) => [id, []]));
  for (const e of edges) {
    if (incoming[e.target]) incoming[e.target].push(e.source);
  }

  const level = {};
  function levelOf(id, seen) {
    if (level[id] !== undefined) return level[id];
    if (seen.has(id)) return 0; // cạnh lạ tạo vòng lặp -- không nên xảy ra (backend đã phá cycle), an toàn thoát
    seen.add(id);
    const preds = (incoming[id] || []).filter((p) => nodeIds.includes(p));
    const lvl = preds.length === 0 ? 0 : 1 + Math.max(...preds.map((p) => levelOf(p, seen)));
    level[id] = lvl;
    return lvl;
  }
  nodeIds.forEach((id) => levelOf(id, new Set()));

  const byLevel = {};
  nodeIds.forEach((id) => {
    const lvl = level[id];
    (byLevel[lvl] ??= []).push(id);
  });

  const maxCount = Math.max(1, ...Object.values(byLevel).map((a) => a.length));
  const positions = {};
  Object.entries(byLevel).forEach(([lvl, ids]) => {
    const totalWidth = maxCount * HORIZONTAL_GAP;
    const startX = (totalWidth - ids.length * HORIZONTAL_GAP) / 2;
    ids.forEach((id, i) => {
      positions[id] = { x: startX + i * HORIZONTAL_GAP, y: Number(lvl) * VERTICAL_GAP };
    });
  });

  return positions;
}

export default function RoadmapGraph({ roadmap, edges, onNodeSelect }) {
  const positions = useMemo(() => computeLayout(roadmap, edges), [roadmap, edges]);

  const nodes = useMemo(
    () =>
      roadmap.map((n) => {
        const color = IMPORTANCE_COLOR[n.importance] || IMPORTANCE_COLOR.OPTIONAL;
        return {
          id: n.node_id,
          position: positions[n.node_id] || { x: 0, y: 0 },
          data: { label: n.title },
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
          style: {
            background: "#10152a",
            color: "#e6e9f5",
            border: `1.5px solid ${color}`,
            borderRadius: 10,
            padding: "10px 14px",
            fontFamily: "'Space Grotesk', sans-serif",
            fontSize: 13,
            fontWeight: 600,
            width: 188,
            textAlign: "center",
            boxShadow: `0 0 14px ${color}33`,
            cursor: "pointer",
          },
        };
      }),
    [roadmap, positions]
  );

  const flowEdges = useMemo(
    () =>
      edges.map((e, i) => ({
        id: `e-${i}-${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        animated: true,
        style: { stroke: "#a78bfa", strokeWidth: 1.5 },
      })),
    [edges]
  );

  const handleNodeClick = useCallback(
    (_event, node) => {
      const roadmapNode = roadmap.find((n) => n.node_id === node.id);
      const citation = roadmapNode?.citations?.[0];
      if (citation) onNodeSelect(citation);
    },
    [roadmap, onNodeSelect]
  );

  if (roadmap.length === 0) return null;

  const maxY = Math.max(0, ...Object.values(positions).map((p) => p.y));
  const height = Math.max(220, maxY + VERTICAL_GAP + 80);

  return (
    <div className="roadmap-graph" style={{ height }}>
      <ReactFlow
        nodes={nodes}
        edges={flowEdges}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        nodesDraggable={false}
        nodesConnectable={false}
        colorMode="dark"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#22314f" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

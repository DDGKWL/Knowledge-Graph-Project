/**
 * 将二跳 highlightPath 拆成两段「链块」（每段 2 节点 1 关系），供证据合成台拼接。
 */
export function splitHighlightPathIntoSegments(highlightPath, resolveNode) {
  const ids = (highlightPath?.nodeIds || []).map((id) => String(id));
  const edges = highlightPath?.edges || [];
  if (ids.length < 3 || edges.length < 2) return [];

  const [rootId, midId, candId] = ids;
  const rel0 = edges[0]?.relation || edges[0]?.label || "关联";
  const rel1 = edges[1]?.relation || edges[1]?.label || "关联";

  const buildSeg = (sourceId, targetId, relation) => {
    const a = resolveNode(sourceId);
    const b = resolveNode(targetId);
    return {
      sourceNodeId: sourceId,
      targetNodeId: targetId,
      relation,
      stripNodes: [
        { label: a.label, artifact: a.artifact, id: sourceId },
        { label: b.label, artifact: b.artifact, id: targetId },
      ],
      stripRels: [relation],
      highlightPath: {
        nodeIds: [sourceId, targetId],
        edges: [{ source: sourceId, target: targetId, relation }],
      },
      ariaLabel: `${a.fullName} 经「${relation}」到 ${b.fullName}`,
    };
  };

  return [
    buildSeg(rootId, midId, rel0),
    buildSeg(midId, candId, rel1),
  ];
}

/** 上一段终点是否等于下一段起点（可拼接） */
export function segmentsCanSplice(prev, next) {
  if (!prev || !next) return true;
  return String(prev.targetNodeId) === String(next.sourceNodeId);
}

export function createSegmentId() {
  return `seg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

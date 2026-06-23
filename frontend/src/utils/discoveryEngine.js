const toId = (value) => String(value);

/** 单模式下列表过长时截断，避免 DOM 过大 */
const MAX_EXTENSION_ROWS = 80;

function buildAdjacency(fullData) {
  const adjacency = new Map();
  fullData.nodes.forEach((node) => adjacency.set(toId(node.id), []));
  fullData.links.forEach((link) => {
    const sourceId = toId(link.source?.id ?? link.source);
    const targetId = toId(link.target?.id ?? link.target);
    const relation = link.relation || link.label || "关联";
    if (adjacency.has(sourceId)) adjacency.get(sourceId).push({ to: targetId, relation });
    if (adjacency.has(targetId)) adjacency.get(targetId).push({ to: sourceId, relation });
  });
  return adjacency;
}

function nodeName(fullData, id) {
  const node = fullData.nodes.find((item) => toId(item.id) === toId(id));
  return node?.name || toId(id);
}

function nodeById(fullData, id) {
  return fullData.nodes.find((item) => toId(item.id) === toId(id));
}

/**
 * 发现视图：二跳扩展候选 + 解释链 + 知识缺口提示。
 * 规则：合并同一候选节点；过滤「同关系连两次」弱路径；二跳终点仅保留非文物。
 * highlightPath：供主图高亮（根—中间—候选）代表路径。
 */
export function buildDiscoveryView(selectedArtifactId, fullData) {
  if (!selectedArtifactId || !fullData?.nodes?.length) {
    return {
      extensionCandidates: [],
      explanationChains: [],
      knowledgeOpportunities: [],
      discoveryMeta: { totalMerged: 0, shown: 0, truncated: false },
    };
  }

  const rootId = toId(selectedArtifactId);
  const adjacency = buildAdjacency(fullData);
  const oneHop = adjacency.get(rootId) || [];
  const directTargetIds = new Set(oneHop.map((edge) => edge.to));

  /** candidateId -> 聚合 */
  const merged = new Map();

  oneHop.forEach((edge1) => {
    const midId = toId(edge1.to);
    const secondHop = adjacency.get(midId) || [];
    secondHop.forEach((edge2) => {
      const candId = toId(edge2.to);
      if (candId === rootId || directTargetIds.has(candId)) return;

      if (edge1.relation === edge2.relation) return;

      const candNode = nodeById(fullData, candId);
      if (Number(candNode?.is_artifact) === 1) return;

      const reasonPair = `${edge1.relation} → ${edge2.relation}`;
      const pathText = `${nodeName(fullData, rootId)} → ${edge1.relation} → ${nodeName(fullData, midId)} → ${edge2.relation} → ${nodeName(fullData, candId)}`;

      const pathRecord = {
        rootId,
        midId,
        candId,
        rel1: edge1.relation,
        rel2: edge2.relation,
        pathText,
      };

      let bucket = merged.get(candId);
      if (!bucket) {
        bucket = {
          candidateNodeId: candId,
          candidateNodeName: nodeName(fullData, candId),
          reasonPairs: new Set(),
          pathRecords: [],
        };
        merged.set(candId, bucket);
      }
      bucket.reasonPairs.add(reasonPair);
      bucket.pathRecords.push(pathRecord);
    });
  });

  const rows = [...merged.values()].map((bucket) => {
    const reasons = [...bucket.reasonPairs].sort((a, b) => a.localeCompare(b, "zh-Hans-CN"));
    const reps = bucket.pathRecords;
    const representative = reps.reduce(
      (best, cur) => (cur.pathText.length < best.pathText.length ? cur : best),
      reps[0]
    );
    const variantCount = reps.length;

    const highlightPath = {
      nodeIds: [representative.rootId, representative.midId, representative.candId],
      edges: [
        { source: representative.rootId, target: representative.midId, relation: representative.rel1 },
        { source: representative.midId, target: representative.candId, relation: representative.rel2 },
      ],
    };

    return {
      key: bucket.candidateNodeId,
      candidateNodeId: bucket.candidateNodeId,
      candidateNodeName: bucket.candidateNodeName,
      reason: reasons.join(" · "),
      pathVariantCount: variantCount,
      reasonVariantCount: reasons.length,
      representativePath: representative.pathText,
      highlightPath,
    };
  });

  rows.sort((a, b) => String(a.candidateNodeName).localeCompare(String(b.candidateNodeName), "zh-Hans-CN"));

  const sliced = rows.slice(0, MAX_EXTENSION_ROWS);

  const extensionCandidates = sliced.map((row) => ({
    key: row.key,
    candidateNodeId: row.candidateNodeId,
    candidateNodeName: row.candidateNodeName,
    reason: row.reason,
    pathVariantCount: row.pathVariantCount,
    reasonVariantCount: row.reasonVariantCount,
    highlightPath: row.highlightPath,
  }));

  const explanationChains = sliced.map((row) => {
    let pathText = row.representativePath;
    if (row.pathVariantCount > 1) {
      pathText += ` （合并自 ${row.pathVariantCount} 条二跳路径`;
      if (row.reasonVariantCount > 1) {
        pathText += `，${row.reasonVariantCount} 种关系组合`;
      }
      pathText += "）";
    }
    return { pathText };
  });

  const expectedRelations = ["包含组件", "时代", "材质", "用途", "工艺"];
  const existingRelations = new Set(oneHop.map((edge) => edge.relation));
  const missingExpected = expectedRelations.filter((relation) => !existingRelations.has(relation));
  const knowledgeOpportunities = missingExpected.map((relation) => ({
    title: `建议补全“${relation}”信息`,
    detail: `当前文物缺少 ${relation} 相关关联，可作为优先研究切入点。`,
  }));

  return {
    extensionCandidates,
    explanationChains,
    knowledgeOpportunities,
    discoveryMeta: {
      totalMerged: merged.size,
      shown: sliced.length,
      truncated: rows.length > MAX_EXTENSION_ROWS,
    },
  };
}

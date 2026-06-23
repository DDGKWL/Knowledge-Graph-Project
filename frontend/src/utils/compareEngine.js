import { COMPARE_CONFLICT_RELATION_PATTERN } from "./graphConfig";
import { buildDiscoveryView } from "./discoveryEngine";

const toId = (value) => String(value);

function buildNodeLookup(fullData) {
  const nameMap = new Map();
  const nodeMap = new Map();
  (fullData.nodes || []).forEach((node) => {
    const id = toId(node.id);
    nameMap.set(id, node.name || id);
    nodeMap.set(id, node);
  });
  return { nameMap, nodeMap };
}

function nodeDescription(nodeMap, nodeId) {
  const node = nodeMap.get(toId(nodeId));
  return String(node?.description || "").trim();
}

function nodeBook(nodeMap, nodeId) {
  const node = nodeMap.get(toId(nodeId));
  return String(node?.book || node?.belongs_to || node?.belongsTo || "").trim();
}

function evidenceSide(artifactId, artifactName, relation, targetId, targetName, nodeMap, present = true) {
  return {
    artifact_id: artifactId,
    artifact_name: artifactName,
    book: nodeBook(nodeMap, artifactId) || nodeBook(nodeMap, targetId),
    relation,
    target_id: targetId || "",
    target_name: targetName || "",
    description: targetId ? nodeDescription(nodeMap, targetId) : "",
    present,
  };
}

function attachDiffEvidence(item, artifactIds, neighborMap, nameMap, nodeMap) {
  const relation = item.relation;
  const sides = [];
  artifactIds.forEach((aid) => {
    const entries = (neighborMap.get(aid) || []).filter((p) => p.relation === relation);
    const artName = nameMap.get(aid) || aid;
    if (entries.length) {
      entries.forEach(({ relation: r, targetId }) => {
        sides.push(
          evidenceSide(
            aid,
            artName,
            r,
            targetId,
            nameMap.get(targetId) || targetId,
            nodeMap,
            true
          )
        );
      });
    } else {
      sides.push(evidenceSide(aid, artName, relation, "", "", nodeMap, false));
    }
  });
  item.evidence = {
    kind: "compare-diff",
    claim: `关系「${relation}」指向不同实体：${(item.values || []).join(" / ")}`,
    sides,
  };
}

function attachMissingEvidence(miss, artifactId, artifactName, nodeMap) {
  const { relation, targetId, targetName } = miss;
  miss.evidence = {
    kind: "compare-missing",
    claim: `${artifactName} 缺少 ${relation} → ${targetName}`,
    sides: [
      evidenceSide(artifactId, artifactName, relation, "", targetName, nodeMap, false),
      {
        artifact_id: "",
        artifact_name: "参照节点",
        book: nodeBook(nodeMap, targetId),
        relation,
        target_id: targetId,
        target_name: targetName,
        description: nodeDescription(nodeMap, targetId),
        present: true,
      },
    ],
  };
}

function attachConflictEvidence(item, artifactIds, neighborMap, nameMap, nodeMap) {
  attachDiffEvidence(item, artifactIds, neighborMap, nameMap, nodeMap);
  item.evidence.kind = "compare-conflict";
  item.evidence.claim = item.detail || item.evidence.claim;
}

function buildNeighborMap(fullData, artifactIds) {
  const map = new Map();
  artifactIds.forEach((id) => map.set(id, []));

  fullData.links.forEach((link) => {
    const sourceId = toId(link.source?.id ?? link.source);
    const targetId = toId(link.target?.id ?? link.target);
    const relation = link.relation || link.label || "关联";

    if (map.has(sourceId)) map.get(sourceId).push({ relation, targetId });
    if (map.has(targetId)) map.get(targetId).push({ relation, targetId: sourceId });
  });
  return map;
}

export function buildCompareView(compareArtifacts, fullData) {
  if (!compareArtifacts?.length || !fullData?.nodes?.length) {
    return {
      sharedStructures: [],
      differenceStructures: [],
      missingStructures: [],
      conflictStructures: [],
      numericComparison: [],
      meta: { ready: false, reason: "no_data" },
    };
  }

  if (compareArtifacts.length < 2) {
    return {
      sharedStructures: [],
      differenceStructures: [],
      missingStructures: [],
      conflictStructures: [],
      numericComparison: [],
      meta: { ready: false, reason: "need_two_artifacts" },
    };
  }

  const artifactIds = compareArtifacts.map((item) => toId(item.id));
  const neighborMap = buildNeighborMap(fullData, artifactIds);
  const { nameMap, nodeMap } = buildNodeLookup(fullData);
  const nodeNameMap = nameMap;

  const perArtifactPairs = artifactIds.map((id) => {
    const pairs = neighborMap.get(id) || [];
    return new Set(pairs.map((pair) => `${pair.relation}::${pair.targetId}`));
  });

  const sharedKeys = [...perArtifactPairs[0]].filter((key) =>
    perArtifactPairs.every((set) => set.has(key))
  );

  const sharedStructures = sharedKeys.map((key) => {
    const [relation, targetId] = key.split("::");
    return { relation, targetName: nodeNameMap.get(targetId) || targetId };
  });

  const relationValueMap = new Map();
  artifactIds.forEach((id) => {
    (neighborMap.get(id) || []).forEach(({ relation, targetId }) => {
      if (!relationValueMap.has(relation)) relationValueMap.set(relation, new Set());
      relationValueMap.get(relation).add(targetId);
    });
  });

  const differenceStructures = [...relationValueMap.entries()]
    .filter(([, values]) => values.size > 1)
    .map(([relation, valueSet]) => {
      const targetIds = [...valueSet];
      const nodeIds = new Set(artifactIds);
      targetIds.forEach((tid) => nodeIds.add(tid));
      const edges = [];
      artifactIds.forEach((aid) => {
        (neighborMap.get(aid) || []).forEach(({ relation: r, targetId }) => {
          if (r === relation && valueSet.has(targetId)) {
            edges.push({ source: aid, target: targetId, relation: r });
          }
        });
      });
      return {
        key: `diff-${relation}`,
        relation,
        values: targetIds.map((id) => nodeNameMap.get(id) || id),
        highlightPath: {
          nodeIds: [...nodeIds],
          edges,
        },
      };
    });

  const unionKeys = new Set();
  perArtifactPairs.forEach((set) => set.forEach((key) => unionKeys.add(key)));

  const missingStructures = compareArtifacts.map((artifact) => {
    const artifactId = toId(artifact.id);
    const hasSet = perArtifactPairs[artifactIds.indexOf(artifactId)];
    const missing = [...unionKeys]
      .filter((key) => !hasSet.has(key))
      .map((key) => {
        const [relation, targetId] = key.split("::");
        const targetName = nodeNameMap.get(targetId) || targetId;
        return {
          key: `miss-${artifactId}-${relation}-${targetId}`,
          relation,
          targetId,
          targetName,
          label: `${relation} → ${targetName}`,
          highlightPath: {
            nodeIds: [artifactId, targetId],
            edges: [{ source: artifactId, target: targetId, relation }],
          },
        };
      });
    return {
      artifactId,
      artifactName: artifact.name,
      missing,
      total: missing.length,
    };
  });

  const conflictStructures = differenceStructures
    .filter((item) => COMPARE_CONFLICT_RELATION_PATTERN.test(item.relation))
    .map((item) => ({
      key: `conflict-${item.relation}`,
      relation: item.relation,
      detail: `候选值不一致：${item.values.join(" / ")}`,
      highlightPath: item.highlightPath,
    }));

  differenceStructures.forEach((item) =>
    attachDiffEvidence(item, artifactIds, neighborMap, nodeNameMap, nodeMap)
  );
  missingStructures.forEach((row) => {
    row.missing.forEach((miss) =>
      attachMissingEvidence(miss, row.artifactId, row.artifactName, nodeMap)
    );
  });
  conflictStructures.forEach((item) => {
    const diffSource = differenceStructures.find((d) => d.relation === item.relation);
    if (diffSource?.evidence) {
      item.evidence = {
        ...diffSource.evidence,
        kind: "compare-conflict",
        claim: item.detail || diffSource.evidence.claim,
      };
    } else {
      attachConflictEvidence(item, artifactIds, neighborMap, nodeNameMap, nodeMap);
    }
  });

  const numericComparison = compareArtifacts.map((artifact) => {
    const artifactId = toId(artifact.id);
    const discovery = buildDiscoveryView(artifactId, fullData);
    const fromGraph = discovery.extensionCandidates?.length ?? 0;
    return {
      artifactId,
      artifactName: artifact.name,
      candidateCount: fromGraph,
      legacyCount: Number(artifact.candidateCount || 0),
    };
  });

  return {
    sharedStructures,
    differenceStructures,
    missingStructures,
    conflictStructures,
    numericComparison,
    meta: { ready: true, reason: "" },
  };
}

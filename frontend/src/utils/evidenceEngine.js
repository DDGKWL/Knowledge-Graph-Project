/**
 * 比较差异 / 缺失 / 冲突 → 可解释证据项；发现模式链块元数据补全。
 */

export function lookupNode(nodes, id) {
  if (!id) return null;
  return (nodes || []).find((n) => String(n.id) === String(id)) || null;
}

export function nodeMeta(node) {
  if (!node) return { book: "", description: "", name: "" };
  const book = String(node.book || node.belongs_to || node.belongsTo || "").trim();
  const description = String(node.description || "").trim();
  return {
    book,
    description,
    name: String(node.name || node.label || "").trim(),
  };
}

export function truncateText(text, max = 120) {
  if (text == null) return "";
  const s = String(text).trim();
  if (!s) return "";
  return s.length <= max ? s : `${s.slice(0, Math.max(1, max - 1))}…`;
}

export function createEvidenceId() {
  return `ev-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function compareKindLabel(kind) {
  if (kind === "compare-diff") return "差异";
  if (kind === "compare-missing") return "缺失";
  if (kind === "compare-conflict") return "冲突";
  return "线索";
}

function mapBackendSide(side) {
  return {
    artifactId: String(side.artifact_id || side.artifactId || ""),
    artifactName: side.artifact_name || side.artifactName || "",
    book: side.book || "",
    relation: side.relation || "",
    targetId: String(side.target_id || side.targetId || ""),
    targetName: side.target_name || side.targetName || "",
    description: side.description || "",
    present: side.present !== false,
  };
}

function sideFromEntry(artifactId, artifactName, entry, graphNodes, present = true) {
  const targetId = entry?.target_id || entry?.targetId || "";
  const targetName = entry?.target_name || entry?.targetName || "";
  const relation = entry?.relation || "";
  const targetNode = lookupNode(graphNodes, targetId);
  const artNode = lookupNode(graphNodes, artifactId);
  const targetMeta = nodeMeta(targetNode);
  const artMeta = nodeMeta(artNode);
  return {
    artifactId: String(artifactId),
    artifactName: artifactName || artMeta.name || String(artifactId),
    book: artMeta.book || targetMeta.book,
    relation,
    targetId: String(targetId),
    targetName: targetName || targetMeta.name,
    description: targetMeta.description,
    present,
  };
}

function buildStripFromHighlightPath(highlightPath, graphNodes) {
  const ids = (highlightPath?.nodeIds || []).map((id) => String(id));
  const edges = highlightPath?.edges || [];
  if (ids.length < 2) return { stripNodes: [], stripRels: [], ariaLabel: "" };

  const stripNodes = [];
  const stripRels = [];
  const names = [];

  ids.forEach((id, i) => {
    const node = lookupNode(graphNodes, id);
    const name = nodeMeta(node).name || id;
    names.push(name);
    stripNodes.push({
      id,
      label: name.length > 10 ? `${name.slice(0, 9)}…` : name,
      artifact: Number(node?.is_artifact) === 1,
    });
    if (i < ids.length - 1) {
      const rel = edges[i]?.relation || edges[i]?.label || "关联";
      stripRels.push(rel.length > 9 ? `${rel.slice(0, 8)}…` : rel);
    }
  });

  let ariaLabel = names.join(" → ");
  if (edges.length && names.length >= 2) {
    ariaLabel = `${names[0]} 经「${edges[0]?.relation || "关联"}」到 ${names[1]}`;
    if (names.length >= 3 && edges[1]) {
      ariaLabel += `，再经「${edges[1]?.relation || "关联"}」到 ${names[2]}`;
    }
  }

  return { stripNodes, stripRels, ariaLabel };
}

function buildDiffEvidenceClient(item, compareArtifacts, graphNodes) {
  const relation = item.relation;
  const sides = [];
  (compareArtifacts || []).forEach((art) => {
    const aid = String(art.id);
    const artNode = lookupNode(graphNodes, aid);
    const artName = art.name || nodeMeta(artNode).name || aid;
    const hp = item.highlightPath;
    const edge = (hp?.edges || []).find((e) => String(e.source) === aid);
    if (edge) {
      sides.push(
        sideFromEntry(
          aid,
          artName,
          { relation, targetId: edge.target, targetName: item.values?.find((_, i) => true) },
          graphNodes,
          true
        )
      );
      const tid = String(edge.target);
      const tnode = lookupNode(graphNodes, tid);
      sides[sides.length - 1].targetName = nodeMeta(tnode).name || tid;
      sides[sides.length - 1].description = nodeMeta(tnode).description;
    }
  });

  // Rebuild sides properly from edges
  const rebuilt = [];
  (compareArtifacts || []).forEach((art) => {
    const aid = String(art.id);
    const artName = art.name || nodeMeta(lookupNode(graphNodes, aid)).name || aid;
    const edges = (item.highlightPath?.edges || []).filter((e) => String(e.source) === aid);
    if (edges.length) {
      edges.forEach((e) => {
        rebuilt.push(
          sideFromEntry(
            aid,
            artName,
            { relation: e.relation || relation, targetId: e.target, targetName: "" },
            graphNodes,
            true
          )
        );
      });
    } else {
      rebuilt.push({
        artifactId: aid,
        artifactName: artName,
        book: nodeMeta(lookupNode(graphNodes, aid)).book,
        relation,
        targetId: "",
        targetName: "—",
        description: "",
        present: false,
      });
    }
  });

  const values = (item.values || []).join(" / ");
  return {
    kind: "compare-diff",
    claim: `关系「${relation}」指向不同实体：${values}`,
    sides: rebuilt,
  };
}

function buildMissingEvidenceClient(item, row, graphNodes) {
  const artifactId = String(row?.artifactId || item.artifactId || "");
  const artifactName =
    row?.artifactName ||
    item.artifactName ||
    nodeMeta(lookupNode(graphNodes, artifactId)).name ||
    artifactId;
  const targetId = String(item.targetId || item.highlightPath?.nodeIds?.[1] || "");
  const relation = item.relation || "关联";
  const targetName =
    item.targetName || nodeMeta(lookupNode(graphNodes, targetId)).name || targetId;

  const sides = [
    {
      artifactId,
      artifactName,
      book: nodeMeta(lookupNode(graphNodes, artifactId)).book,
      relation,
      targetId: "",
      targetName,
      description: "",
      present: false,
    },
    {
      artifactId: "",
      artifactName: "参照节点",
      book: nodeMeta(lookupNode(graphNodes, targetId)).book,
      relation,
      targetId,
      targetName,
      description: nodeMeta(lookupNode(graphNodes, targetId)).description,
      present: true,
    },
  ];

  return {
    kind: "compare-missing",
    claim: `${artifactName} 缺少 ${relation} → ${targetName}`,
    sides,
  };
}

function evidenceTitle(kind, item) {
  if (kind === "compare-missing") return item.label || item.relation || "缺失结构";
  if (kind === "compare-conflict") return `[${item.relation}] 冲突`;
  return `[${item.relation}] 差异`;
}

export function buildCompareEvidenceItem({
  kind,
  item,
  compareArtifacts = [],
  graphNodes = [],
  isCrossBook = false,
  missingRow = null,
}) {
  const key = String(item.key || "");
  const hp = item.highlightPath;
  const dhp = item.displayHighlightPath;

  let payload = item.evidence;
  if (payload && payload.sides) {
    payload = {
      kind: payload.kind || kind,
      claim: payload.claim || "",
      sides: payload.sides.map(mapBackendSide),
    };
  } else if (kind === "compare-diff") {
    payload = buildDiffEvidenceClient(item, compareArtifacts, graphNodes);
  } else if (kind === "compare-missing") {
    payload = buildMissingEvidenceClient(item, missingRow, graphNodes);
  } else if (kind === "compare-conflict") {
    const diffPayload = buildDiffEvidenceClient(item, compareArtifacts, graphNodes);
    payload = {
      kind: "compare-conflict",
      claim: item.detail || diffPayload.claim,
      sides: diffPayload.sides,
    };
  } else {
    payload = { kind, claim: "", sides: [] };
  }

  const highlightPath = hp || null;
  const displayHighlightPath = isCrossBook ? dhp || hp : hp;
  const strip = buildStripFromHighlightPath(displayHighlightPath || highlightPath, graphNodes);

  return {
    id: createEvidenceId(),
    kind: payload.kind || kind,
    sourceKey: key,
    title: evidenceTitle(kind, item),
    claim: payload.claim,
    sides: payload.sides || [],
    highlightPath,
    displayHighlightPath,
    stripNodes: strip.stripNodes,
    stripRels: strip.stripRels,
    ariaLabel: strip.ariaLabel || payload.claim,
    spliceOk: true,
  };
}

export function enrichDiscoverySegment(segment, graphNodes) {
  const sourceNode = lookupNode(graphNodes, segment.sourceNodeId);
  const targetNode = lookupNode(graphNodes, segment.targetNodeId);
  const sourceMeta = nodeMeta(sourceNode);
  const targetMeta = nodeMeta(targetNode);
  return {
    ...segment,
    kind: segment.kind || "discovery",
    sourceDescription: sourceMeta.description,
    targetDescription: targetMeta.description,
    sourceBook: sourceMeta.book,
    targetBook: targetMeta.book,
  };
}

/** 图谱布局：力导向 / 径向 / 层次 / 按书目分列 */

function buildAdjacency(links) {
  const adj = new Map();
  const add = (a, b) => {
    if (!adj.has(a)) adj.set(a, new Set());
    adj.get(a).add(b);
  };
  (links || []).forEach((l) => {
    const s = String(l.source?.id ?? l.source);
    const t = String(l.target?.id ?? l.target);
    if (!s || !t) return;
    add(s, t);
    add(t, s);
  });
  return adj;
}

function computeDegreeMap(links) {
  const deg = new Map();
  (links || []).forEach((l) => {
    const s = String(l.source?.id ?? l.source);
    const t = String(l.target?.id ?? l.target);
    deg.set(s, (deg.get(s) || 0) + 1);
    deg.set(t, (deg.get(t) || 0) + 1);
  });
  return deg;
}

function bfsLevels(nodes, links, centerId) {
  const adj = buildAdjacency(links);
  const levels = new Map();
  const queue = [centerId];
  levels.set(centerId, 0);
  while (queue.length) {
    const cur = queue.shift();
    const nextLevel = levels.get(cur) + 1;
    for (const nb of adj.get(cur) || []) {
      if (!levels.has(nb)) {
        levels.set(nb, nextLevel);
        queue.push(nb);
      }
    }
  }
  nodes.forEach((n) => {
    const id = String(n.id);
    if (!levels.has(id)) levels.set(id, 99);
  });
  return levels;
}

function pickCenterNode(nodes, links) {
  const artifacts = nodes.filter((n) => Number(n.is_artifact) === 1);
  if (artifacts.length === 1) return String(artifacts[0].id);
  const deg = computeDegreeMap(links);
  let best = nodes[0];
  let bestScore = -1;
  nodes.forEach((n) => {
    const id = String(n.id);
    const score = (deg.get(id) || 0) + (Number(n.is_artifact) === 1 ? 5 : 0);
    if (score > bestScore) {
      bestScore = score;
      best = n;
    }
  });
  return String(best?.id);
}

export function applyRadialLayout(nodes, links, width, height) {
  if (!nodes?.length) return;
  const centerId = pickCenterNode(nodes, links);
  const levels = bfsLevels(nodes, links, centerId);
  const byLevel = new Map();
  nodes.forEach((n) => {
    const lv = levels.get(String(n.id)) ?? 0;
    if (!byLevel.has(lv)) byLevel.set(lv, []);
    byLevel.get(lv).push(n);
  });
  const cx = width / 2;
  const cy = height / 2;
  const maxLevel = Math.max(...[...byLevel.keys()], 1);
  const maxR = Math.min(width, height) * 0.42;

  byLevel.forEach((group, level) => {
    if (level === 0) {
      group.forEach((n) => {
        n.fx = cx;
        n.fy = cy;
      });
      return;
    }
    const r = (level / maxLevel) * maxR;
    const gap = (2 * Math.PI) / Math.max(group.length, 1);
    group.forEach((n, i) => {
      const angle = i * gap - Math.PI / 2;
      n.fx = cx + r * Math.cos(angle);
      n.fy = cy + r * Math.sin(angle);
    });
  });
}

export function applyHierarchicalLayout(nodes, links, width, height) {
  if (!nodes?.length) return;
  const centerId = pickCenterNode(nodes, links);
  const levels = bfsLevels(nodes, links, centerId);
  const byLevel = new Map();
  nodes.forEach((n) => {
    const lv = Math.min(levels.get(String(n.id)) ?? 0, 6);
    if (!byLevel.has(lv)) byLevel.set(lv, []);
    byLevel.get(lv).push(n);
  });
  const padY = 48;
  const rowH = Math.max(56, (height - padY * 2) / Math.max(byLevel.size, 1));

  [...byLevel.entries()]
    .sort((a, b) => a[0] - b[0])
    .forEach(([level, group]) => {
      const y = padY + level * rowH;
      const gap = width / (group.length + 1);
      group.forEach((n, i) => {
        n.fx = gap * (i + 1);
        n.fy = y;
      });
    });
}

export function applyBookClusterLayout(nodes, width, height) {
  if (!nodes?.length) return;
  const books = [...new Set(nodes.map((n) => String(n.book || "").trim().toLowerCase()).filter(Boolean))];
  if (books.length < 2) return false;

  const colW = width / books.length;
  books.forEach((book, bi) => {
    const group = nodes.filter((n) => String(n.book || "").trim().toLowerCase() === book);
    const cx = colW * bi + colW / 2;
    const gap = Math.min(42, (height - 80) / Math.max(group.length, 1));
    const block = group.length * gap;
    let startY = (height - block) / 2 + gap / 2;
    group.forEach((n, i) => {
      n.fx = cx;
      n.fy = startY + i * gap;
    });
  });
  return true;
}

export function clearFixedPositions(nodes) {
  (nodes || []).forEach((n) => {
    n.fx = null;
    n.fy = null;
  });
}

export function applyGraphLayout(mode, nodes, links, width, height, { compareAlign = false } = {}) {
  clearFixedPositions(nodes);
  if (compareAlign) return mode;
  switch (mode) {
    case "radial":
      applyRadialLayout(nodes, links, width, height);
      return mode;
    case "hierarchical":
      applyHierarchicalLayout(nodes, links, width, height);
      return mode;
    case "book":
      if (applyBookClusterLayout(nodes, width, height)) return mode;
      return "force";
    default:
      return "force";
  }
}

export { computeDegreeMap };

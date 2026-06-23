/** 部件对照视图辅助 */

export const DIFF_KIND_LABELS = {
  S: "共享",
  V: "校勘",
  A: "增量",
  M: "缺失",
  G: "粒度",
  I: "诠释",
};

export const DIFF_KIND_CLASS = {
  S: "diff-s",
  V: "diff-v",
  A: "diff-a",
  M: "diff-m",
  G: "diff-g",
  I: "diff-i",
};

export function diffKindLabel(kind, customLabels = {}) {
  const key = String(kind || "").toUpperCase();
  return customLabels[key] || DIFF_KIND_LABELS[key] || key || "—";
}

export function truncateCell(value, max = 80) {
  if (value == null || value === "") return "—";
  const text = String(value).trim();
  if (!text) return "—";
  return text.length <= max ? text : `${text.slice(0, Math.max(1, max - 1))}…`;
}

export function artifactColumnLabel(artifact, availableBooks = []) {
  const name = artifact?.name || artifact?.id || "";
  const bookLabel = artifact?.book_label || artifact?.book || "";
  if (bookLabel) return `${name} · ${bookLabel}`;
  return name;
}

export function filterPartRows(rows, { diffKindFilter = "all", partFilter = "", layerFilter = "" } = {}) {
  let list = rows || [];
  if (diffKindFilter && diffKindFilter !== "all") {
    list = list.filter((row) => String(row.diff_kind).toUpperCase() === String(diffKindFilter).toUpperCase());
  }
  if (partFilter) {
    const kw = String(partFilter).trim().toLowerCase();
    list = list.filter(
      (row) =>
        String(row.canonical_part_label || "").toLowerCase().includes(kw) ||
        String(row.predicate || "").toLowerCase().includes(kw)
    );
  }
  if (layerFilter && layerFilter !== "all") {
    list = list.filter((row) => row.semantic_layer === layerFilter);
  }
  return list;
}

export function inscriptionDiffPreview(segments, maxLen = 120) {
  if (!segments?.length) return "";
  let out = "";
  for (const seg of segments) {
    if (seg.type === "equal") out += seg.text || "";
    else if (seg.type === "replace") out += `[${seg.left}↔${seg.right}]`;
    else if (seg.type === "delete") out += `[−${seg.left}]`;
    else if (seg.type === "insert") out += `[+${seg.right}]`;
    if (out.length >= maxLen) break;
  }
  return out.length > maxLen ? `${out.slice(0, maxLen)}…` : out;
}

/** 转义 HTML 并在源文中高亮关键词（用于多模态源文展示） */

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function highlightKeywordHtml(text, keyword) {
  const raw = String(text || "");
  const kw = String(keyword || "").trim();
  if (!raw) return "";
  if (!kw || kw.length < 2) return escapeHtml(raw);

  const lower = raw.toLowerCase();
  const kwLower = kw.toLowerCase();
  let result = "";
  let cursor = 0;
  let idx = lower.indexOf(kwLower, cursor);

  while (idx !== -1) {
    result += escapeHtml(raw.slice(cursor, idx));
    result += `<mark class="text-highlight-mark">${escapeHtml(raw.slice(idx, idx + kw.length))}</mark>`;
    cursor = idx + kw.length;
    idx = lower.indexOf(kwLower, cursor);
  }
  result += escapeHtml(raw.slice(cursor));
  return result;
}

export function resolveModality(hasImages, hasText) {
  if (hasImages && hasText) return "both";
  if (hasImages) return "image";
  if (hasText) return "text";
  return "none";
}

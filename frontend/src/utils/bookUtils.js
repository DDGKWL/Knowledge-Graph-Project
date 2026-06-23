/** 将 /books 条目或编码字符串规范为 { code, label } */
export function normalizeBookEntry(entry) {
  if (entry && typeof entry === "object" && entry.code != null) {
    const code = String(entry.code).trim().toLowerCase();
    const label = String(entry.label || entry.code).trim();
    return { code, label: label || code };
  }
  const code = String(entry ?? "").trim().toLowerCase();
  return { code, label: code };
}

/** 从书目对象列表或编码列表提取 API 查询用编码 */
export function booksToQueryCodes(books) {
  return (books || [])
    .map((item) => {
      if (item && typeof item === "object" && item.code != null) {
        return String(item.code).trim().toLowerCase();
      }
      return String(item ?? "").trim().toLowerCase();
    })
    .filter(Boolean);
}

export function bookCode(book) {
  if (book && typeof book === "object" && book.code != null) {
    return String(book.code).trim().toLowerCase();
  }
  return String(book ?? "").trim().toLowerCase();
}

export function bookLabel(book, fallback = "") {
  if (book && typeof book === "object") {
    return String(book.label || book.code || fallback).trim();
  }
  return String(fallback || book || "").trim();
}

/** 按编码在书目列表中查找显示名 */
export function labelForBookCode(code, availableBooks = []) {
  const key = String(code ?? "").trim().toLowerCase();
  const hit = (availableBooks || []).find(
    (item) => bookCode(item) === key
  );
  return hit ? bookLabel(hit, key) : key;
}

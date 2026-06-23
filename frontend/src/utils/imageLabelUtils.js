/** 从 CLIP 重命名后的文件名解析部件标签（与 clip_images/image_test.py CLASS_CONFIG 对齐） */

export const PART_LABEL_MAP = {
  longchi: "龙池",
  mingwen: "铭文",
  qimian: "琴面",
  qindi: "琴底",
  qincemian: "侧面",
  qine: "琴额",
  qintou: "琴头",
  qinwei: "琴尾",
  qinzhen: "琴轸",
  yanzu: "雁足",
};

const PART_KEYS = Object.keys(PART_LABEL_MAP);

/** 从 URL 或路径提取不含扩展名的 basename */
export function imageBasename(urlOrPath) {
  const raw = String(urlOrPath || "").trim();
  if (!raw) return "";
  const noQuery = raw.split("?")[0].split("#")[0];
  const parts = noQuery.replace(/\\/g, "/").split("/");
  const name = parts[parts.length - 1] || "";
  return name.replace(/\.(jpe?g|png|webp|gif|bmp)$/i, "");
}

/**
 * 解析图片部件标签
 * @returns {{ key: string, label: string, classified: boolean }}
 */
export function parseImageLabel(urlOrPath) {
  const base = imageBasename(urlOrPath);
  if (!base) {
    return { key: "", label: "未分类", classified: false };
  }

  for (const key of PART_KEYS) {
    if (base === key || base.startsWith(`${key}_`)) {
      return { key, label: PART_LABEL_MAP[key], classified: true };
    }
  }

  return { key: "", label: "未分类", classified: false };
}

/** 将 URL 列表转为带标签的对象列表 */
export function enrichImagePaths(urls) {
  return (urls || []).map((url) => {
    const meta = parseImageLabel(url);
    return { url, ...meta };
  });
}

/** 当前图片集合中出现的可筛选标签（去重，保留顺序） */
export function collectImageFilterOptions(labeledImages) {
  const options = [{ id: "all", label: "全部" }];
  const seen = new Set();
  (labeledImages || []).forEach((item) => {
    const id = item.classified ? item.key : "__unclassified__";
    const label = item.label || "未分类";
    if (seen.has(id)) return;
    seen.add(id);
    options.push({ id, label });
  });
  return options;
}

/** 按 chip id 筛选 */
export function filterLabeledImages(labeledImages, filterId) {
  if (!filterId || filterId === "all") return labeledImages || [];
  if (filterId === "__unclassified__") {
    return (labeledImages || []).filter((item) => !item.classified);
  }
  return (labeledImages || []).filter((item) => item.key === filterId);
}

/** 对照表 canonical_part_label → CLIP 文件名 key */
export const CANONICAL_PART_TO_IMAGE_KEY = {
  琴面: "qimian",
  琴底: "qindi",
  龙池: "longchi",
  铭文: "mingwen",
  琴额: "qine",
  琴头: "qintou",
  琴尾: "qinwei",
  雁足: "yanzu",
  侧面: "qincemian",
  琴轸: "qinzhen",
};

/** 按标准部件名取匹配的图片（最多 max 张） */
export function imagesForCanonicalPart(labeledImages, canonicalPartLabel, max = 2) {
  const key = CANONICAL_PART_TO_IMAGE_KEY[String(canonicalPartLabel || "").trim()];
  if (!key) return [];
  return (labeledImages || []).filter((item) => item.key === key).slice(0, max);
}

export const RELATION_COLOR_MAP = {
  饰有: "#ff9800",
  具有: "#2196f3",
  包含组件: "#5c6bc0",
  属于: "#8e24aa",
  制作: "#00897b",
  流传: "#78909c",
};

export const DEFAULT_COLORS = {
  artifact: "#FFA500",
  other: "#EBD6C1",
  otherLabel: "#3f3427",
  shared: "#66bb6a",
  unique: "#bcaaa4",
};

/** 按书目区分文物节点颜色（未知书目回退 artifact 色） */
export const BOOK_COLOR_MAP = {
  gq: "#4a90d9",
  yjzq: "#e67e22",
  eg: "#e67e22",
};

/** 比较模式中视为「属性冲突」的关系名关键词 */
export const COMPARE_CONFLICT_RELATION_KEYWORDS = [
  "时代",
  "年代",
  "朝代",
  "材质",
  "用途",
  "工艺",
];

export const COMPARE_CONFLICT_RELATION_PATTERN = new RegExp(
  COMPARE_CONFLICT_RELATION_KEYWORDS.join("|")
);

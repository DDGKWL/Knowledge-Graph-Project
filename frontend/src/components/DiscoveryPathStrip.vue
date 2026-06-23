<template>
  <svg
    class="discovery-path-strip-svg"
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="`0 0 ${vbW} ${vbH}`"
    preserveAspectRatio="xMidYMid meet"
    role="img"
    :aria-label="ariaLabel"
  >
    <defs>
      <marker
        :id="markerId"
        markerUnits="strokeWidth"
        markerWidth="6"
        markerHeight="6"
        refX="5"
        refY="3"
        orient="auto"
      >
        <path d="M0,0 L6,3 L0,6 z" class="discovery-strip-arrow-head" />
      </marker>
    </defs>

    <g v-for="(seg, ei) in edgeLayout" :key="'e-' + ei">
      <line
        class="discovery-strip-edge"
        :x1="seg.x1"
        :y1="seg.y"
        :x2="seg.x2"
        :y2="seg.y"
        :marker-end="markerEndRef"
      />
      <text
        class="discovery-strip-rel"
        :x="seg.midX"
        :y="seg.labelY"
        text-anchor="middle"
      >
        {{ seg.rel }}
      </text>
    </g>

    <g v-for="(n, ni) in nodeLayout" :key="'n-' + ni">
      <rect
        class="discovery-strip-node-rect"
        :class="{ 'is-artifact': n.artifact }"
        :x="n.x"
        :y="n.y"
        :width="n.w"
        :height="n.h"
        :rx="rx"
      />
      <text
        class="discovery-strip-node-text"
        :class="{ 'is-artifact': n.artifact }"
        :x="n.cx"
        :y="n.cy"
        text-anchor="middle"
        dominant-baseline="central"
      >
        {{ n.label }}
      </text>
    </g>
  </svg>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  /** 路径上的节点，顺序为根 → 中 → 候选 */
  nodes: {
    type: Array,
    default: () => [],
    validator: (arr) => Array.isArray(arr) && arr.length <= 8,
  },
  /** 相邻节点之间的关系统称，长度应为 nodes.length - 1 */
  relations: {
    type: Array,
    default: () => [],
  },
  /** 读屏用完整描述 */
  ariaLabel: { type: String, default: "" },
  /** defs 内 marker id 唯一后缀（避免多实例冲突） */
  stripId: { type: String, required: true },
  /** 合成台链块等窄容器 */
  compact: { type: Boolean, default: false },
});

const vbW = computed(() => (props.compact ? 220 : 340));
const vbH = 44;
const cy = 22;
const boxW = computed(() => (props.compact ? 58 : 70));
const boxH = 24;
const rx = 6;

const markerId = computed(() => `discovery-strip-arr-${sanitizeId(props.stripId)}`);
const markerEndRef = computed(() => `url(#${markerId.value})`);

function sanitizeId(raw) {
  return String(raw).replace(/[^a-zA-Z0-9_-]/g, "_");
}

const nodeLayout = computed(() => {
  const list = props.nodes || [];
  if (list.length < 1) return [];
  const n = list.length;
  const width = vbW.value;
  const bw = boxW.value;
  const margin = 6;
  const leftBound = margin + bw / 2;
  const rightBound = width - margin - bw / 2;
  const span = Math.max(0, rightBound - leftBound);
  const centers = list.map((_, i) =>
    n === 1 ? width / 2 : leftBound + (span * i) / (n - 1)
  );
  return list.map((node, i) => ({
    label: node.label ?? "",
    artifact: Boolean(node.artifact),
    cx: centers[i],
    cy,
    x: centers[i] - bw / 2,
    y: cy - boxH / 2,
    w: bw,
    h: boxH,
  }));
});

const edgeLayout = computed(() => {
  const nl = nodeLayout.value;
  const rels = props.relations || [];
  if (nl.length < 2) return [];
  const out = [];
  for (let i = 0; i < nl.length - 1; i++) {
    const a = nl[i];
    const b = nl[i + 1];
    const inset = 5;
    const x1 = a.cx + a.w / 2 + 1;
    const x2 = b.cx - b.w / 2 - inset;
    const y = cy;
    const rel = rels[i] ?? "关联";
    out.push({
      x1,
      x2,
      y,
      midX: (x1 + x2) / 2,
      labelY: 11,
      rel,
    });
  }
  return out;
});
</script>

<style scoped>
.discovery-path-strip-svg {
  display: block;
  width: 100%;
  height: auto;
  min-height: 40px;
  max-height: 52px;
}

.discovery-strip-node-rect {
  fill: rgba(255, 250, 243, 0.98);
  stroke: rgba(184, 159, 119, 0.55);
  stroke-width: 1.25;
}

.discovery-strip-node-rect.is-artifact {
  fill: rgba(95, 135, 124, 0.26);
  stroke: rgba(95, 135, 124, 0.55);
}

.discovery-strip-node-text {
  font-size: 9.5px;
  font-weight: 700;
  fill: #3f3427;
  pointer-events: none;
}

.discovery-strip-node-text.is-artifact {
  fill: #1e3d36;
}

.discovery-strip-edge {
  stroke: rgba(95, 135, 124, 0.55);
  stroke-width: 1.35;
  fill: none;
}

.discovery-strip-arrow-head {
  fill: rgba(95, 135, 124, 0.75);
}

.discovery-strip-rel {
  font-size: 8.5px;
  font-weight: 700;
  fill: #5f877c;
  pointer-events: none;
}
</style>

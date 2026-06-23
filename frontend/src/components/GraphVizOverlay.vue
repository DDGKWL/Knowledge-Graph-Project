<template>
  <div class="graph-viz-overlay" @click.stop @mousedown.stop>
    <div class="graph-viz-toolbar panel">
      <label class="viz-field">
        <span class="viz-label">布局</span>
        <select
          class="viz-select"
          :value="options.layoutMode"
          :disabled="compareAlign"
          @change="patch({ layoutMode: $event.target.value })"
        >
          <option value="force">力导向</option>
          <option value="radial">径向（中心扩展）</option>
          <option value="hierarchical">层次（自上而下）</option>
          <option value="book">按书目分列</option>
        </select>
      </label>
      <label class="viz-check">
        <input
          type="checkbox"
          :checked="options.showLinkLabels"
          @change="patch({ showLinkLabels: $event.target.checked })"
        />
        关系标签
      </label>
      <label class="viz-check">
        <input
          type="checkbox"
          :checked="options.colorEdgesByRelation"
          @change="patch({ colorEdgesByRelation: $event.target.checked })"
        />
        关系着色
      </label>
      <label class="viz-check">
        <input
          type="checkbox"
          :checked="options.nodeSizeByDegree"
          @change="patch({ nodeSizeByDegree: $event.target.checked })"
        />
        度中心大小
      </label>
      <label class="viz-check">
        <input
          type="checkbox"
          :checked="options.showArtifactThumbs"
          @change="patch({ showArtifactThumbs: $event.target.checked })"
        />
        文物缩略图
      </label>
      <label class="viz-check">
        <input
          type="checkbox"
          :checked="options.curvedEdges"
          @change="patch({ curvedEdges: $event.target.checked })"
        />
        曲线边
      </label>
      <label v-if="availableRelations.length" class="viz-field">
        <span class="viz-label">关系</span>
        <select
          class="viz-select"
          :value="options.relationFilter || ''"
          @change="patch({ relationFilter: $event.target.value })"
        >
          <option value="">全部</option>
          <option v-for="rel in availableRelations" :key="rel" :value="rel">{{ rel }}</option>
        </select>
      </label>
      <div class="viz-zoom-btns">
        <button type="button" class="viz-btn" title="适应画布" @click="$emit('fit')">适应</button>
        <button type="button" class="viz-btn" title="放大" @click="$emit('zoom-in')">+</button>
        <button type="button" class="viz-btn" title="缩小" @click="$emit('zoom-out')">−</button>
        <button type="button" class="viz-btn" title="重置缩放" @click="$emit('zoom-reset')">重置</button>
      </div>
    </div>

    <div v-if="graphStats" class="graph-viz-stats panel">
      <span>{{ graphStats.nodes }} 节点</span>
      <span class="stats-sep">·</span>
      <span>{{ graphStats.links }} 关系</span>
      <span v-if="graphStats.artifacts" class="stats-sep">·</span>
      <span v-if="graphStats.artifacts">{{ graphStats.artifacts }} 文物</span>
    </div>

    <div class="graph-viz-legend panel">
      <div class="legend-title">图例</div>
      <template v-if="compareAlign">
        <div class="legend-row"><span class="legend-dot shared" />共享对齐</div>
        <div class="legend-row"><span class="legend-dot unique" />独有邻居</div>
        <div class="legend-row"><span class="legend-dot artifact" />比较文物</div>
      </template>
      <template v-else>
        <div class="legend-row"><span class="legend-dot artifact" />文物节点</div>
        <div class="legend-row"><span class="legend-dot other" />属性/其他</div>
        <div
          v-for="book in bookLegend"
          :key="book.code"
          class="legend-row"
        >
          <span class="legend-dot" :style="{ background: bookColor(book.code) }" />
          {{ book.label }}
        </div>
        <div v-if="options.colorEdgesByRelation" class="legend-relations">
          <div
            v-for="(color, name) in relationColors"
            :key="name"
            class="legend-row small"
          >
            <span class="legend-line" :style="{ background: color }" />
            {{ name }}
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { BOOK_COLOR_MAP, DEFAULT_COLORS, RELATION_COLOR_MAP } from "@/utils/graphConfig";
import { bookCode, normalizeBookEntry } from "@/utils/bookUtils";

const props = defineProps({
  options: { type: Object, required: true },
  availableBooks: { type: Array, default: () => [] },
  availableRelations: { type: Array, default: () => [] },
  graphStats: { type: Object, default: null },
  compareAlign: { type: Boolean, default: false },
});

const emit = defineEmits([
  "update:options",
  "fit",
  "zoom-in",
  "zoom-out",
  "zoom-reset",
]);

const relationColors = RELATION_COLOR_MAP;

const bookLegend = computed(() =>
  (props.availableBooks || []).map((b) => normalizeBookEntry(b))
);

function bookColor(code) {
  const key = bookCode(code);
  return BOOK_COLOR_MAP[key] || DEFAULT_COLORS.artifact;
}

function patch(partial) {
  emit("update:options", { ...props.options, ...partial });
}
</script>

<style scoped>
.graph-viz-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 4;
}

.graph-viz-toolbar,
.graph-viz-legend {
  pointer-events: auto;
  position: absolute;
  background: rgba(255, 252, 245, 0.94);
  border: 1px solid rgba(184, 159, 119, 0.45);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(88, 70, 44, 0.1);
}

.graph-viz-toolbar {
  top: 10px;
  left: 10px;
  right: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  padding: 8px 12px;
}

.graph-viz-stats {
  pointer-events: auto;
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 6px 12px;
  font-size: 11px;
  color: var(--muted, #6d5c4d);
}

.stats-sep {
  margin: 0 4px;
  opacity: 0.5;
}

.graph-viz-legend {
  bottom: 10px;
  left: 10px;
  max-width: 220px;
  padding: 10px 12px;
  font-size: 11px;
}

.legend-title {
  font-weight: 700;
  margin-bottom: 6px;
  color: var(--text, #3e2723);
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0;
  color: var(--muted, #6d5c4d);
}

.legend-row.small {
  font-size: 10px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-dot.artifact {
  background: #ffa500;
}

.legend-dot.other {
  background: #ebd6c1;
}

.legend-dot.shared {
  background: #66bb6a;
}

.legend-dot.unique {
  background: #bcaaa4;
}

.legend-line {
  width: 18px;
  height: 3px;
  border-radius: 2px;
  flex-shrink: 0;
}

.legend-relations {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed rgba(184, 159, 119, 0.35);
}

.viz-field {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.viz-label {
  color: var(--muted, #6d5c4d);
  white-space: nowrap;
}

.viz-select {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid rgba(184, 159, 119, 0.45);
  background: #fff;
}

.viz-check {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text, #3e2723);
  cursor: pointer;
}

.viz-zoom-btns {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.viz-btn {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid rgba(184, 159, 119, 0.45);
  background: rgba(255, 255, 255, 0.9);
  cursor: pointer;
}

.viz-btn:hover {
  background: rgba(184, 159, 119, 0.15);
}
</style>

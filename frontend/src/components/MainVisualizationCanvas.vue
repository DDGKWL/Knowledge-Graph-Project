<template>
  <section class="visual-canvas panel">
    <div class="canvas-header">
      <div class="segmented-control compact canvas-focus-switch" role="toolbar" aria-label="版面焦点">
        <button
          type="button"
          class="seg-btn"
          :class="{ active: focusMode === 'visual' }"
          @click="emit('change-focus', 'visual')"
        >
          主视图
        </button>
        <button
          type="button"
          class="seg-btn"
          :class="{ active: focusMode === 'evidence' }"
          @click="emit('change-focus', 'evidence')"
        >
          证据优先
        </button>
        <button
          type="button"
          class="seg-btn"
          :class="{ active: focusMode === 'balanced' }"
          @click="emit('change-focus', 'balanced')"
        >
          均衡
        </button>
      </div>
      <div class="canvas-header-actions">
        <div class="segmented-control canvas-mode-switch" role="tablist" aria-label="分析模式">
          <button
            v-for="item in modeItems"
            :key="item.value"
            type="button"
            class="seg-btn"
            role="tab"
            :class="{ active: mode === item.value }"
            :aria-selected="mode === item.value"
            @click="emit('change-mode', item.value)"
          >
            {{ item.label }}
          </button>
        </div>
        <div class="canvas-tags">
          <span class="canvas-tag">{{ modeLabel }}</span>
          <span class="canvas-tag emphasis">{{ artifact.name }}</span>
        </div>
      </div>
    </div>

    <div v-if="mode === 'artifact' || mode === 'discovery'" class="canvas-content artifact-layout">
      <div class="artifact-main-column">
        <div class="artifact-center-block graph-container">
          <svg ref="svgRef" style="width: 100%; height: 100%;"></svg>
          <GraphVizOverlay
            :options="graphVizOptions"
            :available-books="availableBooks"
            :available-relations="graphRelationTypes"
            :graph-stats="graphStats"
            :compare-align="false"
            @update:options="onGraphVizOptionsUpdate"
            @fit="onGraphFit"
            @zoom-in="onGraphZoomIn"
            @zoom-out="onGraphZoomOut"
            @zoom-reset="onGraphZoomReset"
          />
        </div>
        <MultimodalEvidenceStrip
          v-if="mode === 'artifact'"
          :focus="multimodalFocus"
        />
      </div>
      <div v-if="mode === 'artifact'" class="artifact-side-grid">
        <div class="placeholder-block layer-block">
          <div class="placeholder-title">基础层</div>
          <div class="mini-graph-wrap">
            <div v-if="!baseLayerGraph" class="empty-hint">暂无基础层关系</div>
            <svg
              v-else
              class="base-layer-mini-svg"
              :viewBox="`0 0 ${baseLayerGraph.w} ${baseLayerGraph.h}`"
              xmlns="http://www.w3.org/2000/svg"
              aria-label="基础层关系子图"
              role="img"
            >
              <defs>
                <marker id="mini-arrow-head-base" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                  <path d="M0,0 L10,5 L0,10 z" fill="rgba(95,135,124,0.75)" />
                </marker>
              </defs>

              <g v-for="(edge, ei) in baseLayerGraph.edges" :key="'e-' + ei">
                <line
                  class="mini-edge-line"
                  :x1="edge.x1"
                  :y1="edge.y1"
                  :x2="edge.x2"
                  :y2="edge.y2"
                  marker-end="url(#mini-arrow-head-base)"
                />
                <text class="mini-edge-label" :x="edge.midX" :y="edge.midY" text-anchor="middle">
                  {{ edge.relation }}
                </text>
              </g>

              <circle
                class="mini-node-mini mini-node-center"
                :cx="baseLayerGraph.cx"
                :cy="baseLayerGraph.cy"
                :r="baseLayerGraph.cr"
              />
              <text
                class="mini-node-label mini-node-label-center"
                :x="baseLayerGraph.cx"
                :y="baseLayerGraph.cy"
                dy="4"
                text-anchor="middle"
              >
                {{ baseLayerGraph.centerLabel }}
              </text>

              <g v-for="(edge, ei) in baseLayerGraph.edges" :key="'t-' + ei">
                <circle class="mini-node-mini mini-node-tail" :cx="edge.tx" :cy="edge.ty" :r="edge.tr" />
                <text class="mini-node-label mini-node-label-tail" :x="edge.tx" :y="edge.ty" dy="4" text-anchor="middle">
                  {{ edge.targetLabel }}
                </text>
              </g>
            </svg>
          </div>
        </div>

        <div class="placeholder-block layer-block">
          <div class="placeholder-title">特有层</div>
          <div class="mini-graph-wrap">
            <div v-if="!uniqueLayerGraph" class="empty-hint">暂无特有层关系</div>
            <svg
              v-else
              class="base-layer-mini-svg"
              :viewBox="`0 0 ${uniqueLayerGraph.w} ${uniqueLayerGraph.h}`"
              xmlns="http://www.w3.org/2000/svg"
              aria-label="特有层关系子图"
              role="img"
            >
              <defs>
                <marker id="mini-arrow-head-unique" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
                  <path d="M0,0 L10,5 L0,10 z" fill="rgba(145,112,72,0.82)" />
                </marker>
              </defs>

              <g v-for="(edge, ei) in uniqueLayerGraph.edges" :key="'ue-' + ei">
                <line
                  class="mini-edge-line mini-edge-line-unique"
                  :x1="edge.x1"
                  :y1="edge.y1"
                  :x2="edge.x2"
                  :y2="edge.y2"
                  marker-end="url(#mini-arrow-head-unique)"
                />
                <text class="mini-edge-label" :x="edge.midX" :y="edge.midY" text-anchor="middle">
                  {{ edge.relation }}
                </text>
              </g>

              <circle
                class="mini-node-mini mini-node-center mini-node-center-unique"
                :cx="uniqueLayerGraph.cx"
                :cy="uniqueLayerGraph.cy"
                :r="uniqueLayerGraph.cr"
              />
              <text
                class="mini-node-label mini-node-label-center"
                :x="uniqueLayerGraph.cx"
                :y="uniqueLayerGraph.cy"
                dy="4"
                text-anchor="middle"
              >
                {{ uniqueLayerGraph.centerLabel }}
              </text>

              <g v-for="(edge, ei) in uniqueLayerGraph.edges" :key="'ut-' + ei">
                <circle class="mini-node-mini mini-node-tail mini-node-tail-unique" :cx="edge.tx" :cy="edge.ty" :r="edge.tr" />
                <text class="mini-node-label mini-node-label-tail" :x="edge.tx" :y="edge.ty" dy="4" text-anchor="middle">
                  {{ edge.targetLabel }}
                </text>
              </g>
            </svg>
          </div>
        </div>

        <div class="placeholder-block layer-block">
          <div class="placeholder-title">背景层</div>
          <div class="relation-list">
            <div v-if="layerBuckets.background.length === 0" class="empty-hint">暂无背景层关系</div>
            <div v-for="item in layerBuckets.background" :key="item.key" class="rel-item">
              <span class="rel-label">[{{ item.relation }}]</span>
              <span>{{ item.targetName }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="discovery-side-scroll discovery-rail">
        <p class="discovery-task-lead">
          点击<strong>路径卡片</strong>在主图预览二跳路径；点右侧 <strong>+</strong> 将路径拆为链块加入底部合成台；在合成台点击链块可高亮该段，「高亮全部」显示已拼接路径并集。
        </p>

        <div class="placeholder-block info-block discovery-candidates-block">
          <div class="placeholder-title">关系扩展候选</div>
          <div class="discovery-rules-hint empty-hint">
            已合并同一候选节点；已忽略「首跳与二跳关系同名」的路径；二跳终点仅保留非文物。
          </div>
          <div
            v-if="discoveryView.discoveryMeta?.truncated"
            class="empty-hint discovery-truncate-hint"
          >
            共 {{ discoveryView.discoveryMeta.totalMerged }} 个候选，当前展示前 {{ discoveryView.discoveryMeta.shown }} 条。
          </div>
          <div class="relation-list discovery-candidate-list">
            <div v-if="discoveryView.extensionCandidates.length === 0" class="empty-hint">暂无扩展关系候选</div>
            <div
              v-for="row in discoveryCandidateRows"
              :key="row.item.key"
              class="rel-item discovery-candidate-row"
              :class="{ active: discoverySelectedKey === String(row.item.key) }"
            >
              <div
                class="discovery-candidate-main"
                role="button"
                tabindex="0"
                :title="row.item.candidateNodeName + ' — ' + row.item.reason"
                @click="onDiscoveryCandidateClick(row.item)"
                @keydown.enter.prevent="onDiscoveryCandidateClick(row.item)"
              >
              <div v-if="row.stripNodes.length === 3" class="discovery-path-strip-wrap">
                <DiscoveryPathStrip
                  :nodes="row.stripNodes"
                  :relations="row.stripRels"
                  :aria-label="row.ariaLabel || row.item.candidateNodeName"
                  :strip-id="'cand-' + String(row.item.key)"
                />
              </div>
              <div v-else class="discovery-path-fallback">
                <span class="discovery-candidate-name">{{ row.item.candidateNodeName }}</span>
              </div>
              <div class="discovery-path-reason-line" :title="row.item.reason">{{ truncateLabel(row.item.reason, 56) }}</div>
              </div>
              <button
                v-if="row.stripNodes.length === 3"
                type="button"
                class="discovery-add-synthesis"
                title="拆为两段链块并加入底部证据合成台"
                @click.stop="onAddToSynthesis(row)"
              >
                +
              </button>
            </div>
          </div>
        </div>

        <div class="discovery-grid">
          <div class="placeholder-block info-block">
            <div class="placeholder-title">解释链</div>
            <div class="relation-list discovery-chain-list">
              <div v-if="discoveryCandidateRows.length === 0" class="empty-hint">暂无解释链</div>
              <div
                v-for="(row, chainIndex) in discoveryCandidateRows"
                :key="'chain-' + row.item.key"
                class="rel-item discovery-chain-item"
              >
                <div v-if="row.stripNodes.length === 3" class="discovery-path-strip-wrap">
                  <DiscoveryPathStrip
                    :nodes="row.stripNodes"
                    :relations="row.stripRels"
                    :aria-label="row.ariaLabel || discoveryView.explanationChains[chainIndex]?.pathText"
                    :strip-id="'chain-' + String(row.item.key)"
                  />
                </div>
                <p
                  v-if="discoveryView.explanationChains[chainIndex]"
                  class="discovery-chain-caption"
                  :class="{ 'discovery-chain-caption--solo': row.stripNodes.length !== 3 }"
                  :title="discoveryView.explanationChains[chainIndex].pathText"
                >
                  {{ truncateLabel(discoveryView.explanationChains[chainIndex].pathText, 72) }}
                </p>
              </div>
            </div>
          </div>
          <div class="placeholder-block info-block">
            <div class="placeholder-title">新知识机会</div>
            <div class="relation-list">
              <div v-if="discoveryView.knowledgeOpportunities.length === 0" class="empty-hint">暂无发现</div>
              <div v-for="item in discoveryView.knowledgeOpportunities" :key="item.title" class="rel-item">
                <strong>{{ item.title }}</strong>
                <span>{{ item.detail }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="mode === 'compare'" class="canvas-content compare-layout">
      <div class="compare-graph-row">
        <div v-if="compareArtifactIds.length < 2" class="compare-graph-block compare-graph-placeholder panel">
          <p class="empty-hint">请在左侧将至少 2 件文物「加入比较」，以加载比较子图。</p>
        </div>
        <div v-else-if="multiCompareLoading" class="compare-graph-block compare-graph-placeholder panel">
          <p class="empty-hint">正在从后端加载多节点比较子图…</p>
        </div>
        <div v-else-if="multiCompareError" class="compare-graph-block compare-graph-placeholder panel">
          <p class="empty-hint">{{ multiCompareError }}</p>
        </div>
        <div v-else class="compare-graph-block graph-container">
          <svg ref="svgRef" style="width: 100%; height: 100%;"></svg>
          <GraphVizOverlay
            :options="graphVizOptions"
            :available-books="availableBooks"
            :compare-align="isCompareAlignView"
            @update:options="onGraphVizOptionsUpdate"
            @fit="onGraphFit"
            @zoom-in="onGraphZoomIn"
            @zoom-out="onGraphZoomOut"
            @zoom-reset="onGraphZoomReset"
          />
        </div>
        <p class="compare-graph-caption empty-hint">
          <template v-if="isCompareAlignView">
            <span class="compare-align-lead">
              {{ isCrossBookCompare ? "跨书" : "同书" }}对齐视图：左/右为两件文物，中间绿色 hub 为
              <strong>共享对齐</strong>；虚线边为各侧 <strong>独有邻居</strong>。
            </span>
            <span class="compare-legend">
              <span class="legend-dot legend-artifact">文物（按书目着色）</span>
              <span class="legend-dot legend-shared">共享对齐</span>
              <span class="legend-dot legend-unique">独有邻居</span>
            </span>
            <label class="compare-unique-toggle">
              <input v-model="compareShowUnique" type="checkbox" @change="loadCompareGraph" />
              显示独有属性
            </label>
            <span v-if="compareApiResult?.meta?.effective_match_mode" class="compare-mode-tag">
              对齐键：{{ compareApiResult.meta.effective_match_mode }}
            </span>
          </template>
          <template v-else>
            比较子图未返回对齐布局；请确认已加载统一比较数据（/artifact-compare）。
          </template>
        </p>
      </div>
      <div class="compare-main-row">
        <div class="placeholder-block info-block">
          <div class="placeholder-title">共享结构 · 共有节点</div>
          <div class="relation-list">
            <div v-if="compareArtifactIds.length < 2" class="empty-hint">
              请在左侧比较栏将至少 2 件文物「加入」比较
            </div>
            <template v-else>
              <div v-if="multiCompareLoading" class="empty-hint">正在从后端加载多节点子图…</div>
              <div v-else-if="multiCompareError" class="empty-hint">{{ multiCompareError }}</div>
              <template v-else>
                <div class="multi-compare-summary empty-hint">
                  {{ isCrossBookCompare ? "跨书" : "同书" }}统一比较 · 书目
                  {{ (compareApiResult?.meta?.books || []).join("、") || "—" }} · 对齐
                  {{ compareApiResult?.meta?.effective_match_mode || "text" }} · 对齐视图节点
                  {{ multiComparePayload.nodes.length }}（物理
                  {{ compareApiResult?.meta?.physical_node_count ?? "—" }}），边
                  {{ multiComparePayload.links.length }} ·
                  <strong>共享对齐</strong>节点 {{ multiCompareSharedNodes.length }} 个
                </div>
                <details class="multi-compare-debug">
                  <summary>查看后端原始 JSON（调试用）</summary>
                  <pre class="multi-compare-json">{{ multiCompareJsonPreview }}</pre>
                </details>
                <div v-if="multiCompareSharedNodes.length === 0" class="empty-hint multi-compare-hint">
                  未发现可对齐的共有非文物节点（各文物一跳「关系 + 显示名」无交集）。
                </div>
                <div v-for="item in multiCompareSharedNodes" :key="item.id" class="rel-item multi-shared-node">
                <div class="multi-shared-head">
                  <span class="rel-label">非文物 · 共享</span>
                  <strong class="multi-shared-name">{{ item.name }}</strong>
                </div>
                <div class="multi-shared-meta">ID {{ item.id }}</div>
                <div v-if="item.belongsTo" class="multi-shared-meta">
                  {{ isCrossBookCompare ? "书目" : "归属" }}：{{ item.belongsTo }}
                </div>
                <div v-if="item.relations?.length" class="multi-shared-meta">
                  关系：{{ item.relations.join("、") }}
                </div>
                </div>
              </template>
            </template>
          </div>
        </div>
        <div class="placeholder-block info-block compare-panel-block">
          <div class="placeholder-title">差异结构</div>
          <p class="compare-block-hint empty-hint">同一关系类型，各文物连向的邻居节点不一致（主图一跳）。点击行可在上方子图高亮。</p>
          <div class="relation-list">
            <div v-if="!comparePanelsReady" class="empty-hint">{{ comparePanelsEmptyText }}</div>
            <div
              v-for="item in compareView.differenceStructures"
              :key="item.key"
              class="rel-item compare-evidence-row"
              :class="{ active: compareHighlightKey === item.key }"
            >
              <div
                class="compare-evidence-main compare-clickable-row"
                role="button"
                tabindex="0"
                @click="onCompareHighlightClick(item)"
                @keydown.enter.prevent="onCompareHighlightClick(item)"
              >
                <span class="rel-label">[{{ item.relation }}]</span>
                <span>{{ item.values.join(' / ') }}</span>
              </div>
              <button
                type="button"
                class="discovery-add-synthesis"
                title="加入证据链（含原文摘录）"
                @click.stop="onAddCompareEvidence(item, 'compare-diff')"
              >
                +
              </button>
            </div>
          </div>
        </div>
      </div>
      <div class="compare-sub-row">
        <div class="placeholder-block info-block compare-panel-block">
          <div class="placeholder-title">缺失结构</div>
          <p class="compare-block-hint empty-hint">其他文物有、本件没有的一跳关系。点击单行可高亮该边。</p>
          <div class="relation-list">
            <div v-if="!comparePanelsReady" class="empty-hint">{{ comparePanelsEmptyText }}</div>
            <div
              v-for="row in compareView.missingStructures"
              :key="row.artifactId"
              class="rel-item compare-missing-group"
            >
              <div class="compare-missing-head">
                <strong>{{ row.artifactName }}</strong>
                <span class="compare-missing-count">共 {{ row.total }} 条</span>
              </div>
              <div v-if="row.total === 0" class="empty-hint compare-missing-none">无缺失</div>
              <template v-else>
                <div
                  v-for="m in visibleMissingItems(row)"
                  :key="m.key"
                  class="compare-missing-line compare-evidence-row"
                  :class="{ active: compareHighlightKey === m.key }"
                >
                  <div
                    class="compare-evidence-main compare-clickable-row"
                    role="button"
                    tabindex="0"
                    @click="onCompareHighlightClick(m)"
                    @keydown.enter.prevent="onCompareHighlightClick(m)"
                  >
                    {{ m.label }}
                  </div>
                  <button
                    type="button"
                    class="discovery-add-synthesis compare-add-evidence"
                    title="加入证据链（含原文摘录）"
                    @click.stop="onAddCompareEvidence(m, 'compare-missing', row)"
                  >
                    +
                  </button>
                </div>
                <button
                  v-if="row.total > compareMissingPreviewCount"
                  type="button"
                  class="compare-expand-btn"
                  @click="toggleMissingExpand(row.artifactId)"
                >
                  {{ isMissingExpanded(row.artifactId) ? '收起' : `展开其余 ${row.total - compareMissingPreviewCount} 条` }}
                </button>
              </template>
            </div>
          </div>
        </div>
        <div class="placeholder-block info-block compare-panel-block">
          <div class="placeholder-title">冲突结构</div>
          <p class="compare-block-hint empty-hint">差异结构中，关系名含时代/材质等属性类关键词的项。</p>
          <div class="relation-list">
            <div v-if="!comparePanelsReady" class="empty-hint">{{ comparePanelsEmptyText }}</div>
            <div v-else-if="compareView.conflictStructures.length === 0" class="empty-hint">未发现属性类冲突</div>
            <div
              v-for="item in compareView.conflictStructures"
              :key="item.key"
              class="rel-item conflict-item compare-evidence-row"
              :class="{ active: compareHighlightKey === item.key }"
            >
              <div
                class="compare-evidence-main compare-clickable-row"
                role="button"
                tabindex="0"
                @click="onCompareHighlightClick(item)"
                @keydown.enter.prevent="onCompareHighlightClick(item)"
              >
                <span class="rel-label">[{{ item.relation }}]</span>
                <span>{{ item.detail }}</span>
              </div>
              <button
                type="button"
                class="discovery-add-synthesis"
                title="加入证据链（含原文摘录）"
                @click.stop="onAddCompareEvidence(item, 'compare-conflict')"
              >
                +
              </button>
            </div>
          </div>
        </div>
        <div class="placeholder-block info-block compare-panel-block">
          <div class="placeholder-title">扩展候选（二跳）</div>
          <p class="compare-block-hint empty-hint">按发现模式规则，从主图统计各文物二跳扩展候选数量。</p>
          <div class="relation-list">
            <div v-if="!comparePanelsReady" class="empty-hint">{{ comparePanelsEmptyText }}</div>
            <div v-for="item in compareView.numericComparison" :key="item.artifactId" class="rel-item">
              <strong>{{ item.artifactName }}</strong>
              <span>扩展候选 {{ item.candidateCount }} 条</span>
            </div>
          </div>
        </div>
      </div>
      <div class="compare-part-row">
        <PartComparePanel
          :loading="partCompareLoading"
          :error="partCompareError"
          :result="partCompareResult"
          :artifact-images-map="compareArtifactImagesMap"
          :selected-slot-key="partCompareHighlightKey"
          :available-books="availableBooks"
          @row-click="onPartCompareRowClick"
        />
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";
import { getArtifactImages, getArtifactText, getGraphData, postArtifactCompare, postPartCompare } from "@/utils/api";
import { booksToQueryCodes } from "@/utils/bookUtils";
import { initGraph } from "@/utils/graphRender";
import { buildCompareView } from "@/utils/compareEngine";
import { buildDiscoveryView } from "@/utils/discoveryEngine";
import {
  splitHighlightPathIntoSegments,
  createSegmentId,
} from "@/utils/synthesisEngine";
import {
  buildCompareEvidenceItem,
  enrichDiscoverySegment,
} from "@/utils/evidenceEngine";
import DiscoveryPathStrip from "./DiscoveryPathStrip.vue";
import GraphVizOverlay from "./GraphVizOverlay.vue";
import MultimodalEvidenceStrip from "./MultimodalEvidenceStrip.vue";
import PartComparePanel from "./PartComparePanel.vue";
import { resolveModality } from "@/utils/textHighlight";
import { enrichImagePaths } from "@/utils/imageLabelUtils";

const LAYER_RELATION_CONFIG = {
  base: ["包含组件"],
  backgroundKeywords: ["历史", "人物", "流传", "文献", "参考"],
};

const props = defineProps({
  mode: { type: String, required: true },
  artifact: { type: Object, required: true },
  compareList: { type: Array, required: true },
  focusMode: { type: String, required: true },
  availableBooks: { type: Array, default: () => [] },
  selectedBooks: { type: Array, default: () => [] },
  booksReady: { type: Boolean, default: false },
  synthesisSegments: { type: Array, default: () => [] },
  synthesisSelectedSegmentId: { type: String, default: "" },
  synthesisHighlightAll: { type: Boolean, default: false },
});

const emit = defineEmits([
  "artifact-images-change",
  "artifact-text-change",
  "artifact-queue-enqueue",
  "graph-context-change",
  "change-mode",
  "change-focus",
  "add-synthesis-segments",
  "clear-synthesis-selection",
  "ensure-books-for-compare",
]);

const modeItems = [
  { value: "artifact", label: "单文物" },
  { value: "compare", label: "比较" },
  { value: "discovery", label: "发现" },
];

const modeLabel = computed(() => {
  if (props.mode === "compare") return `比较视图 · ${props.compareList.length} 件`;
  if (props.mode === "discovery") return "扩展发现";
  return "单文物结构";
});

const svgRef = ref(null);
let graphInstance = null;
const graphVizOptions = ref({
  layoutMode: "force",
  showLinkLabels: true,
  colorEdgesByRelation: true,
  nodeSizeByDegree: false,
  showArtifactThumbs: true,
  curvedEdges: true,
  relationFilter: "",
});

const activeGraphLinks = computed(() => {
  if (props.mode === "compare" && multiComparePayload.value?.links?.length) {
    return multiComparePayload.value.links;
  }
  return fullGraphData.value.links || [];
});

const graphRelationTypes = computed(() => {
  const rels = new Set();
  activeGraphLinks.value.forEach((l) => {
    const r = l.relation || l.label;
    if (r) rels.add(String(r));
  });
  return [...rels].sort((a, b) => a.localeCompare(b, "zh"));
});

const graphStats = computed(() => {
  const nodes = fullGraphData.value.nodes || [];
  const links = fullGraphData.value.links || [];
  return {
    nodes: nodes.length,
    links: links.length,
    artifacts: nodes.filter((n) => Number(n.is_artifact) === 1).length,
  };
});

const compareGraphStats = computed(() => {
  const payload = multiComparePayload.value || {};
  const nodes = payload.nodes || [];
  const links = payload.links || [];
  return {
    nodes: nodes.length,
    links: links.length,
    artifacts: nodes.filter((n) => Number(n.is_artifact) === 1 || n.role === "artifact").length,
  };
});
const discoverySelectedKey = ref("");
const compareHighlightKey = ref("");
const compareMissingPreviewCount = 3;
const compareExpandedMissing = ref({});
const selectedNodeIds = ref([]);
const fullGraphData = ref({ nodes: [], links: [] });
const relatedSubgraph = ref({ nodes: [], links: [] });
const graphLoadError = ref("");

const multimodalFocus = ref({
  nodeId: "",
  nodeName: "",
  imagePaths: [],
  sourceText: "",
  description: "",
  highlightKeyword: "",
  isArtifact: false,
  modality: "none",
});

const layerBuckets = ref({
  base: [],
  unique: [],
  background: [],
});

const graphContext = ref({
  selectedArtifactId: "",
  evidencePayload: {},
  relatedSubgraph: { nodes: [], links: [] },
  layerBuckets: { base: [], unique: [], background: [] },
  candidates: [],
  aiSummary: "",
});

const compareView = computed(() => {
  if (compareApiResult.value?.meta?.ready) {
    return mapCrossCompareToView(compareApiResult.value);
  }
  return buildCompareView(props.compareList || [], fullGraphData.value);
});

const comparePanelsReady = computed(() => compareView.value.meta?.ready === true);

const comparePanelsEmptyText = computed(() => {
  if (compareArtifactIds.value.length < 2) return "请至少选择 2 件文物进行比较";
  if (!compareApiResult.value?.meta?.ready && !multiCompareLoading.value) {
    return multiCompareError.value || "统一比较数据未加载";
  }
  return "暂无可展示项";
});

/** 左侧比较栏中已「加入比较」的文物节点 ID（与 App.vue 传入的 compareList 一致） */
const compareArtifactIds = computed(() =>
  (props.compareList || []).map((item) => String(item.id)).filter(Boolean)
);

function booksFromArtifactIds(ids) {
  return [
    ...new Set(
      (ids || [])
        .map((id) => String(id).split("_")[0]?.trim().toLowerCase())
        .filter(Boolean)
    ),
  ];
}

const isCrossBookCompare = computed(() => booksFromArtifactIds(compareArtifactIds.value).length > 1);

/** 统一比较返回 compare-align 子图（同书/跨书均可用共享 hub + 独有邻居） */
const isCompareAlignView = computed(() => {
  const payload = multiComparePayload.value;
  return (
    payload?.layout === "compare-align" &&
    Array.isArray(payload?.nodes) &&
    payload.nodes.some((n) => n.role)
  );
});

const multiCompareLoading = ref(false);
const multiCompareError = ref("");
const multiComparePayload = ref({ nodes: [], links: [] });
/** POST /artifact-compare 完整响应（同书/跨书） */
const compareApiResult = ref(null);
/** POST /part-compare 部件级对照 */
const partCompareResult = ref(null);
const partCompareLoading = ref(false);
const partCompareError = ref("");
const partCompareHighlightKey = ref("");
/** 比较模式下各文物 labeled 图片 { artifactId: LabeledImage[] } */
const compareArtifactImagesMap = ref({});

function normalizeHighlightPath(hp) {
  if (!hp) return null;
  const nodeIds = hp.nodeIds || hp.node_ids || [];
  const edges = (hp.edges || []).map((e) => ({
    source: e.source,
    target: e.target,
    relation: e.relation || "关联",
  }));
  return { nodeIds, edges };
}

function mapCrossCompareToView(result) {
  return {
    sharedStructures: (result.shared_structures || []).map((s) => ({
      relation: s.relation,
      targetName: s.target_name,
    })),
    differenceStructures: (result.difference_structures || []).map((d) => ({
      key: d.key,
      relation: d.relation,
      values: d.values || [],
      evidence: d.evidence,
      highlightPath: normalizeHighlightPath(d.highlight_path || d.highlightPath),
      displayHighlightPath: normalizeHighlightPath(
        d.display_highlight_path || d.displayHighlightPath
      ),
    })),
    missingStructures: (result.missing_structures || []).map((r) => ({
      artifactId: r.artifact_id,
      artifactName: r.artifact_name,
      missing: (r.missing || []).map((m) => ({
        key: m.key,
        relation: m.relation,
        targetId: m.target_id,
        targetName: m.target_name,
        label: m.label,
        evidence: m.evidence,
        highlightPath: normalizeHighlightPath(m.highlight_path || m.highlightPath),
        displayHighlightPath: normalizeHighlightPath(
          m.display_highlight_path || m.displayHighlightPath
        ),
      })),
      total: r.total ?? (r.missing || []).length,
    })),
    conflictStructures: (result.conflict_structures || []).map((c) => ({
      key: c.key,
      relation: c.relation,
      detail: c.detail,
      evidence: c.evidence,
      highlightPath: normalizeHighlightPath(c.highlight_path || c.highlightPath),
      displayHighlightPath: normalizeHighlightPath(
        c.display_highlight_path || c.displayHighlightPath
      ),
    })),
    numericComparison: [],
    meta: result.meta || { ready: false },
  };
}

function ensureSelectedBooksForCompare(ids) {
  emit("ensure-books-for-compare", ids);
}

const multiCompareJsonPreview = computed(() =>
  JSON.stringify(
    compareApiResult.value?.meta?.ready ? compareApiResult.value : multiComparePayload.value,
    null,
    2
  )
);

/** 解析节点归属字段（兼容后端 belongs_to / belongsTo / belongs to） */
function nodeBelongsTokens(node) {
  if (!node) return [];
  const raw = node.belongs_to ?? node.belongsTo ?? node["belongs to"];
  if (raw == null || raw === "") return [];
  return String(raw)
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function belongsUnionForCompareIds(compareIds, apiNodes, graphNodes) {
  const union = new Set();
  const apiById = new Map((apiNodes || []).map((n) => [String(n.id), n]));
  const graphById = new Map((graphNodes || []).map((n) => [String(n.id), n]));
  compareIds.forEach((id) => {
    const sid = String(id);
    const n = apiById.get(sid) || graphById.get(sid);
    nodeBelongsTokens(n).forEach((t) => union.add(t));
  });
  return union;
}

/** 非文物节点且 belongs_to 解析后的集合完整包含比较文物归属并集（并集中每一项都必须在节点归属中出现，缺一不算共享） */
function computeSharedNonArtifactByBelongsUnion(compareIds, apiNodes, graphNodes) {
  const ids = compareIds.map(String);
  if (ids.length < 2) return [];

  const union = belongsUnionForCompareIds(ids, apiNodes, graphNodes);
  if (union.size === 0) return [];

  const rows = [];
  (apiNodes || []).forEach((n) => {
    if (Number(n.is_artifact) === 1) return;
    const tokenSet = new Set(nodeBelongsTokens(n));
    const coversUnion = [...union].every((t) => tokenSet.has(t));
    if (!coversUnion) return;
    rows.push({
      id: String(n.id),
      name: n.name || String(n.id),
      belongsTo: n.belongs_to != null ? String(n.belongs_to).trim() : "",
    });
  });

  rows.sort((a, b) => String(a.name).localeCompare(String(b.name), "zh-Hans-CN"));
  return rows;
}

const multiCompareBelongsUnion = computed(() => {
  if (compareArtifactIds.value.length < 2) return [];
  const u = belongsUnionForCompareIds(
    compareArtifactIds.value,
    multiComparePayload.value.nodes,
    fullGraphData.value.nodes
  );
  return [...u].sort((a, b) => a.localeCompare(b, "zh-Hans-CN"));
});

const multiCompareBelongsUnionText = computed(() =>
  multiCompareBelongsUnion.value.length ? multiCompareBelongsUnion.value.join("、") : "（无）"
);

const multiCompareSharedNodes = computed(() => {
  if (compareApiResult.value?.shared_nodes?.length) {
    return compareApiResult.value.shared_nodes.map((n) => ({
      id: String(n.id),
      name: n.name || String(n.id),
      belongsTo: (n.books || []).join("、") || n.belongsTo || "",
      relations: n.relations || [],
    }));
  }
  return computeSharedNonArtifactByBelongsUnion(
    compareArtifactIds.value,
    multiComparePayload.value.nodes,
    fullGraphData.value.nodes
  );
});

async function loadMultiCompareSubgraph() {
  const ids = compareArtifactIds.value;
  if (props.mode !== "compare" || ids.length < 2) {
    multiComparePayload.value = { nodes: [], links: [] };
    compareApiResult.value = null;
    multiCompareError.value = "";
    multiCompareLoading.value = false;
    return;
  }

  multiCompareLoading.value = true;
  multiCompareError.value = "";
  compareApiResult.value = null;
  try {
    const { data } = await postArtifactCompare(ids, { matchMode: "auto" });
    console.info("[canvas] POST /artifact-compare 响应体:", data);
    compareApiResult.value = data;
    const displayGraph = data?.display_subgraph || data?.displaySubgraph;
    const graphPayload =
      displayGraph?.nodes?.length ? displayGraph : data?.subgraph || { nodes: [], links: [] };
    multiComparePayload.value = {
      nodes: Array.isArray(graphPayload?.nodes) ? graphPayload.nodes : [],
      links: Array.isArray(graphPayload?.links) ? graphPayload.links : [],
      layout: graphPayload?.layout || "compare-align",
    };
  } catch (error) {
    multiComparePayload.value = { nodes: [], links: [] };
    compareApiResult.value = null;
    multiCompareError.value =
      error?.response?.data?.error ||
      error?.response?.data?.message ||
      error?.message ||
      "统一比较加载失败";
    console.error("[canvas] compare load:", error);
  } finally {
    multiCompareLoading.value = false;
    if (props.mode === "compare") {
      await loadCompareGraph();
    }
  }
}

async function loadCompareArtifactImages(ids) {
  const map = {};
  await Promise.all(
    ids.map(async (id) => {
      try {
        const { data } = await getArtifactImages(id);
        const paths = data?.image_paths || data?.imagePaths || [];
        map[id] = enrichImagePaths(paths);
      } catch {
        map[id] = [];
      }
    })
  );
  compareArtifactImagesMap.value = map;
}

async function loadPartCompare() {
  const ids = compareArtifactIds.value;
  if (props.mode !== "compare" || ids.length < 2) {
    partCompareResult.value = null;
    partCompareError.value = "";
    partCompareLoading.value = false;
    partCompareHighlightKey.value = "";
    compareArtifactImagesMap.value = {};
    return;
  }

  partCompareLoading.value = true;
  partCompareError.value = "";
  try {
    const [{ data }] = await Promise.all([
      postPartCompare(ids),
      loadCompareArtifactImages(ids),
    ]);
    partCompareResult.value = data?.meta?.ready ? data : null;
    if (!data?.meta?.ready) {
      partCompareError.value = data?.meta?.reason === "need_two_artifacts"
        ? "请至少选择 2 件文物"
        : "部件对照数据未就绪";
    }
  } catch (error) {
    partCompareResult.value = null;
    compareArtifactImagesMap.value = {};
    partCompareError.value =
      error?.response?.data?.error ||
      error?.response?.data?.message ||
      error?.message ||
      "部件对照加载失败";
    console.error("[canvas] part-compare load:", error);
  } finally {
    partCompareLoading.value = false;
  }
}

function onPartCompareRowClick(row) {
  if (!graphInstance?.highlightDiscoveryPath || !row) return;
  const key = String(row.slot_key || "");
  if (partCompareHighlightKey.value === key) {
    partCompareHighlightKey.value = "";
    compareHighlightKey.value = "";
    graphInstance.clearDiscoveryPath();
    return;
  }
  partCompareHighlightKey.value = key;
  compareHighlightKey.value = "";

  let highlightPath = null;
  const artifactIds = (partCompareResult.value?.artifacts || []).map((a) => a.id);
  for (const aid of artifactIds) {
    const cell = row.cells?.[aid];
    if (cell?.highlight_path?.node_ids?.length) {
      highlightPath = cell.highlight_path;
      break;
    }
  }
  if (!highlightPath) return;
  const normalized = normalizeHighlightPath(highlightPath);
  if (!normalized?.nodeIds?.length) return;
  graphInstance.highlightDiscoveryPath(buildSubgraphFromHighlightPath(normalized));
}
const discoveryView = computed(() =>
  buildDiscoveryView(
    selectedNodeIds.value.length ? selectedNodeIds.value[0] : props.artifact?.id,
    fullGraphData.value
  )
);

function linkRelationFromGraph(link) {
  return link.relation || link.label || "关联";
}

/** 将 discoveryEngine 的 highlightPath 对齐到主图节点与边上的 relation 字段，供 applyHighlightVisuals 匹配 */
function isMissingExpanded(artifactId) {
  return Boolean(compareExpandedMissing.value[String(artifactId)]);
}

function toggleMissingExpand(artifactId) {
  const key = String(artifactId);
  compareExpandedMissing.value = {
    ...compareExpandedMissing.value,
    [key]: !compareExpandedMissing.value[key],
  };
}

function visibleMissingItems(row) {
  const list = row.missing || [];
  if (isMissingExpanded(row.artifactId)) return list;
  return list.slice(0, compareMissingPreviewCount);
}

function onCompareHighlightClick(item) {
  if (!graphInstance?.highlightDiscoveryPath) return;
  const hp = compareApiResult.value?.meta?.ready
    ? item.displayHighlightPath || item.highlightPath
    : item.highlightPath;
  const normalized = normalizeHighlightPath(hp);
  if (!normalized?.nodeIds?.length) return;
  const key = String(item.key || "");
  if (compareHighlightKey.value === key) {
    compareHighlightKey.value = "";
    graphInstance.clearDiscoveryPath();
    return;
  }
  compareHighlightKey.value = key;
  graphInstance.highlightDiscoveryPath(buildSubgraphFromHighlightPath(normalized));
}

function compareGraphSource() {
  if (props.mode === "compare" && multiComparePayload.value?.nodes?.length) {
    return multiComparePayload.value;
  }
  return fullGraphData.value;
}

function buildSubgraphFromHighlightPath(highlightPath) {
  const full = compareGraphSource();
  if (!highlightPath?.nodeIds?.length || !full?.nodes?.length) return { nodes: [], links: [] };
  const idSet = new Set(highlightPath.nodeIds.map((id) => String(id)));
  const nodes = full.nodes.filter((n) => idSet.has(String(n.id)));
  const linksOut = [];
  for (const e of highlightPath.edges || []) {
    const s = String(e.source);
    const t = String(e.target);
    const rel = e.relation || "关联";
    const found = full.links.find((l) => {
      const ls = String(l.source?.id ?? l.source);
      const lt = String(l.target?.id ?? l.target);
      const lr = linkRelationFromGraph(l);
      return lr === rel && ((ls === s && lt === t) || (ls === t && lt === s));
    });
    if (found) {
      const lr = linkRelationFromGraph(found);
      linksOut.push({
        ...found,
        relation: lr,
        source: found.source?.id ?? found.source,
        target: found.target?.id ?? found.target,
      });
    } else {
      linksOut.push({ source: s, target: t, relation: rel });
    }
  }
  return { nodes, links: linksOut };
}

function buildSubgraphFromSegments(segments) {
  const nodeById = new Map();
  const linksOut = [];
  (segments || []).forEach((seg) => {
    const hp =
      (props.mode === "compare" && compareApiResult.value?.meta?.ready
        ? seg.displayHighlightPath || seg.highlightPath
        : seg.highlightPath || seg.displayHighlightPath) || seg.highlightPath;
    const sub = buildSubgraphFromHighlightPath(normalizeHighlightPath(hp));
    sub.nodes.forEach((n) => {
      const id = String(n.id);
      if (!nodeById.has(id)) nodeById.set(id, n);
    });
    sub.links.forEach((l) => linksOut.push(l));
  });
  return { nodes: [...nodeById.values()], links: linksOut };
}

function applySynthesisHighlight() {
  if (!graphInstance?.highlightDiscoveryPath) return;
  if (props.mode !== "discovery" && props.mode !== "compare") return;
  if (props.synthesisHighlightAll && props.synthesisSegments?.length) {
    graphInstance.highlightDiscoveryPath(buildSubgraphFromSegments(props.synthesisSegments));
    if (props.mode === "discovery") discoverySelectedKey.value = "";
    return;
  }
  if (props.synthesisSelectedSegmentId && props.synthesisSegments?.length) {
    const seg = props.synthesisSegments.find(
      (s) => String(s.id) === String(props.synthesisSelectedSegmentId)
    );
    if (seg?.highlightPath || seg?.displayHighlightPath) {
      const hp =
        props.mode === "compare" && compareApiResult.value?.meta?.ready
          ? seg.displayHighlightPath || seg.highlightPath
          : seg.highlightPath || seg.displayHighlightPath;
      graphInstance.highlightDiscoveryPath(buildSubgraphFromHighlightPath(normalizeHighlightPath(hp)));
      if (props.mode === "discovery") discoverySelectedKey.value = "";
    }
  }
}

function onDiscoveryCandidateClick(item) {
  if (!graphInstance?.highlightDiscoveryPath) return;
  const hp = item?.highlightPath;
  if (!hp?.nodeIds?.length) return;
  const key = String(item.key);
  emit("clear-synthesis-selection");
  if (discoverySelectedKey.value === key) {
    discoverySelectedKey.value = "";
    graphInstance.clearDiscoveryPath();
    return;
  }
  discoverySelectedKey.value = key;
  graphInstance.highlightDiscoveryPath(buildSubgraphFromHighlightPath(hp));
}

function resolveNodeForSynthesis(nodeId) {
  const id = String(nodeId);
  const node = fullGraphData.value.nodes.find((n) => String(n.id) === id);
  const fullName = node?.name || node?.label || id;
  return {
    label: truncateLabel(fullName, 10),
    fullName,
    artifact: Number(node?.is_artifact) === 1,
    description: String(node?.description || "").trim(),
    book: String(node?.book || node?.belongs_to || "").trim(),
  };
}

function onAddCompareEvidence(item, kind, missingRow = null) {
  if (!item?.key) return;
  const evidenceItem = buildCompareEvidenceItem({
    kind,
    item,
    compareArtifacts: props.compareList || [],
    graphNodes: compareGraphSource().nodes || fullGraphData.value.nodes || [],
    isCrossBook: isCrossBookCompare.value,
    missingRow,
  });
  emit("add-synthesis-segments", [evidenceItem]);
}

function onAddToSynthesis(row) {
  const hp = row?.item?.highlightPath;
  if (!hp?.nodeIds?.length) return;
  const parts = splitHighlightPathIntoSegments(hp, resolveNodeForSynthesis);
  if (!parts.length) return;
  const segments = parts.map((part) => ({
    ...enrichDiscoverySegment(
      { ...part, kind: "discovery" },
      fullGraphData.value.nodes || []
    ),
    id: createSegmentId(),
    fromCandidateKey: String(row.item.key),
  }));
  emit("add-synthesis-segments", segments);
}

function truncateLabel(text, max = 8) {
  if (text == null) return "";
  const s = String(text).trim();
  return s.length <= max ? s : `${s.slice(0, Math.max(1, max - 1))}…`;
}

/** 发现模式：每条候选的路径数据（SVG 条带 + 读屏文案） */
const discoveryCandidateRows = computed(() => {
  const byId = new Map((fullGraphData.value.nodes || []).map((n) => [String(n.id), n]));
  const list = discoveryView.value.extensionCandidates || [];
  return list.map((item) => {
    const hp = item.highlightPath;
    const ids = hp?.nodeIds?.length ? hp.nodeIds.map((id) => String(id)) : [];
    const edges = hp?.edges || [];
    const steps = [];
    let ariaLabel = "";
    if (ids.length >= 3) {
      const triple = ids.slice(0, 3);
      triple.forEach((id, i) => {
        const node = byId.get(id);
        steps.push({
          type: "node",
          id,
          label: truncateLabel(node?.name || node?.label || id, 10),
          artifact: Number(node?.is_artifact) === 1,
        });
        if (i < triple.length - 1) {
          steps.push({
            type: "rel",
            text: truncateLabel(edges[i]?.relation || edges[i]?.label || "关联", 9),
          });
        }
      });
      const n0 = byId.get(triple[0])?.name || triple[0];
      const n1 = byId.get(triple[1])?.name || triple[1];
      const n2 = byId.get(triple[2])?.name || triple[2];
      const r0 = edges[0]?.relation || edges[0]?.label || "关联";
      const r1 = edges[1]?.relation || edges[1]?.label || "关联";
      ariaLabel = `二跳路径：${n0} 经「${r0}」到 ${n1}，再经「${r1}」到 ${n2}`;
    }
    const stripNodes = steps.filter((s) => s.type === "node").map((s) => ({ label: s.label, artifact: s.artifact }));
    const stripRels = steps.filter((s) => s.type === "rel").map((s) => s.text);
    return { item, steps, stripNodes, stripRels, ariaLabel };
  });
});

function buildHubSpokeMiniGraph(items) {
  const centerId = selectedNodeIds.value[0];
  if (!centerId || !items.length) return null;

  const centerNode = fullGraphData.value.nodes.find((node) => String(node.id) === String(centerId));
  const centerLabel = truncateLabel(
    centerNode?.name ?? centerNode?.label ?? props.artifact?.name ?? String(centerId),
    12
  );

  const margin = 36;
  const n = items.length;
  const w = 340;
  const rowGap = 58;
  const h = Math.max(156, margin * 2 + n * rowGap);
  const cx = 76;
  const cy = h / 2;
  const cr = 34;
  const tr = 22;

  const edges = [];

  items.forEach((item, i) => {
    const ty = margin + ((i + 1) / (n + 1)) * (h - 2 * margin);
    const tx = w - margin - tr - 12;
    const dx = tx - cx;
    const dy = ty - cy;
    const len = Math.hypot(dx, dy) || 1;
    const ux = dx / len;
    const uy = dy / len;
    const x1 = cx + ux * cr;
    const y1 = cy + uy * cr;
    const x2 = tx - ux * tr;
    const y2 = ty - uy * tr;
    const midX = (x1 + x2) / 2 + uy * 16;
    const midY = (y1 + y2) / 2 - ux * 16;

    edges.push({
      x1,
      y1,
      x2,
      y2,
      midX,
      midY,
      relation: truncateLabel(item.relation, 14),
      targetLabel: truncateLabel(item.targetName, 12),
      tx,
      ty,
      tr,
    });
  });

  return {
    w,
    h,
    cx,
    cy,
    cr,
    centerLabel,
    edges,
  };
}

const baseLayerGraph = computed(() => buildHubSpokeMiniGraph(layerBuckets.value.base || []));
const uniqueLayerGraph = computed(() => buildHubSpokeMiniGraph(layerBuckets.value.unique || []));

function bucketizeRelations(selectedNodeId, graphData = fullGraphData.value) {
  const selectedId = String(selectedNodeId);
  const nodeMap = new Map(graphData.nodes.map((node) => [String(node.id), node]));
  const directLinks = graphData.links.filter((link) => {
    const sourceId = String(link.source?.id ?? link.source);
    const targetId = String(link.target?.id ?? link.target);
    return sourceId === selectedId || targetId === selectedId;
  });

  const base = [];
  const unique = [];
  const background = [];

  directLinks.forEach((link, index) => {
    const sourceId = String(link.source?.id ?? link.source);
    const targetId = String(link.target?.id ?? link.target);
    const relation = link.relation || link.label || "关联";
    const peerId = sourceId === selectedId ? targetId : sourceId;
    const peerNode = nodeMap.get(peerId);
    const item = {
      key: `${index}-${relation}-${peerId}`,
      relation,
      targetId: peerId,
      targetName: peerNode?.name || peerId,
    };

    const isBase = LAYER_RELATION_CONFIG.base.includes(relation);
    const isBackground =
      !isBase &&
      LAYER_RELATION_CONFIG.backgroundKeywords.some((keyword) => relation.includes(keyword));

    if (isBase) base.push(item);
    else if (isBackground) background.push(item);
    else unique.push(item);
  });

  layerBuckets.value = { base, unique, background };
}

function buildFocusNode() {
  const nodeId = selectedNodeIds.value[0] || "";
  if (!nodeId) return null;
  const node = getNodeById(nodeId);
  const name = node?.name || node?.label || props.artifact?.name || nodeId;
  const lb = layerBuckets.value;
  const neighborCount =
    (lb.base?.length || 0) + (lb.unique?.length || 0) + (lb.background?.length || 0);
  return {
    id: String(nodeId),
    name: String(name),
    isArtifact: node ? Number(node.is_artifact) === 1 : true,
    neighborCount,
  };
}

function buildModePanel() {
  if (props.mode === "compare") {
    const cv = compareView.value;
    const previews = [];
    (cv.differenceStructures || []).slice(0, 3).forEach((d) => {
      const vals = (d.values || []).slice(0, 2).join(" / ");
      previews.push({
        key: d.key,
        type: "diff",
        label: `${d.relation} · ${vals}${(d.values || []).length > 2 ? "…" : ""}`,
      });
    });
    (cv.conflictStructures || []).slice(0, 2).forEach((c) => {
      previews.push({
        key: c.key,
        type: "conflict",
        label: c.detail || c.relation,
      });
    });
    let missShown = 0;
    for (const row of cv.missingStructures || []) {
      if (missShown >= 2) break;
      for (const m of row.missing || []) {
        if (missShown >= 2) break;
        previews.push({
          key: m.key,
          type: "missing",
          label: `${row.artifactName}: ${m.label}`,
        });
        missShown += 1;
      }
    }
    const missingTotal = (cv.missingStructures || []).reduce(
      (sum, row) => sum + (row.total || 0),
      0
    );
    return {
      kind: "compare",
      ready: cv.meta?.ready === true,
      reason: cv.meta?.reason || "",
      artifactCount: (props.compareList || []).length,
      counts: {
        difference: (cv.differenceStructures || []).length,
        missing: missingTotal,
        conflict: (cv.conflictStructures || []).length,
        shared: (cv.sharedStructures || []).length,
      },
      previews,
      emptyHint: comparePanelsEmptyText.value,
    };
  }

  if (props.mode === "discovery") {
    const dv = discoveryView.value;
    const meta = dv.discoveryMeta || {};
    return {
      kind: "discovery",
      candidateTotal: (dv.extensionCandidates || []).length,
      truncated: !!meta.truncated,
      shown: meta.shown ?? (dv.extensionCandidates || []).length,
      total: meta.totalMerged ?? (dv.extensionCandidates || []).length,
      opportunityCount: (dv.knowledgeOpportunities || []).length,
      hint: "在中间列表浏览候选，用 + 加入证据合成台；右栏显示已关注与合成进度。",
    };
  }

  const lb = layerBuckets.value;
  return {
    kind: "artifact",
    layerCounts: {
      base: (lb.base || []).length,
      unique: (lb.unique || []).length,
      background: (lb.background || []).length,
    },
    hint: "点击主图节点查看关系分层与图片预览。",
  };
}

function emitGraphContextChange() {
  const focusNode = buildFocusNode();
  graphContext.value = {
    selectedArtifactId: selectedNodeIds.value[0] || "",
    focusNode,
    modePanel: buildModePanel(),
    evidencePayload: {
      nodeId: selectedNodeIds.value[0] || "",
      nodeName: focusNode?.name || props.artifact?.name || "",
      mode: props.mode,
    },
    relatedSubgraph: relatedSubgraph.value,
    layerBuckets: layerBuckets.value,
    candidates: discoveryView.value.extensionCandidates.slice(0, 5),
    aiSummary:
      props.mode === "compare"
        ? `比较 ${props.compareList.length} 件：差异 ${compareView.value.differenceStructures.length}，缺失项 ${(compareView.value.missingStructures || []).reduce((s, r) => s + (r.total || 0), 0)}，冲突 ${compareView.value.conflictStructures.length}。`
        : props.mode === "discovery"
          ? `发现模式：扩展候选 ${discoveryView.value.extensionCandidates.length} 条；请在中间主图与列表中探索，右栏跟踪关注与合成。`
          : `单文物：${focusNode?.name || props.artifact?.name || "未选择"}；基础层 ${layerBuckets.value.base.length}、特有层 ${layerBuckets.value.unique.length}、背景层 ${layerBuckets.value.background.length}。`,
  };
  emit("graph-context-change", graphContext.value);
}

function getNodeById(nodeId) {
  return fullGraphData.value.nodes.find((node) => String(node.id) === String(nodeId));
}

function findLinkedArtifactId(nodeId) {
  const nid = String(nodeId);
  const node = getNodeById(nid);
  if (node && Number(node.is_artifact) === 1) return nid;

  for (const link of fullGraphData.value.links || []) {
    const s = String(link.source?.id ?? link.source);
    const t = String(link.target?.id ?? link.target);
    if (s !== nid && t !== nid) continue;
    const otherId = s === nid ? t : s;
    const other = getNodeById(otherId);
    if (other && Number(other.is_artifact) === 1) return otherId;
  }
  return selectedNodeIds.value[0] || "";
}

function syncMultimodalFocus(payload) {
  const images = payload.imagePaths || [];
  const sourceText = payload.sourceText || "";
  const description = payload.description || "";
  multimodalFocus.value = {
    nodeId: payload.nodeId || "",
    nodeName: payload.nodeName || "",
    imagePaths: images,
    sourceText,
    description,
    highlightKeyword: payload.highlightKeyword || payload.nodeName || "",
    isArtifact: Boolean(payload.isArtifact),
    modality: resolveModality(images.length > 0, Boolean(sourceText || description)),
  };
}

function clearMultimodalFocus() {
  syncMultimodalFocus({
    nodeId: "",
    nodeName: "",
    imagePaths: [],
    sourceText: "",
    description: "",
    highlightKeyword: "",
    isArtifact: false,
  });
}

async function updateMultimodalForNode(node) {
  if (!node) {
    clearMultimodalFocus();
    return;
  }
  const nodeId = String(node.id);
  const nodeName = node.name || nodeId;
  const isArtifact = Number(node.is_artifact) === 1;
  const description = String(node.description || "").trim();
  const nodeImages = node.image_urls || node.imageUrls || [];

  let imagePaths = [...nodeImages];
  let sourceText = "";
  const artifactId = isArtifact ? nodeId : findLinkedArtifactId(nodeId);

  if (isArtifact) {
    try {
      const res = await getArtifactImages(nodeId);
      const apiPaths = res?.data?.image_paths || [];
      if (apiPaths.length) imagePaths = apiPaths;
    } catch (_) {
      /* use cache */
    }
  }

  if (artifactId) {
    try {
      const res = await getArtifactText(artifactId);
      sourceText = res?.data?.source_text || "";
    } catch (_) {
      /* use cache */
    }
    if (!sourceText) {
      const artNode = getNodeById(artifactId);
      sourceText = artNode?.source_text || artNode?.sourceText || "";
    }
  }

  const focusPayload = {
    nodeId,
    nodeName,
    imagePaths,
    sourceText: String(sourceText || ""),
    description,
    highlightKeyword: nodeName,
    isArtifact,
  };
  syncMultimodalFocus(focusPayload);

  emit("artifact-images-change", {
    artifactId: isArtifact ? nodeId : artifactId,
    nodeName,
    imagePaths,
  });
  emit("artifact-text-change", {
    artifactId: isArtifact ? nodeId : artifactId,
    nodeName,
    sourceText: focusPayload.sourceText,
    description,
  });
}

async function handleNodeSelect(ids, currentNode, isCancel) {
  discoverySelectedKey.value = "";
  selectedNodeIds.value = [...ids];

  if (!isCancel && currentNode) {
    emit("artifact-queue-enqueue", {
      id: String(currentNode.id),
      name: currentNode.name || String(currentNode.id),
      raw: currentNode,
    });
  }

  if (ids.length === 1 && !isCancel) {
    const selectedId = ids[0];
    const selectedNode = currentNode || getNodeById(selectedId);
    bucketizeRelations(selectedId);
    relatedSubgraph.value = {
      nodes: [selectedNode].filter(Boolean),
      links: [],
    };
    await updateMultimodalForNode(selectedNode);
  } else {
    layerBuckets.value = { base: [], unique: [], background: [] };
    relatedSubgraph.value = { nodes: [], links: [] };
    clearMultimodalFocus();
    emit("artifact-images-change", { artifactId: "", nodeName: "", imagePaths: [] });
    emit("artifact-text-change", { artifactId: "", nodeName: "", sourceText: "" });
  }

  emitGraphContextChange();
}

function handleNonArtifact(nodeData, _event, status) {
  if (status !== "DATA_READY") return;
  discoverySelectedKey.value = "";
  relatedSubgraph.value = {
    nodes: [nodeData],
    links: [],
  };
  void updateMultimodalForNode(nodeData);
  emitGraphContextChange();
}

function handleClearUI() {
  discoverySelectedKey.value = "";
  compareHighlightKey.value = "";
  selectedNodeIds.value = [];
  layerBuckets.value = { base: [], unique: [], background: [] };
  relatedSubgraph.value = { nodes: [], links: [] };
  clearMultimodalFocus();
  emit("artifact-images-change", { artifactId: "", nodeName: "", imagePaths: [] });
  emit("artifact-text-change", { artifactId: "", nodeName: "", sourceText: "" });
  emitGraphContextChange();
}

async function reloadGraphForBooks() {
  handleClearUI();
  fullGraphData.value = { nodes: [], links: [] };
  multiComparePayload.value = { nodes: [], links: [] };
  compareApiResult.value = null;
  await loadFullGraphSnapshot();
  await loadGraph();
  if (props.mode === "compare" && compareArtifactIds.value.length >= 2) {
    await loadMultiCompareSubgraph();
  }
}

function normalizeGraphPayload(data) {
  const nodes = data?.nodes || [];
  const links = (data?.links || []).filter((link) => {
    const nodeIds = new Set(nodes.map((node) => String(node.id)));
    const sourceId = String(link.source?.id ?? link.source);
    const targetId = String(link.target?.id ?? link.target);
    return nodeIds.has(sourceId) && nodeIds.has(targetId);
  });
  return {
    nodes,
    links,
    layout: data?.layout || null,
  };
}

const compareShowUnique = ref(false);

function filterCompareGraphPayload(payload) {
  if (compareShowUnique.value || payload.layout !== "compare-align") {
    return payload;
  }
  const hideIds = new Set(
    payload.nodes.filter((n) => n.role === "unique").map((n) => String(n.id))
  );
  return {
    ...payload,
    nodes: payload.nodes.filter((n) => !hideIds.has(String(n.id))),
    links: payload.links.filter((l) => {
      const targetId = String(l.target?.id ?? l.target);
      return !hideIds.has(targetId);
    }),
  };
}

function onGraphVizOptionsUpdate(next) {
  graphVizOptions.value = { ...graphVizOptions.value, ...next };
  graphInstance?.setVizOptions?.({ ...graphVizOptions.value });
}

function onGraphFit() {
  graphInstance?.fitView?.() || graphInstance?.zoom?.fit?.();
}

function onGraphZoomIn() {
  graphInstance?.zoom?.in?.();
}

function onGraphZoomOut() {
  graphInstance?.zoom?.out?.();
}

function onGraphZoomReset() {
  graphInstance?.zoom?.reset?.();
}

function mountGraphInstance(graphData) {
  if (!svgRef.value) return;
  const { nodes, links, layout } = graphData;
  svgRef.value.innerHTML = "";
  graphInstance = initGraph(
    svgRef.value,
    { nodes, links, layout, vizOptions: { ...graphVizOptions.value } },
    {
    onNodeSelect: handleNodeSelect,
    onSubgraphUpdate: (subgraph) => {
      relatedSubgraph.value = subgraph || { nodes: [], links: [] };
      if (selectedNodeIds.value.length === 1) {
        bucketizeRelations(selectedNodeIds.value[0], subgraph || fullGraphData.value);
      }
      emitGraphContextChange();
    },
    onHandleNonArtifact: handleNonArtifact,
    onClearUI: handleClearUI,
    }
  );
}

async function loadFullGraphSnapshot() {
  graphLoadError.value = "";
  try {
    const books =
      props.selectedBooks.length > 0
        ? props.selectedBooks
        : booksToQueryCodes(props.availableBooks);
    const { data } = await getGraphData(books);
    fullGraphData.value = normalizeGraphPayload(data);
  } catch (error) {
    graphLoadError.value = error?.message || "主图数据加载失败";
    console.error("[canvas] 主图数据加载失败:", error);
  }
}

async function loadCompareGraph() {
  await nextTick();
  if (props.mode !== "compare") return;
  if (compareArtifactIds.value.length < 2) return;
  if (multiCompareLoading.value || multiCompareError.value) return;
  if (!multiComparePayload.value.nodes?.length) return;
  if (!svgRef.value) return;

  const rect = svgRef.value.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return;

  const graphData = filterCompareGraphPayload(normalizeGraphPayload(multiComparePayload.value));
  mountGraphInstance(graphData);
  if (compareHighlightKey.value) {
    const diff = compareView.value.differenceStructures.find(
      (d) => d.key === compareHighlightKey.value
    );
    const conflict = compareView.value.conflictStructures.find(
      (c) => c.key === compareHighlightKey.value
    );
    const missing = compareView.value.missingStructures
      .flatMap((r) => r.missing)
      .find((m) => m.key === compareHighlightKey.value);
    const item = diff || conflict || missing;
    const hp = compareApiResult.value?.meta?.ready
      ? item?.displayHighlightPath || item?.highlightPath
      : item?.highlightPath;
    const normalized = normalizeHighlightPath(hp);
    if (normalized?.nodeIds?.length) {
      graphInstance?.highlightDiscoveryPath(buildSubgraphFromHighlightPath(normalized));
    }
  }
}

async function loadGraph() {
  await nextTick();
  if (props.mode === "compare") {
    await loadFullGraphSnapshot();
    await loadCompareGraph();
    emitGraphContextChange();
    return;
  }
  if (!svgRef.value) return;

  const rect = svgRef.value.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return;

  try {
    if (!fullGraphData.value.nodes?.length) {
      await loadFullGraphSnapshot();
    }
    const graphData = fullGraphData.value;
    mountGraphInstance(graphData);
    emitGraphContextChange();
  } catch (error) {
    console.error("图谱加载失败:", error);
  }
}

watch(
  () => props.selectedBooks.join(","),
  async () => {
    if (!props.booksReady) return;
    await reloadGraphForBooks();
  }
);

watch(
  () => props.booksReady,
  async (ready) => {
    if (!ready) return;
    await loadFullGraphSnapshot();
    await loadGraph();
  },
  { immediate: true }
);

watch(
  () => props.artifact.id,
  () => {
    discoverySelectedKey.value = "";
    if (props.mode === "artifact" || props.mode === "discovery") loadGraph();
  }
);

watch(
  () => ({ mode: props.mode, idsKey: compareArtifactIds.value.join("\u0001") }),
  async () => {
    if (props.mode !== "compare") {
      multiComparePayload.value = { nodes: [], links: [] };
      compareApiResult.value = null;
      multiCompareError.value = "";
      multiCompareLoading.value = false;
      partCompareResult.value = null;
      partCompareError.value = "";
      partCompareLoading.value = false;
      compareArtifactImagesMap.value = {};
      compareHighlightKey.value = "";
      partCompareHighlightKey.value = "";
      return;
    }
    compareHighlightKey.value = "";
    partCompareHighlightKey.value = "";
    compareExpandedMissing.value = {};
    if (isCrossBookCompare.value) {
      const booksBefore = props.selectedBooks.join(",");
      ensureSelectedBooksForCompare(compareArtifactIds.value);
      await nextTick();
      if (props.selectedBooks.join(",") !== booksBefore) {
        return;
      }
    }
    await loadFullGraphSnapshot();
    await Promise.all([loadMultiCompareSubgraph(), loadPartCompare()]);
    emitGraphContextChange();
  },
  { immediate: true }
);

watch(
  () => props.mode,
  (mode) => {
    if (mode !== "discovery") discoverySelectedKey.value = "";
    if (mode !== "compare") compareHighlightKey.value = "";
    if (mode === "artifact" || mode === "discovery" || mode === "compare") loadGraph();
    emitGraphContextChange();
  }
);

watch(
  () => props.compareList,
  () => emitGraphContextChange(),
  { deep: true }
);

watch(
  () => discoveryView.value.extensionCandidates?.length,
  () => {
    if (props.mode === "discovery") emitGraphContextChange();
  }
);

watch(
  () => [
    props.synthesisSegments,
    props.synthesisSelectedSegmentId,
    props.synthesisHighlightAll,
    props.mode,
  ],
  () => {
    if (props.mode !== "discovery" && props.mode !== "compare") return;
    if (props.synthesisHighlightAll || props.synthesisSelectedSegmentId) {
      applySynthesisHighlight();
    }
  },
  { deep: true }
);
</script>

<style scoped>
.visual-canvas {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.canvas-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 16px;
}

.canvas-focus-switch {
  flex-shrink: 0;
  align-self: center;
}

.canvas-header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex: 0 1 auto;
}

.canvas-mode-switch {
  flex-shrink: 0;
}

.canvas-content {
  flex: 1;
  min-height: 0;
}

.artifact-layout {
  flex: 1;
  display: flex;
  gap: 20px;
  min-height: 0;
}

.graph-container {
  flex: 1;
  min-height: 0;
  width: 100%;
  background: #fdfaf5;
  position: relative;
  border: 1px solid #eee;
}

.graph-container > svg {
  display: block;
  width: 100% !important;
  height: 100% !important;
}

:deep(.hidden) {
  display: none !important;
}

.layer-block,
.info-block {
  display: flex;
  flex-direction: column;
  justify-content: flex-start !important;
  padding: 44px 8px 8px;
  overflow-y: auto;
}

.relation-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rel-item {
  background: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(184, 159, 119, 0.16);
  border-radius: 8px;
  padding: 6px 8px;
  font-size: 12px;
  text-align: left;
  display: grid;
  gap: 4px;
}

.rel-label {
  color: var(--accent);
  font-weight: 700;
}

.empty-hint {
  color: var(--muted);
  font-size: 12px;
}

.conflict-item {
  border-color: rgba(184, 103, 83, 0.42);
}

.multi-shared-head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}

.multi-shared-name {
  font-size: 13px;
}

.multi-shared-meta {
  color: var(--muted);
  font-size: 11px;
}

.multi-compare-summary {
  line-height: 1.45;
}

.multi-compare-hint {
  margin-top: 6px;
  line-height: 1.45;
}

.multi-compare-debug {
  margin: 8px 0;
  font-size: 12px;
  color: var(--text, #3f3427);
}

.multi-compare-debug summary {
  cursor: pointer;
  color: var(--accent);
  font-weight: 600;
}

.multi-compare-json {
  margin: 8px 0 0;
  padding: 8px;
  max-height: 240px;
  overflow: auto;
  font-size: 11px;
  line-height: 1.35;
  white-space: pre-wrap;
  word-break: break-all;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
  border: 1px solid rgba(184, 159, 119, 0.25);
}

.compare-graph-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.compare-graph-block {
  min-height: min(320px, 42vh);
  width: 100%;
}

.compare-graph-placeholder {
  display: grid;
  place-items: center;
  padding: 24px;
  min-height: min(200px, 32vh);
}

.compare-graph-caption {
  margin: 0;
  line-height: 1.45;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}

.compare-align-lead {
  flex: 1 1 100%;
}

.compare-mode-tag {
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  background: rgba(95, 135, 124, 0.14);
  color: #2a4a42;
}

.compare-legend {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-left: 8px;
}

.legend-dot::before {
  content: "";
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}

.legend-artifact::before {
  background: linear-gradient(90deg, #4a90d9 50%, #e67e22 50%);
}

.legend-shared::before {
  background: #66bb6a;
  border: 1px solid #2e7d32;
}

.legend-unique::before {
  background: #bcaaa4;
}

.compare-unique-toggle {
  margin-left: 12px;
  font-size: 12px;
  cursor: pointer;
  user-select: none;
}

.compare-unique-toggle input {
  margin-right: 4px;
  vertical-align: middle;
}

.compare-panel-block {
  align-items: flex-start !important;
  justify-content: flex-start !important;
}

.compare-block-hint {
  width: 100%;
  margin: 0 0 8px;
  line-height: 1.4;
  text-align: left;
}

.compare-clickable-row {
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}

.compare-clickable-row:hover {
  border-color: rgba(95, 135, 124, 0.45);
  background: rgba(255, 255, 255, 0.78);
}

.compare-clickable-row.active {
  border-color: rgba(210, 120, 60, 0.7);
  background: rgba(255, 248, 238, 0.95);
  box-shadow: 0 0 0 1px rgba(210, 120, 60, 0.22);
}

.compare-missing-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: left;
}

.compare-missing-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
}

.compare-missing-count {
  font-size: 11px;
  color: var(--muted);
}

.compare-missing-line {
  font-size: 12px;
  padding: 5px 8px;
  border-radius: 8px;
  border: 1px solid rgba(184, 159, 119, 0.22);
  background: rgba(255, 255, 255, 0.5);
}

.compare-missing-none {
  margin: 0;
}

.compare-expand-btn {
  align-self: flex-start;
  border: 0;
  background: transparent;
  color: var(--accent, #5f877c);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 0;
}

.compare-expand-btn:hover {
  text-decoration: underline;
}

.discovery-rules-hint {
  margin-bottom: 6px;
  line-height: 1.4;
}

.discovery-task-lead {
  margin: 0;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--text, #3f3427);
  background: rgba(95, 135, 124, 0.08);
  border: 1px solid rgba(95, 135, 124, 0.22);
  border-radius: 10px;
}

.discovery-side-scroll {
  flex: 0 0 min(420px, 44%);
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.discovery-candidates-block {
  min-height: 0;
}

.discovery-candidate-list {
  gap: 10px;
}

.discovery-candidate-row {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: 8px;
  text-align: left;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}

.discovery-candidate-main {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.discovery-candidate-main:focus-visible {
  outline: 2px solid rgba(95, 135, 124, 0.55);
  outline-offset: 2px;
  border-radius: 8px;
}

.discovery-add-synthesis {
  flex-shrink: 0;
  align-self: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid rgba(95, 135, 124, 0.45);
  background: rgba(95, 135, 124, 0.14);
  color: #2a4a42;
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.discovery-add-synthesis:hover {
  background: rgba(95, 135, 124, 0.28);
  border-color: rgba(95, 135, 124, 0.65);
}

.compare-evidence-row {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: 8px;
}

.compare-evidence-main {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.compare-add-evidence {
  align-self: center;
  width: 32px;
  height: 32px;
  font-size: 20px;
}

.discovery-candidate-row:hover {
  border-color: rgba(95, 135, 124, 0.45);
  background: rgba(255, 255, 255, 0.72);
}

.discovery-candidate-row.active {
  border-color: rgba(95, 135, 124, 0.65);
  background: rgba(95, 135, 124, 0.12);
  box-shadow: 0 0 0 1px rgba(95, 135, 124, 0.18);
}

.discovery-path-strip-wrap {
  width: 100%;
  border-radius: 8px;
  background: rgba(255, 252, 248, 0.65);
  border: 1px solid rgba(184, 159, 119, 0.22);
  padding: 4px 6px;
}

.discovery-path-reason-line {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid rgba(184, 159, 119, 0.2);
  font-size: 10px;
  line-height: 1.4;
  color: var(--muted);
  word-break: break-word;
}

.discovery-path-fallback {
  font-size: 12px;
}

.discovery-candidate-name {
  font-weight: 700;
  color: var(--text, #3f3427);
}

.discovery-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  min-height: 0;
}

.discovery-chain-list {
  max-height: min(280px, 38vh);
  overflow-y: auto;
}

.discovery-chain-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: left;
}

.discovery-chain-caption {
  margin: 0;
  font-size: 10px;
  line-height: 1.45;
  color: var(--muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.discovery-chain-caption--solo {
  -webkit-line-clamp: 4;
  font-size: 11px;
}

.discovery-truncate-hint {
  margin-bottom: 6px;
}

.mini-graph-wrap {
  flex: 1;
  min-height: 168px;
  width: 100%;
  border-radius: 12px;
  border: 1px solid rgba(184, 159, 119, 0.28);
  background: rgba(255, 252, 246, 0.55);
  display: grid;
  place-items: stretch;
  overflow: auto;
}

.base-layer-mini-svg {
  width: 100%;
  height: auto;
  min-height: 168px;
  max-height: min(360px, 55vh);
  display: block;
}

.mini-edge-line {
  stroke: rgba(184, 159, 119, 0.72);
  stroke-width: 2.25;
  fill: none;
}

.mini-edge-label {
  font-size: 12px;
  font-weight: 600;
  fill: rgba(63, 52, 39, 0.92);
}

.mini-node-mini {
  stroke: rgba(184, 159, 119, 0.55);
  stroke-width: 1.75;
}

.mini-node-center {
  fill: rgba(95, 135, 124, 0.42);
}

.mini-node-tail {
  fill: rgba(255, 250, 243, 0.98);
}

.mini-edge-line-unique {
  stroke: rgba(145, 112, 72, 0.68);
}

.mini-node-center-unique {
  fill: rgba(145, 112, 72, 0.38);
}

.mini-node-tail-unique {
  fill: rgba(255, 248, 238, 0.98);
}

.mini-node-label {
  font-size: 13px;
  font-weight: 600;
  fill: var(--text, #3f3427);
  pointer-events: none;
}
</style>

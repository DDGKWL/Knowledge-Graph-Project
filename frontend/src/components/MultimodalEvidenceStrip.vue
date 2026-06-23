<template>
  <section class="multimodal-strip panel" aria-label="多模态证据带">
    <div class="mm-strip-head">
      <div class="mm-strip-title-row">
        <span class="mm-strip-eyebrow">多模态证据</span>
        <span v-if="focus.nodeName" class="mm-focus-name">{{ focus.nodeName }}</span>
        <span v-else class="mm-focus-name muted">点击主图节点查看图文证据</span>
        <span
          v-if="modality !== 'none'"
          class="mm-modality-badge"
          :class="`mm-modality-${modality}`"
        >
          {{ modalityLabel }}
        </span>
      </div>
      <div class="mm-strip-meta">
        <span v-if="labeledImages.length">{{ filteredImages.length }}/{{ labeledImages.length }} 张图</span>
        <span v-if="labeledImages.length && focus.sourceText"> · </span>
        <span v-if="focus.sourceText">{{ textLength }} 字原文</span>
        <span v-if="focus.description && !focus.sourceText"> · 属性描述</span>
        <span v-if="labeledImages.length" class="mm-auto-label-hint"> · 弱监督自动分类，仅供参考</span>
      </div>
      <div v-if="labeledImages.length && showImageFilters" class="mm-part-chip-row">
        <button
          v-for="chip in filterOptions"
          :key="chip.id"
          type="button"
          class="mm-part-chip"
          :class="{ active: imageFilter === chip.id }"
          @click="imageFilter = chip.id"
        >
          {{ chip.label }}
        </button>
      </div>
      <div class="mm-tab-row">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          class="mm-tab"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div class="mm-strip-body">
      <div v-if="activeTab === 'combined'" class="mm-combined">
        <div class="mm-combined-images">
          <div v-if="!labeledImages.length" class="mm-empty">暂无关联图片</div>
          <div v-else-if="!filteredImages.length" class="mm-empty">
            当前筛选无图片，请切换「全部」
          </div>
          <button
            v-for="(item, idx) in filteredImages"
            :key="`${item.url}-${idx}`"
            type="button"
            class="mm-thumb-btn"
            @click="openImage(item)"
          >
            <img :src="item.url" :alt="item.label" class="mm-thumb" />
            <span class="mm-thumb-label" :class="{ unclassified: !item.classified }">{{ item.label }}</span>
          </button>
        </div>
        <div class="mm-combined-text">
          <div v-if="focus.description" class="mm-desc-block">
            <div class="mm-block-label">节点描述</div>
            <p>{{ focus.description }}</p>
          </div>
          <div v-if="highlightedSourceHtml" class="mm-source-block">
            <div class="mm-block-label">
              源文摘录
              <span v-if="focus.highlightKeyword" class="mm-hl-hint">已高亮「{{ focus.highlightKeyword }}」</span>
            </div>
            <div class="mm-source-scroll" v-html="highlightedSourceHtml" />
          </div>
          <div v-else-if="!focus.description" class="mm-empty">暂无源文，请选择文物或属性节点</div>
        </div>
      </div>

      <div v-else-if="activeTab === 'images'" class="mm-images-only">
        <div v-if="!labeledImages.length" class="mm-empty">暂无图片</div>
        <div v-else-if="!filteredImages.length" class="mm-empty">
          当前筛选无图片，请切换「全部」
        </div>
        <div v-else class="mm-image-grid">
          <figure v-for="(item, idx) in filteredImages" :key="`${item.url}-${idx}`" class="mm-figure">
            <img :src="item.url" :alt="item.label" class="mm-image-large" @click="openImage(item)" />
            <figcaption :class="{ unclassified: !item.classified }">{{ item.label }}</figcaption>
          </figure>
        </div>
      </div>

      <div v-else class="mm-text-only">
        <div v-if="focus.description" class="mm-desc-block standalone">
          <div class="mm-block-label">属性描述</div>
          <p>{{ focus.description }}</p>
        </div>
        <div v-if="highlightedSourceHtml" class="mm-source-scroll standalone" v-html="highlightedSourceHtml" />
        <div v-if="!highlightedSourceHtml && !focus.description" class="mm-empty">暂无源文</div>
      </div>
    </div>

    <div v-if="showLargeImage" class="mm-lightbox" @click="closeLightbox">
      <div class="mm-lightbox-inner" @click.stop>
        <div v-if="currentLargeLabel" class="mm-lightbox-caption">
          {{ currentLargeLabel }}
          <span class="mm-lightbox-caption-hint">自动分类</span>
        </div>
        <img :src="currentLargeImage" alt="大图预览" class="mm-lightbox-img" />
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { highlightKeywordHtml, resolveModality } from "@/utils/textHighlight";
import {
  collectImageFilterOptions,
  enrichImagePaths,
  filterLabeledImages,
} from "@/utils/imageLabelUtils";

const props = defineProps({
  focus: {
    type: Object,
    default: () => ({
      nodeId: "",
      nodeName: "",
      imagePaths: [],
      sourceText: "",
      description: "",
      highlightKeyword: "",
      isArtifact: false,
    }),
  },
});

const tabs = [
  { id: "combined", label: "综合" },
  { id: "images", label: "图片" },
  { id: "text", label: "源文" },
];

const activeTab = ref("combined");
const imageFilter = ref("all");
const showLargeImage = ref(false);
const currentLargeImage = ref("");
const currentLargeLabel = ref("");

const labeledImages = computed(() => enrichImagePaths(props.focus.imagePaths || []));

const filterOptions = computed(() => collectImageFilterOptions(labeledImages.value));

const filteredImages = computed(() => filterLabeledImages(labeledImages.value, imageFilter.value));

const showImageFilters = computed(() => filterOptions.value.length > 2);

const modality = computed(() =>
  resolveModality(
    labeledImages.value.length > 0,
    Boolean(props.focus.sourceText || props.focus.description)
  )
);

const modalityLabel = computed(() => {
  const map = { both: "图文", image: "图", text: "文", none: "" };
  return map[modality.value] || "";
});

const textLength = computed(() => String(props.focus.sourceText || "").length);

const highlightedSourceHtml = computed(() => {
  const text = props.focus.sourceText || "";
  if (!text) return "";
  return highlightKeywordHtml(text, props.focus.highlightKeyword || props.focus.nodeName);
});

watch(
  () => props.focus.nodeId,
  () => {
    activeTab.value = "combined";
    imageFilter.value = "all";
  }
);

function openImage(item) {
  const url = typeof item === "string" ? item : item?.url;
  if (!url) return;
  currentLargeImage.value = url;
  if (typeof item === "object" && item?.label) {
    currentLargeLabel.value = item.label;
  } else {
    currentLargeLabel.value = enrichImagePaths([url])[0]?.label || "";
  }
  showLargeImage.value = true;
}

function closeLightbox() {
  showLargeImage.value = false;
  currentLargeLabel.value = "";
}
</script>

<style scoped>
.multimodal-strip {
  flex-shrink: 0;
  margin-top: 10px;
  padding: 10px 14px 12px;
  border-radius: 14px;
  max-height: 260px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.mm-strip-head {
  flex-shrink: 0;
}

.mm-strip-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.mm-strip-eyebrow {
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted, #7b6b59);
}

.mm-focus-name {
  font-weight: 700;
  font-size: 14px;
  color: var(--text, #3f3427);
}

.mm-focus-name.muted {
  font-weight: 500;
  color: var(--muted, #7b6b59);
}

.mm-modality-badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(184, 159, 119, 0.45);
}

.mm-modality-both {
  background: rgba(95, 135, 124, 0.15);
  color: #3d6b62;
}

.mm-modality-image {
  background: rgba(74, 144, 217, 0.12);
  color: #2a5f9e;
}

.mm-modality-text {
  background: rgba(184, 159, 119, 0.18);
  color: #6d5340;
}

.mm-strip-meta {
  font-size: 11px;
  color: var(--muted, #7b6b59);
  margin: 4px 0 6px;
}

.mm-auto-label-hint {
  font-style: italic;
  opacity: 0.85;
}

.mm-part-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 6px;
}

.mm-part-chip {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid rgba(184, 159, 119, 0.4);
  background: rgba(255, 255, 255, 0.65);
  color: var(--text, #3f3427);
  cursor: pointer;
}

.mm-part-chip.active {
  background: rgba(74, 144, 217, 0.16);
  border-color: rgba(74, 144, 217, 0.45);
  color: #2a5f9e;
  font-weight: 600;
}

.mm-tab-row {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.mm-tab {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid rgba(184, 159, 119, 0.4);
  background: rgba(255, 255, 255, 0.6);
  color: var(--text, #3f3427);
}

.mm-tab.active {
  background: rgba(95, 135, 124, 0.18);
  border-color: rgba(95, 135, 124, 0.45);
  color: #2f5c52;
  font-weight: 600;
}

.mm-strip-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.mm-combined {
  display: grid;
  grid-template-columns: minmax(120px, 28%) 1fr;
  gap: 12px;
  height: 100%;
  min-height: 0;
}

.mm-combined-images {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  align-items: flex-start;
  padding-bottom: 4px;
}

.mm-thumb-btn {
  position: relative;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 8px;
  background: none;
  flex-shrink: 0;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.mm-thumb-btn:hover {
  border-color: rgba(95, 135, 124, 0.5);
}

.mm-thumb {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 6px;
  display: block;
}

.mm-thumb-label {
  font-size: 10px;
  line-height: 1.2;
  max-width: 76px;
  text-align: center;
  color: #2a5f9e;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mm-thumb-label.unclassified {
  color: var(--muted, #7b6b59);
  font-weight: 500;
}

.mm-combined-text {
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mm-block-label {
  font-size: 10px;
  color: var(--muted, #7b6b59);
  margin-bottom: 2px;
}

.mm-hl-hint {
  margin-left: 6px;
  color: #b86753;
}

.mm-desc-block p {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
}

.mm-source-scroll {
  font-size: 12px;
  line-height: 1.55;
  overflow-y: auto;
  max-height: 88px;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text, #3f3427);
}

.mm-source-scroll.standalone {
  max-height: 120px;
}

.mm-source-scroll :deep(.text-highlight-mark) {
  background: rgba(230, 81, 0, 0.22);
  color: #bf360c;
  padding: 0 2px;
  border-radius: 2px;
}

.mm-empty {
  font-size: 12px;
  color: var(--muted, #7b6b59);
  padding: 8px 0;
}

.mm-image-grid {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.mm-figure {
  margin: 0;
  flex-shrink: 0;
}

.mm-image-large {
  height: 100px;
  max-width: 160px;
  object-fit: cover;
  border-radius: 8px;
  cursor: zoom-in;
  border: 1px solid rgba(184, 159, 119, 0.35);
}

.mm-figure figcaption {
  font-size: 11px;
  color: #2a5f9e;
  font-weight: 600;
  text-align: center;
  margin-top: 4px;
}

.mm-figure figcaption.unclassified {
  color: var(--muted, #7b6b59);
  font-weight: 500;
}

.mm-lightbox {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(20, 16, 12, 0.82);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.mm-lightbox-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  max-width: min(92vw, 960px);
}

.mm-lightbox-caption {
  color: #f5f0e8;
  font-size: 14px;
  font-weight: 600;
}

.mm-lightbox-caption-hint {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 400;
  opacity: 0.75;
}

.mm-lightbox-img {
  max-width: min(92vw, 960px);
  max-height: 82vh;
  object-fit: contain;
  border-radius: 8px;
}
</style>

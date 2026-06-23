<template>
  <section class="part-compare-panel panel" aria-label="部件级对照">
    <div class="part-compare-head">
      <div>
        <div class="part-compare-title">部件级对照</div>
        <p class="part-compare-sub empty-hint">
          按标准部件 × 谓词对齐；有部件图时在单元格内显示（弱监督分类）。
          点击行可在上方子图高亮证据链。
          <span v-if="summary.total_slots != null">共 {{ summary.total_slots }} 个 slot</span>
        </p>
      </div>
      <div class="part-compare-filters">
        <label class="part-filter-item">
          <span>差异类型</span>
          <select v-model="localDiffKind" class="part-filter-select">
            <option value="all">全部</option>
            <option v-for="opt in diffKindOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </label>
        <label class="part-filter-item">
          <span>语义层</span>
          <select v-model="localLayer" class="part-filter-select">
            <option value="all">全部</option>
            <option v-for="layer in layerOptions" :key="layer" :value="layer">{{ layer }}</option>
          </select>
        </label>
        <label class="part-filter-item part-filter-grow">
          <span>搜索部件/谓词</span>
          <input v-model="localPartKw" type="search" class="part-filter-input" placeholder="如 龙池、灰胎" />
        </label>
        <label class="part-filter-item part-filter-check">
          <input v-model="hideShared" type="checkbox" />
          隐藏共享行
        </label>
      </div>
    </div>

    <div v-if="loading" class="part-compare-empty empty-hint">正在加载部件对照…</div>
    <div v-else-if="error" class="part-compare-empty empty-hint">{{ error }}</div>
    <div v-else-if="!artifacts.length" class="part-compare-empty empty-hint">
      请至少选择 2 件文物以加载部件对照表。
    </div>
    <div v-else-if="!filteredRows.length" class="part-compare-empty empty-hint">当前筛选下无对照行。</div>

    <div v-else class="part-compare-table-wrap">
      <table class="part-compare-table">
        <thead>
          <tr>
            <th>部件</th>
            <th>谓词</th>
            <th>层</th>
            <th>类型</th>
            <th v-for="art in artifacts" :key="art.id" class="part-col-artifact">
              {{ columnLabel(art) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in filteredRows"
            :key="row.slot_key"
            class="part-compare-row"
            :class="{ active: selectedSlotKey === row.slot_key, [`row-${diffClass(row.diff_kind)}`]: true }"
            tabindex="0"
            role="button"
            @click="onRowClick(row)"
            @keydown.enter.prevent="onRowClick(row)"
          >
            <td class="part-cell-name">{{ row.canonical_part_label }}</td>
            <td>{{ row.predicate }}</td>
            <td class="part-cell-layer">{{ row.semantic_layer }}</td>
            <td>
              <span class="part-diff-badge" :class="diffClass(row.diff_kind)">
                {{ diffLabel(row.diff_kind) }}
              </span>
            </td>
            <td
              v-for="art in artifacts"
              :key="`${row.slot_key}-${art.id}`"
              class="part-cell-value"
              :class="{ missing: !cellPresent(row, art.id) && !cellPartImages(row, art.id).length }"
            >
              <div class="part-cell-inner">
                <template v-if="cellPresent(row, art.id)">
                  <span
                    v-if="row.inscription_diff && !row.inscription_diff.equal"
                    class="part-inscription-diff"
                    :title="inscriptionTitle(row.inscription_diff)"
                  >
                    {{ inscriptionPreview(row.inscription_diff) }}
                  </span>
                  <span v-else :title="cellValue(row, art.id)">{{ truncate(cellValue(row, art.id)) }}</span>
                </template>
                <span v-else-if="!cellPartImages(row, art.id).length" class="part-missing-mark">未载</span>
                <div v-if="cellPartImages(row, art.id).length" class="part-cell-images">
                  <button
                    v-for="(img, imgIdx) in cellPartImages(row, art.id)"
                    :key="`${img.url}-${imgIdx}`"
                    type="button"
                    class="part-cell-thumb-btn"
                    :title="`${img.label} · 点击查看大图`"
                    @click.stop="openImage(img)"
                  >
                    <img :src="img.url" :alt="img.label" class="part-cell-thumb" />
                  </button>
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="summary.by_diff_kind && !loading" class="part-compare-summary">
      <span v-for="(count, kind) in summary.by_diff_kind" :key="kind" class="part-summary-chip">
        {{ diffLabel(kind) }} {{ count }}
      </span>
    </div>

    <div v-if="showLargeImage" class="part-image-lightbox" @click="closeLightbox">
      <div class="part-lightbox-inner" @click.stop>
        <div v-if="lightboxLabel" class="part-lightbox-caption">{{ lightboxLabel }}</div>
        <img :src="lightboxUrl" alt="部件图预览" class="part-lightbox-img" />
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import {
  artifactColumnLabel,
  diffKindLabel,
  filterPartRows,
  inscriptionDiffPreview,
  truncateCell,
  DIFF_KIND_CLASS,
} from "@/utils/partCompareView";
import { imagesForCanonicalPart } from "@/utils/imageLabelUtils";

const props = defineProps({
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
  result: { type: Object, default: null },
  artifactImagesMap: { type: Object, default: () => ({}) },
  selectedSlotKey: { type: String, default: "" },
  availableBooks: { type: Array, default: () => [] },
});

const emit = defineEmits(["row-click", "filter-change"]);

const localDiffKind = ref("all");
const localLayer = ref("all");
const localPartKw = ref("");
const hideShared = ref(false);
const showLargeImage = ref(false);
const lightboxUrl = ref("");
const lightboxLabel = ref("");

const artifacts = computed(() => props.result?.artifacts || []);
const rows = computed(() => props.result?.rows || []);
const summary = computed(() => props.result?.summary || {});

const diffKindLabels = computed(() => props.result?.meta?.diff_kind_labels || {});

const diffKindOptions = computed(() => {
  const kinds = Object.keys(summary.value.by_diff_kind || {});
  const defaults = ["V", "A", "S", "I", "M"];
  const merged = [...new Set([...kinds, ...defaults])];
  return merged.map((value) => ({
    value,
    label: diffKindLabel(value, diffKindLabels.value),
  }));
});

const layerOptions = computed(() => {
  const set = new Set(rows.value.map((r) => r.semantic_layer).filter(Boolean));
  return [...set];
});

const filteredRows = computed(() => {
  let list = filterPartRows(rows.value, {
    diffKindFilter: localDiffKind.value,
    partFilter: localPartKw.value,
    layerFilter: localLayer.value,
  });
  if (hideShared.value) {
    list = list.filter((row) => row.diff_kind !== "S");
  }
  return list;
});

watch([localDiffKind, localLayer, localPartKw, hideShared], () => {
  emit("filter-change", {
    diffKind: localDiffKind.value,
    layer: localLayer.value,
    keyword: localPartKw.value,
    hideShared: hideShared.value,
  });
});

function columnLabel(art) {
  return artifactColumnLabel(art, props.availableBooks);
}

function diffLabel(kind) {
  return diffKindLabel(kind, diffKindLabels.value);
}

function diffClass(kind) {
  return DIFF_KIND_CLASS[String(kind).toUpperCase()] || "diff-other";
}

function cellPresent(row, artifactId) {
  return Boolean(row.cells?.[artifactId]?.present);
}

function cellValue(row, artifactId) {
  return row.cells?.[artifactId]?.value;
}

function cellPartImages(row, artifactId) {
  const labeled = props.artifactImagesMap?.[artifactId] || [];
  return imagesForCanonicalPart(labeled, row.canonical_part_label, 2);
}

function openImage(img) {
  if (!img?.url) return;
  lightboxUrl.value = img.url;
  lightboxLabel.value = img.label || "";
  showLargeImage.value = true;
}

function closeLightbox() {
  showLargeImage.value = false;
  lightboxUrl.value = "";
  lightboxLabel.value = "";
}

function truncate(value) {
  return truncateCell(value, 72);
}

function inscriptionPreview(diff) {
  return inscriptionDiffPreview(diff?.segments, 96) || "铭文有异文";
}

function inscriptionTitle(diff) {
  if (!diff?.segments) return "";
  return diff.segments
    .map((seg) => {
      if (seg.type === "equal") return seg.text;
      if (seg.type === "replace") return `${seg.left} → ${seg.right}`;
      return JSON.stringify(seg);
    })
    .join("");
}

function onRowClick(row) {
  emit("row-click", row);
}
</script>

<style scoped>
.part-compare-panel {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.part-compare-head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: space-between;
  align-items: flex-start;
}

.part-compare-title {
  font-size: 15px;
  font-weight: 700;
  color: rgba(92, 76, 57, 0.88);
  letter-spacing: 0.04em;
}

.part-compare-sub {
  margin: 4px 0 0;
  font-size: 12px;
}

.part-compare-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-end;
}

.part-filter-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: rgba(92, 76, 57, 0.72);
}

.part-filter-grow {
  min-width: 160px;
}

.part-filter-select,
.part-filter-input {
  border: 1px solid rgba(184, 159, 119, 0.45);
  border-radius: 8px;
  padding: 6px 8px;
  font-size: 12px;
  background: rgba(255, 252, 246, 0.95);
}

.part-filter-check {
  flex-direction: row;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding-bottom: 6px;
}

.part-compare-table-wrap {
  overflow: auto;
  max-height: 420px;
  border: 1px solid rgba(184, 159, 119, 0.35);
  border-radius: 12px;
}

.part-compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.part-compare-table th,
.part-compare-table td {
  border-bottom: 1px solid rgba(184, 159, 119, 0.22);
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.part-compare-table th {
  position: sticky;
  top: 0;
  background: rgba(248, 242, 232, 0.98);
  z-index: 1;
  font-weight: 600;
  color: rgba(72, 58, 42, 0.85);
}

.part-col-artifact {
  min-width: 120px;
  max-width: 220px;
}

.part-compare-row {
  cursor: pointer;
  transition: background 0.15s ease;
}

.part-compare-row:hover,
.part-compare-row.active {
  background: rgba(255, 248, 235, 0.92);
}

.part-cell-name {
  font-weight: 600;
  white-space: nowrap;
}

.part-cell-layer {
  color: rgba(92, 76, 57, 0.65);
  white-space: nowrap;
}

.part-cell-value {
  max-width: 240px;
  word-break: break-word;
  line-height: 1.45;
}

.part-cell-inner {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.part-cell-images {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.part-cell-thumb-btn {
  padding: 0;
  border: 1px solid rgba(184, 159, 119, 0.45);
  border-radius: 6px;
  background: rgba(255, 252, 246, 0.9);
  cursor: zoom-in;
  overflow: hidden;
  line-height: 0;
}

.part-cell-thumb-btn:hover {
  border-color: rgba(74, 144, 217, 0.55);
}

.part-cell-thumb {
  width: 56px;
  height: 56px;
  object-fit: cover;
  display: block;
}

.part-image-lightbox {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: rgba(20, 16, 12, 0.82);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.part-lightbox-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.part-lightbox-caption {
  color: #f5f0e8;
  font-size: 14px;
  font-weight: 600;
}

.part-lightbox-img {
  max-width: min(92vw, 960px);
  max-height: 82vh;
  object-fit: contain;
  border-radius: 8px;
}

.part-cell-value.missing {
  color: rgba(140, 120, 95, 0.65);
}

.part-missing-mark {
  font-style: italic;
  opacity: 0.75;
}

.part-diff-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.diff-s { background: rgba(129, 199, 132, 0.35); color: #2e6b34; }
.diff-v { background: rgba(255, 183, 77, 0.35); color: #8a4b00; }
.diff-a { background: rgba(100, 181, 246, 0.3); color: #1565a8; }
.diff-m { background: rgba(189, 189, 189, 0.35); color: #555; }
.diff-i { background: rgba(186, 104, 200, 0.28); color: #6a1b7a; }
.diff-g { background: rgba(161, 136, 127, 0.28); color: #4e342e; }
.diff-other { background: rgba(220, 220, 220, 0.5); color: #444; }

.part-inscription-diff {
  color: #8a4b00;
}

.part-compare-empty {
  padding: 24px 12px;
  text-align: center;
}

.part-compare-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.part-summary-chip {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 250, 243, 0.9);
  border: 1px solid rgba(184, 159, 119, 0.28);
  color: rgba(72, 58, 42, 0.78);
}
</style>

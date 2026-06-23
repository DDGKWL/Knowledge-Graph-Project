<template>
  <footer class="synthesis-workbench panel">
    <div class="synthesis-head">
      <div class="synthesis-head-text">
        <span class="eyebrow">证据链</span>
        <strong class="synthesis-title">{{ title }}</strong>
      </div>
      <div class="synthesis-head-actions">
        <button
          v-if="segments.length"
          type="button"
          class="synthesis-btn"
          @click="$emit('highlight-all')"
        >
          高亮全部
        </button>
        <button
          v-if="segments.length"
          type="button"
          class="synthesis-btn synthesis-btn-muted"
          @click="$emit('clear')"
        >
          清空
        </button>
      </div>
    </div>

    <div v-if="!segments.length" class="synthesis-empty">
      <template v-if="mode === 'compare'">
        在比较面板中点击差异 / 缺失 / 冲突行右侧 <strong>+</strong>，将结构差异与原文摘录加入证据链；点击链块可在主图高亮。
      </template>
      <template v-else>
        在发现模式中点击候选右侧 <strong>+</strong>，将二跳路径拆为链块加入此处；点击链块可在主图高亮该段。
      </template>
    </div>

    <div v-else class="synthesis-track" role="list" aria-label="证据链列表">
      <template v-for="(seg, index) in segments" :key="seg.id">
        <span
          v-if="index > 0 && !isCompareItem(seg)"
          class="synthesis-connector"
          :class="{ 'synthesis-connector--warn': !seg.spliceOk }"
          :title="seg.spliceOk ? '节点衔接' : '与上一段未共享端点，仅作并列展示'"
          aria-hidden="true"
        >⛓</span>
        <span
          v-else-if="index > 0 && isCompareItem(seg)"
          class="synthesis-connector synthesis-connector--dot"
          aria-hidden="true"
        >·</span>
        <div
          role="listitem"
          class="synthesis-segment"
          :class="{
            active: selectedSegmentId === seg.id,
            'synthesis-segment--compare': isCompareItem(seg),
          }"
          tabindex="0"
          @click="$emit('select-segment', seg.id)"
          @keydown.enter.prevent="$emit('select-segment', seg.id)"
        >
          <button
            type="button"
            class="synthesis-segment-remove"
            title="移除此链块"
            @click.stop="$emit('remove-segment', seg.id)"
          >
            ×
          </button>

          <template v-if="isCompareItem(seg)">
            <div class="evidence-compare-head">
              <span class="evidence-kind-tag">{{ kindLabel(seg.kind) }}</span>
              <strong class="evidence-compare-title">{{ seg.title }}</strong>
            </div>
            <p class="evidence-claim" :title="seg.claim">{{ truncate(seg.claim, 88) }}</p>
            <div v-if="seg.stripNodes?.length >= 2" class="evidence-strip-wrap">
              <DiscoveryPathStrip
                :nodes="seg.stripNodes"
                :relations="seg.stripRels"
                :aria-label="seg.ariaLabel"
                :strip-id="'syn-' + seg.id"
                compact
              />
            </div>
            <ul class="evidence-side-list">
              <li
                v-for="(side, si) in visibleSides(seg)"
                :key="`${seg.id}-side-${si}`"
                class="evidence-side-line"
                :class="{ 'evidence-side-line--absent': !side.present }"
              >
                <span class="evidence-side-label">
                  {{ side.artifactName || "节点" }}
                  <span v-if="side.book" class="evidence-side-book">（{{ side.book }}）</span>
                </span>
                <span v-if="side.present && side.targetName" class="evidence-side-target">
                  {{ side.relation }} → {{ side.targetName }}
                </span>
                <span v-else class="evidence-side-target">缺失此关系</span>
                <span v-if="side.description" class="evidence-side-desc">
                  {{ truncate(side.description, 72) }}
                </span>
              </li>
            </ul>
          </template>

          <template v-else>
            <DiscoveryPathStrip
              :nodes="seg.stripNodes"
              :relations="seg.stripRels"
              :aria-label="seg.ariaLabel"
              :strip-id="'syn-' + seg.id"
              compact
            />
            <p
              v-if="seg.targetDescription || seg.sourceDescription"
              class="evidence-discovery-desc"
            >
              {{ truncate(seg.targetDescription || seg.sourceDescription, 80) }}
            </p>
          </template>
        </div>
      </template>
    </div>
  </footer>
</template>

<script setup>
import DiscoveryPathStrip from "./DiscoveryPathStrip.vue";
import { compareKindLabel, truncateText } from "../utils/evidenceEngine";

defineProps({
  segments: { type: Array, default: () => [] },
  selectedSegmentId: { type: String, default: "" },
  title: { type: String, default: "证据链工作台" },
  mode: { type: String, default: "discovery" },
});

defineEmits(["select-segment", "remove-segment", "highlight-all", "clear"]);

function isCompareItem(seg) {
  return String(seg?.kind || "").startsWith("compare-");
}

function kindLabel(kind) {
  return compareKindLabel(kind);
}

function truncate(text, max) {
  return truncateText(text, max);
}

function visibleSides(seg) {
  return (seg.sides || []).slice(0, 4);
}
</script>

<style scoped>
.synthesis-workbench {
  padding: 12px 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.synthesis-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.synthesis-title {
  display: block;
  font-size: 15px;
  color: var(--text, #3f3427);
}

.synthesis-head-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.synthesis-btn {
  border: 1px solid rgba(95, 135, 124, 0.45);
  background: rgba(95, 135, 124, 0.12);
  color: var(--text, #3f3427);
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.synthesis-btn-muted {
  background: rgba(255, 255, 255, 0.5);
  border-color: rgba(184, 159, 119, 0.35);
}

.synthesis-empty {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
  padding: 8px 4px;
}

.synthesis-track {
  display: flex;
  flex-wrap: nowrap;
  align-items: stretch;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.synthesis-connector {
  flex-shrink: 0;
  align-self: center;
  font-size: 14px;
  color: rgba(210, 120, 60, 0.85);
  user-select: none;
}

.synthesis-connector--warn {
  color: rgba(184, 103, 83, 0.9);
}

.synthesis-connector--dot {
  color: rgba(184, 159, 119, 0.75);
  font-size: 18px;
  line-height: 1;
}

.synthesis-segment {
  position: relative;
  flex: 0 0 auto;
  min-width: 200px;
  max-width: 260px;
  padding: 8px 28px 8px 8px;
  border-radius: 12px;
  border: 1px solid rgba(184, 159, 119, 0.35);
  background: rgba(255, 252, 248, 0.9);
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.synthesis-segment--compare {
  min-width: 240px;
  max-width: 320px;
}

.synthesis-segment:hover {
  border-color: rgba(95, 135, 124, 0.45);
}

.synthesis-segment.active {
  border-color: rgba(210, 120, 60, 0.75);
  box-shadow: 0 0 0 2px rgba(210, 120, 60, 0.2);
  background: rgba(255, 248, 238, 0.95);
}

.synthesis-segment-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  border: 0;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.06);
  color: var(--muted);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}

.synthesis-segment-remove:hover {
  background: rgba(184, 103, 83, 0.15);
  color: #8b4a3a;
}

.evidence-compare-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.evidence-kind-tag {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(95, 135, 124, 0.16);
  color: #2a4a42;
}

.evidence-compare-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text, #3f3427);
}

.evidence-claim {
  margin: 0 0 6px;
  font-size: 11px;
  line-height: 1.45;
  color: var(--muted);
}

.evidence-strip-wrap {
  margin-bottom: 6px;
  padding: 4px;
  border-radius: 8px;
  background: rgba(255, 252, 248, 0.65);
  border: 1px solid rgba(184, 159, 119, 0.22);
}

.evidence-side-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.evidence-side-line {
  font-size: 10px;
  line-height: 1.4;
  padding: 4px 6px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(184, 159, 119, 0.18);
}

.evidence-side-line--absent {
  border-style: dashed;
  opacity: 0.85;
}

.evidence-side-label {
  display: block;
  font-weight: 700;
  color: var(--text, #3f3427);
}

.evidence-side-book {
  font-weight: 500;
  color: var(--muted);
}

.evidence-side-target {
  display: block;
  color: #2a4a42;
}

.evidence-side-desc {
  display: block;
  margin-top: 2px;
  color: var(--muted);
  font-style: italic;
}

.evidence-discovery-desc {
  margin: 6px 0 0;
  font-size: 10px;
  line-height: 1.4;
  color: var(--muted);
}
</style>

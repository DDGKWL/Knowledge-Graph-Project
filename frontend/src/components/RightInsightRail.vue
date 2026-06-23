<template>

  <aside class="right-rail panel">

    <div class="right-rail-head">

    <div class="section-title">{{ railTitle }}</div>

    <div class="rail-subtitle">{{ railSubtitle }}</div>



    <div class="mini-mode-map tabs rail-tabs">

      <button

        v-for="tab in visibleTabs"

        :key="tab.id"

        class="mode-chip"

        :class="{ active: activeTab === tab.id }"

        @click="$emit('change-tab', tab.id)"

      >

        {{ tab.label }}

      </button>

    </div>



    <div class="context-card">

      <div class="context-key">当前焦点</div>

      <div class="context-value">{{ displayName }}</div>

      <div class="context-sub">模式：{{ modeText }}</div>

      <div v-if="mode === 'artifact' && modalityLabel" class="context-modality-row">
        <span class="context-modality-badge" :class="`ctx-mod-${modalityKind}`">{{ modalityLabel }}</span>
        <span class="context-modality-meta">{{ modalityMeta }}</span>
      </div>

      <div

        v-if="mode === 'artifact'"

        class="context-image-block"

      >

        <div v-if="artifactImages.length === 0" class="context-image-empty">

          点击单个文物节点后在此预览图片

        </div>

        <div v-else class="context-image-grid">

          <figure
            v-for="(item, idx) in labeledArtifactImages"
            :key="`${item.url}-${idx}`"
            class="context-image-figure"
          >

            <img
              :src="item.url"
              :alt="item.label"
              class="context-image"
              @click="openImage(item.url)"
            />

            <figcaption :class="{ unclassified: !item.classified }">{{ item.label }}</figcaption>

          </figure>

        </div>

        <div

          v-if="mode === 'artifact'"

          class="context-text-block"

        >

          <div class="context-text-label">原始文本</div>

          <div v-if="!artifactSourceText" class="context-image-empty">

            点击单个文物节点后在此显示原文

          </div>

          <pre v-else class="context-text-body">{{ artifactSourceText }}</pre>

        </div>

      </div>

    </div>

    </div>



    <div class="insight-stack">

      <!-- 比较模式：PK 摘要 -->

      <div v-if="mode === 'compare'" class="placeholder-block vertical detail-block mode-panel">

        <div class="placeholder-title">{{ tabTitle }}</div>

        <template v-if="activeTab === 'evidence'">

          <div v-if="!comparePanel.ready" class="context-image-empty">

            {{ comparePanel.emptyHint || '请至少选择 2 件文物进行比较' }}

          </div>

          <template v-else>

            <div class="stat-row">

              <span class="stat-pill">差异 {{ comparePanel.counts?.difference ?? 0 }}</span>

              <span class="stat-pill">缺失 {{ comparePanel.counts?.missing ?? 0 }}</span>

              <span class="stat-pill">冲突 {{ comparePanel.counts?.conflict ?? 0 }}</span>

            </div>

            <div class="detail-item muted-hint">

              比较 {{ comparePanel.artifactCount }} 件 · 共享关系 {{ comparePanel.counts?.shared ?? 0 }} 条（详见中间面板）

            </div>

            <div class="detail-item">

              <strong>证据链</strong> {{ synthesisSegments.length }} 项

            </div>

            <div v-if="synthesisSegments.length === 0" class="context-image-empty">

              在中间差异/缺失/冲突行点 + 加入底部证据链

            </div>

            <template v-if="selectedEvidence">

              <div class="detail-item evidence-selected-head">

                <span class="preview-tag">{{ evidenceKindLabel(selectedEvidence.kind) }}</span>

                <strong>{{ selectedEvidence.title }}</strong>

              </div>

              <div class="detail-item muted-hint">{{ selectedEvidence.claim }}</div>

              <div

                v-for="(side, idx) in selectedEvidence.sides || []"

                :key="`${selectedEvidence.id}-side-${idx}`"

                class="detail-item evidence-side-detail"

                :class="{ 'evidence-side-detail--absent': !side.present }"

              >

                <div>

                  <strong>{{ side.artifactName || '节点' }}</strong>

                  <span v-if="side.book" class="watch-meta"> · {{ side.book }}</span>

                </div>

                <div v-if="side.present && side.targetName">

                  {{ side.relation }} → {{ side.targetName }}

                </div>

                <div v-else class="muted-hint">本件缺失此关系</div>

                <div v-if="side.description" class="evidence-desc-block">

                  {{ side.description }}

                </div>

              </div>

            </template>

            <div v-else-if="synthesisSegments.length" class="context-image-empty muted-hint">

              点击底部证据链块查看完整原文摘录

            </div>

            <div v-if="(comparePanel.previews || []).length" class="detail-item" style="margin-top: 8px">

              <strong>结构预览</strong>

            </div>

            <div

              v-for="item in comparePanel.previews || []"

              :key="item.key"

              class="detail-item preview-row"

              :class="`preview-${item.type}`"

            >

              <span class="preview-tag">{{ previewTypeLabel(item.type) }}</span>

              {{ item.label }}

            </div>

          </template>

        </template>

        <template v-else-if="activeTab === 'ai'">

          <ArtifactQaPanel
            mode="compare"
            :target-ids="qaTargetIds"
            :scope-names="qaScopeNames"
          />

        </template>

        <template v-else>

          <div class="detail-item">{{ graphContext.aiSummary || '—' }}</div>

        </template>

      </div>



      <!-- 发现模式：发现协同 -->

      <div v-else-if="mode === 'discovery'" class="placeholder-block vertical detail-block mode-panel">

        <div class="placeholder-title">{{ tabTitle }}</div>

        <template v-if="activeTab === 'evidence'">

          <div class="stat-row">

            <span class="stat-pill">扩展候选 {{ discoveryPanel.candidateTotal ?? 0 }}</span>

            <span v-if="discoveryPanel.truncated" class="stat-pill muted">展示 {{ discoveryPanel.shown }}/{{ discoveryPanel.total }}</span>

          </div>

          <div class="detail-item muted-hint">{{ discoveryPanel.hint }}</div>

          <div class="detail-item">

            新知识机会 {{ discoveryPanel.opportunityCount ?? 0 }} 条（中间列表）

          </div>

        </template>

        <template v-else-if="activeTab === 'candidate'">

          <div class="detail-item">

            <strong>关注队列</strong> {{ queueArtifacts.length }} 项

          </div>

          <div v-if="queueArtifacts.length === 0" class="context-image-empty">

            从中间候选列表点 + 加入队列，或从主图加入文物

          </div>

          <div

            v-for="item in queueArtifacts"

            :key="item.id"

            class="detail-item watch-row"

          >

            {{ item.name || item.id }}

            <span class="watch-meta">{{ item.category || '实体' }}</span>

          </div>

          <div class="detail-item">

            <strong>证据合成</strong> {{ synthesisSegments.length }} 段

          </div>

          <div v-if="synthesisSegments.length === 0" class="context-image-empty">

            在中间候选行点 + 加入底部证据链

          </div>

          <template v-if="selectedEvidence">

            <div class="detail-item evidence-selected-head">

              <strong>{{ selectedEvidence.title || `段 ${selectedEvidenceIndex + 1}` }}</strong>

            </div>

            <div v-if="selectedEvidence.ariaLabel" class="detail-item muted-hint">

              {{ selectedEvidence.ariaLabel }}

            </div>

            <div v-if="selectedEvidence.targetDescription" class="detail-item evidence-desc-block">

              {{ selectedEvidence.targetDescription }}

            </div>

            <div v-else-if="selectedEvidence.sourceDescription" class="detail-item evidence-desc-block">

              {{ selectedEvidence.sourceDescription }}

            </div>

          </template>

          <div

            v-for="(seg, idx) in synthesisSegments"

            :key="seg.id"

            class="detail-item watch-row"

            :class="{ 'watch-selected': seg.id === synthesisSelectedSegmentId }"

          >

            <span>段 {{ idx + 1 }}</span>

            <span class="watch-meta">{{ seg.spliceOk === false ? '未衔接' : '可衔接' }}</span>

          </div>

        </template>

        <template v-else-if="activeTab === 'ai'">

          <p class="context-image-empty muted-hint">

            图谱问答请在「单文物」或「比较」模式下使用。

          </p>

        </template>

        <template v-else>

          <div class="detail-item">{{ graphContext.aiSummary || '—' }}</div>

        </template>

      </div>



      <!-- 单文物模式 -->

      <div v-else class="placeholder-block vertical detail-block mode-panel">

        <div class="placeholder-title">{{ tabTitle }}</div>

        <div class="detail-list">

          <template v-if="activeTab === 'evidence'">

            <div class="detail-item">

              <strong>节点：</strong>{{ focusName }}

            </div>

            <div v-if="focusNode" class="detail-item muted-hint">

              {{ focusNode.isArtifact ? '文物节点' : '非文物节点' }} · 一度关系 {{ focusNode.neighborCount ?? 0 }} 条

            </div>

            <div v-else class="context-image-empty">点击主图节点查看详情</div>

            <div class="detail-item">

              <strong>关联节点数：</strong>{{ graphContext.relatedSubgraph?.nodes?.length || 0 }}

            </div>

            <div class="detail-item">

              <strong>关联边数：</strong>{{ graphContext.relatedSubgraph?.links?.length || 0 }}

            </div>

          </template>



          <template v-else-if="activeTab === 'candidate'">

            <div class="context-image-empty muted-hint">

              单文物模式下，候选探索请切换到「发现」模式；此处保留快捷预览（前 5 条）。

            </div>

            <div v-if="(graphContext.candidates || []).length === 0" class="context-image-empty">

              暂无候选实体

            </div>

            <button

              v-for="item in graphContext.candidates || []"

              :key="item.key"

              class="candidate-item"

              @click="$emit('add-candidate', item)"

            >

              <span>{{ item.candidateNodeName }}</span>

              <span class="candidate-add">+</span>

            </button>

          </template>



          <template v-else-if="activeTab === 'ai'">

            <ArtifactQaPanel
              mode="artifact"
              :target-ids="qaTargetIds"
              :scope-names="qaScopeNames"
            />

          </template>



          <template v-else>

            <div class="detail-item">{{ graphContext.aiSummary || 'AI 摘要将根据当前上下文自动生成。' }}</div>

          </template>

        </div>

      </div>



      <div v-if="mode === 'artifact'" class="placeholder-block vertical detail-block">

        <div class="placeholder-title">联动摘要</div>

        <div class="detail-item">

          基础层 {{ artifactPanel.layerCounts?.base ?? graphContext.layerBuckets?.base?.length ?? 0 }} 条；

          特有层 {{ artifactPanel.layerCounts?.unique ?? graphContext.layerBuckets?.unique?.length ?? 0 }} 条；

          背景层 {{ artifactPanel.layerCounts?.background ?? graphContext.layerBuckets?.background?.length ?? 0 }} 条。

        </div>

        <div v-if="artifactPanel.hint" class="detail-item muted-hint">{{ artifactPanel.hint }}</div>

      </div>

    </div>

  </aside>

  <div v-if="showLargeImage" class="global-image-modal" @click="showLargeImage = false">

    <div class="modal-content" @click.stop>

      <img :src="currentLargeImage" alt="预览大图">

      <button class="close-btn" @click="showLargeImage = false">×</button>

    </div>

  </div>

</template>



<script setup>

import { computed, ref } from 'vue'

import { compareKindLabel } from '../utils/evidenceEngine'
import { resolveModality } from '../utils/textHighlight'
import { enrichImagePaths } from '../utils/imageLabelUtils'
import ArtifactQaPanel from './ArtifactQaPanel.vue'



const props = defineProps({

  mode: { type: String, required: true },

  artifact: { type: Object, required: true },

  activeTab: { type: String, required: true },

  selectedNodeName: { type: String, default: '' },

  artifactImages: { type: Array, default: () => [] },

  artifactSourceText: { type: String, default: '' },

  compareArtifactIds: { type: Array, default: () => [] },

  queueArtifacts: { type: Array, default: () => [] },

  synthesisSegments: { type: Array, default: () => [] },

  synthesisSelectedSegmentId: { type: String, default: '' },

  graphContext: {

    type: Object,

    default: () => ({

      focusNode: null,

      modePanel: { kind: 'artifact' },

      evidencePayload: {},

      relatedSubgraph: { nodes: [], links: [] },

      layerBuckets: { base: [], unique: [], background: [] },

      candidates: [],

      aiSummary: ''

    })

  }

})



defineEmits(['change-tab', 'add-candidate'])



const modePanel = computed(() => props.graphContext.modePanel || { kind: props.mode })

const comparePanel = computed(() =>

  modePanel.value.kind === 'compare' ? modePanel.value : { ready: false, previews: [], counts: {} }

)

const discoveryPanel = computed(() =>

  modePanel.value.kind === 'discovery' ? modePanel.value : {}

)

const artifactPanel = computed(() =>

  modePanel.value.kind === 'artifact' ? modePanel.value : {}

)



const focusNode = computed(() => props.graphContext.focusNode || null)

const focusName = computed(

  () => focusNode.value?.name || props.graphContext.evidencePayload?.nodeName || '未选中'

)

const selectedEvidence = computed(() => {
  if (!props.synthesisSelectedSegmentId) return null
  return (
    props.synthesisSegments.find(
      (s) => String(s.id) === String(props.synthesisSelectedSegmentId)
    ) || null
  )
})

const selectedEvidenceIndex = computed(() => {
  if (!selectedEvidence.value) return -1
  return props.synthesisSegments.findIndex(
    (s) => String(s.id) === String(selectedEvidence.value.id)
  )
})

function evidenceKindLabel(kind) {
  return compareKindLabel(kind)
}



const railTitle = computed(() => {

  if (props.mode === 'compare') return '比较协同'

  if (props.mode === 'discovery') return '发现协同'

  return '上下文协同'

})



const railSubtitle = computed(() => {

  if (props.mode === 'compare') return '环境感知 · PK 摘要'

  if (props.mode === 'discovery') return '环境感知 · 关注与合成'

  return '环境感知 · 节点与分层'

})



const visibleTabs = computed(() => {

  if (props.mode === 'compare') {

    return [

      { id: 'evidence', label: '证据' },

      { id: 'ai', label: '问答' },

    ]

  }

  if (props.mode === 'discovery') {

    return [

      { id: 'evidence', label: '发现' },

      { id: 'candidate', label: '关注' },

      { id: 'ai', label: '摘要' },

    ]

  }

  return [

    { id: 'evidence', label: '证据' },

    { id: 'candidate', label: '候选' },

    { id: 'ai', label: '问答' },

  ]

})



const tabTitle = computed(() => {

  if (props.mode === 'compare') {

    return props.activeTab === 'ai' ? '图谱问答' : 'PK 对比'

  }

  if (props.mode === 'discovery') {

    if (props.activeTab === 'candidate') return '关注清单'

    if (props.activeTab === 'ai') return '发现摘要'

    return '发现概览'

  }

  if (props.activeTab === 'candidate') return '候选预览'

  if (props.activeTab === 'ai') return '图谱问答'

  return '来源证据'

})



const modeText = computed(() => {

  if (props.mode === 'compare') return '比较'

  if (props.mode === 'discovery') return '发现'

  return '单文物'

})



const displayName = computed(() => props.selectedNodeName || focusName.value || props.artifact.name)

const modalityKind = computed(() =>
  resolveModality(
    (props.artifactImages || []).length > 0,
    Boolean(props.artifactSourceText)
  )
)

const modalityLabel = computed(() => {
  const map = { both: "图文兼备", image: "含图片", text: "含源文", none: "" }
  return map[modalityKind.value] || ""
})

const modalityMeta = computed(() => {
  const parts = []
  if (props.artifactImages?.length) parts.push(`${props.artifactImages.length} 图`)
  if (props.artifactSourceText) parts.push(`${props.artifactSourceText.length} 字`)
  return parts.join(" · ")
})

const labeledArtifactImages = computed(() => enrichImagePaths(props.artifactImages || []))

/** 单文物：焦点文物或队列首件；比较：compareList */
const qaTargetIds = computed(() => {
  if (props.mode === 'compare') {
    return (props.compareArtifactIds || []).map((id) => String(id).trim()).filter(Boolean)
  }
  if (props.mode === 'artifact') {
    const focus = props.graphContext?.focusNode
    if (focus?.isArtifact && focus?.id) {
      return [String(focus.id)]
    }
    const fromQueue = (props.queueArtifacts || []).find((item) => {
      const id = String(item?.id || '')
      return id.includes('_')
    })
    if (fromQueue) return [String(fromQueue.id)]
  }
  return []
})

const qaScopeNames = computed(() => {
  if (props.mode === 'compare') {
    const idSet = new Set(qaTargetIds.value)
    return (props.queueArtifacts || [])
      .filter((item) => idSet.has(String(item.id)))
      .map((item) => item.name || item.id)
  }
  if (props.mode === 'artifact') {
    const focus = props.graphContext?.focusNode
    if (focus?.isArtifact && focus?.name) return [focus.name]
    const id = qaTargetIds.value[0]
    if (!id) return []
    const hit = (props.queueArtifacts || []).find((item) => String(item.id) === id)
    return [hit?.name || focus?.name || id]
  }
  return []
})

function previewTypeLabel(type) {

  if (type === 'diff') return '差异'

  if (type === 'conflict') return '冲突'

  if (type === 'missing') return '缺失'

  return '项'

}



const showLargeImage = ref(false)

const currentLargeImage = ref('')



const openImage = (imagePath) => {

  currentLargeImage.value = imagePath

  showLargeImage.value = true

}

</script>



<style scoped>

.right-rail-head {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rail-tabs {
  flex-shrink: 0;
  align-items: flex-start;
}

.rail-tabs .mode-chip {
  flex: 0 0 auto;
  width: auto;
}

.insight-stack {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  align-content: start;
}

.rail-subtitle {

  font-size: 11px;

  color: var(--muted);

  margin: -4px 0 10px;

}



.context-image-block {

  margin-top: 10px;

}



.context-text-block {

  margin-top: 12px;

}



.context-text-label {

  font-size: 12px;

  font-weight: 600;

  color: var(--ink);

  margin-bottom: 6px;

}



.context-text-body {

  margin: 0;

  max-height: 220px;

  overflow-y: auto;

  padding: 10px;

  font-size: 12px;

  line-height: 1.55;

  white-space: pre-wrap;

  word-break: break-word;

  color: var(--ink);

  background: rgba(255, 252, 245, 0.9);

  border: 1px solid rgba(184, 159, 119, 0.35);

  border-radius: 8px;

  font-family: inherit;

}



.context-image-empty {

  font-size: 12px;

  color: var(--muted);

}



.context-image-grid {

  margin-top: 6px;

  display: grid;

  grid-template-columns: repeat(3, minmax(0, 1fr));

  gap: 8px;

}



.context-image {

  width: 100%;

  aspect-ratio: 1 / 1;

  object-fit: cover;

  border-radius: 8px;

  border: 1px solid rgba(184, 159, 119, 0.45);

  cursor: pointer;

}

.context-image-figure {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.context-image-figure figcaption {
  font-size: 10px;
  text-align: center;
  color: #2a5f9e;
  font-weight: 600;
  line-height: 1.2;
}

.context-image-figure figcaption.unclassified {
  color: var(--muted);
  font-weight: 500;
}



.detail-block {

  display: flex;

  flex-direction: column;

  justify-content: flex-start !important;

  align-items: stretch;

  flex: none;

  min-height: 0;

  padding: 12px;

  gap: 8px;

}



.detail-list {

  display: flex;

  flex-direction: column;

  gap: 8px;

  width: 100%;

}



.detail-item {

  font-size: 12px;

  color: var(--text);

  text-align: left;

  line-height: 1.4;

  padding: 6px 8px;

  border-radius: 8px;

  background: rgba(255, 255, 255, 0.45);

}



.muted-hint {

  color: var(--muted);

  background: transparent;

  padding: 4px 2px;

}



.stat-row {

  display: flex;

  flex-wrap: wrap;

  gap: 6px;

}



.stat-pill {

  font-size: 11px;

  padding: 4px 8px;

  border-radius: 999px;

  background: rgba(184, 159, 119, 0.2);

  color: var(--text);

}



.stat-pill.muted {

  background: rgba(0, 0, 0, 0.06);

}



.preview-row {

  display: flex;

  flex-direction: column;

  gap: 4px;

}



.preview-tag {

  font-size: 10px;

  font-weight: 700;

  color: var(--accent);

}



.preview-conflict .preview-tag {

  color: #a63d3d;

}



.watch-row {

  display: flex;

  justify-content: space-between;

  align-items: center;

  gap: 8px;

}



.watch-meta {

  font-size: 10px;

  color: var(--muted);

}



.watch-selected {

  outline: 1px solid var(--accent);

  background: rgba(184, 159, 119, 0.15);

}



.candidate-item {

  width: 100%;

  border: 1px solid rgba(184, 159, 119, 0.35);

  background: rgba(255, 255, 255, 0.6);

  border-radius: 8px;

  padding: 8px 10px;

  display: flex;

  justify-content: space-between;

  align-items: center;

  color: var(--text);

}



.candidate-add {

  color: var(--accent);

  font-weight: 700;

}



.global-image-modal {

  position: fixed;

  inset: 0;

  background: rgba(0, 0, 0, 0.84);

  display: flex;

  justify-content: center;

  align-items: center;

  z-index: 9999;

}



.modal-content {

  position: relative;

  max-width: 90%;

  max-height: 90%;

}



.modal-content img {

  max-width: 100%;

  max-height: 82vh;

  object-fit: contain;

  border-radius: 8px;

}



.close-btn {

  position: absolute;

  top: -36px;

  right: -28px;

  border: 0;

  background: transparent;

  color: #fff;

  font-size: 30px;

  cursor: pointer;

}

.evidence-selected-head {

  display: flex;

  flex-wrap: wrap;

  align-items: center;

  gap: 8px;

}

.evidence-desc-block {

  font-size: 12px;

  line-height: 1.55;

  padding: 8px 10px;

  border-radius: 8px;

  background: rgba(255, 252, 248, 0.85);

  border: 1px solid rgba(184, 159, 119, 0.25);

  white-space: pre-wrap;

  word-break: break-word;

}

.evidence-side-detail {

  padding: 8px 10px;

  border-radius: 8px;

  background: rgba(255, 255, 255, 0.55);

  border: 1px solid rgba(184, 159, 119, 0.2);

}

.evidence-side-detail--absent {

  border-style: dashed;

  opacity: 0.9;

}

</style>


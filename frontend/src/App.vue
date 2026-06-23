<template>
  <div class="app-shell">
    <TopTaskBar />

    <main class="workbench-grid" :class="`focus-${focusMode}`">
      <LeftArtifactRail
        :queue-artifacts="queueArtifacts"
        :selected-id="selectedArtifactId"
        :compare-list="compareList"
        :available-books="availableBooks"
        :selected-books="selectedBooks"
        @select="selectedArtifactId = $event"
        @remove-from-queue="removeFromQueue"
        @toggle-compare="toggleCompare"
        @toggle-book="toggleBook"
      />

      <MainVisualizationCanvas
        :mode="mode"
        :artifact="selectedArtifact"
        :compare-list="compareObjects"
        :focus-mode="focusMode"
        :available-books="availableBooks"
        :selected-books="selectedBooks"
        :books-ready="booksReady"
        :synthesis-segments="synthesisSegments"
        :synthesis-selected-segment-id="synthesisSelectedSegmentId"
        :synthesis-highlight-all="synthesisHighlightAll"
        @change-mode="mode = $event"
        @change-focus="focusMode = $event"
        @ensure-books-for-compare="ensureBooksForCompare"
        @artifact-images-change="handleArtifactImagesChange"
        @artifact-text-change="handleArtifactTextChange"
        @artifact-queue-enqueue="enqueueArtifactFromGraph"
        @graph-context-change="handleGraphContextChange"
        @add-synthesis-segments="handleAddSynthesisSegments"
        @clear-synthesis-selection="clearSynthesisSelection"
      />

      <RightInsightRail
        :mode="mode"
        :artifact="selectedArtifact"
        :active-tab="activeTab"
        :selected-node-name="selectedNodeName"
        :artifact-images="selectedNodeImages"
        :artifact-source-text="selectedNodeSourceText"
        :compare-artifact-ids="compareList"
        :graph-context="graphContext"
        :queue-artifacts="queueArtifacts"
        :synthesis-segments="synthesisSegments"
        :synthesis-selected-segment-id="synthesisSelectedSegmentId"
        @change-tab="activeTab = $event"
        @add-candidate="handleAddCandidate"
      />
    </main>

    <EvidenceSynthesisWorkbench
      v-if="mode === 'discovery' || mode === 'compare'"
      :segments="synthesisSegments"
      :selected-segment-id="synthesisSelectedSegmentId"
      :title="synthesisWorkbenchTitle"
      :mode="mode"
      @select-segment="onSynthesisSelectSegment"
      @remove-segment="onSynthesisRemoveSegment"
      @highlight-all="onSynthesisHighlightAll"
      @clear="onSynthesisClear"
    />
    <BottomMiniStrip v-else :mode="mode" :compare-count="compareList.length" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import TopTaskBar from './components/TopTaskBar.vue'
import LeftArtifactRail from './components/LeftArtifactRail.vue'
import MainVisualizationCanvas from './components/MainVisualizationCanvas.vue'
import RightInsightRail from './components/RightInsightRail.vue'
import BottomMiniStrip from './components/BottomMiniStrip.vue'
import EvidenceSynthesisWorkbench from './components/EvidenceSynthesisWorkbench.vue'
import { segmentsCanSplice } from './utils/synthesisEngine'
import { getBooks } from './utils/api'
import { bookCode, booksToQueryCodes, normalizeBookEntry } from './utils/bookUtils'

const mode = ref('artifact')
const focusMode = ref('visual')
const activeTab = ref('evidence')
const selectedArtifactId = ref('a1')
const compareList = ref([])
const queueArtifacts = ref([])
const selectedNodeName = ref('')
const selectedNodeImages = ref([])
const selectedNodeSourceText = ref('')
const synthesisSegments = ref([])
const synthesisSelectedSegmentId = ref('')
const synthesisHighlightAll = ref(false)
const availableBooks = ref([])
const selectedBooks = ref(['gq'])
const booksReady = ref(false)

function booksFromArtifactIds(ids) {
  return [
    ...new Set(
      (ids || [])
        .map((id) => String(id).split('_')[0]?.trim().toLowerCase())
        .filter(Boolean)
    ),
  ]
}

async function fetchAvailableBooks() {
  try {
    const { data } = await getBooks()
    const books = (data?.books || []).map(normalizeBookEntry).filter((b) => b.code)
    if (books.length) {
      availableBooks.value = books
      const codes = books.map((b) => b.code)
      if (!selectedBooks.value.length || !selectedBooks.value.some((b) => codes.includes(b))) {
        selectedBooks.value = [codes[0]]
      } else {
        selectedBooks.value = selectedBooks.value.filter((b) => codes.includes(b))
        if (!selectedBooks.value.length) selectedBooks.value = [codes[0]]
      }
    }
  } catch (error) {
    console.warn('[app] GET /books 失败，使用默认书目 gq:', error)
    availableBooks.value = [{ code: 'gq', label: 'gq' }]
    if (!selectedBooks.value.length) selectedBooks.value = ['gq']
  }
}

function toggleBook(book) {
  const key = bookCode(book)
  const set = new Set(selectedBooks.value.map((b) => String(b).trim().toLowerCase()))
  if (set.has(key)) {
    if (set.size <= 1) return
    set.delete(key)
  } else {
    set.add(key)
  }
  selectedBooks.value = booksToQueryCodes(availableBooks.value).filter((code) => set.has(code))
}

function ensureBooksForCompare(ids) {
  const needed = booksFromArtifactIds(ids)
  if (!needed.length) return
  const set = new Set(selectedBooks.value.map((b) => String(b).trim().toLowerCase()))
  needed.forEach((b) => set.add(b))
  selectedBooks.value = availableBooks.value.length
    ? booksToQueryCodes(availableBooks.value).filter((code) => set.has(code))
    : [...set]
  if (!selectedBooks.value.length) selectedBooks.value = needed
}

onMounted(async () => {
  await fetchAvailableBooks()
  booksReady.value = true
})

const synthesisWorkbenchTitle = computed(() => {
  if (mode.value === 'compare') {
    const n = compareList.value.length
    return n >= 2 ? `比较证据链 · ${n} 件文物` : '比较证据链'
  }
  const name = selectedArtifact.value?.name
  return name ? `${name} · 线索合成` : '线索合成工作台'
})

const graphContext = ref({
  selectedArtifactId: '',
  focusNode: null,
  modePanel: { kind: 'artifact' },
  evidencePayload: {},
  relatedSubgraph: { nodes: [], links: [] },
  layerBuckets: { base: [], unique: [], background: [] },
  candidates: [],
  aiSummary: ''
})

const artifacts = ref([
  { id: 'a1', name: '襄', era: '唐', category: '古琴', image: '琴', candidateCount: 6 },
  { id: 'a2', name: '秋籁', era: '宋', category: '古琴', image: '琴', candidateCount: 4 },
  { id: 'a3', name: '龙吟', era: '明', category: '古琴', image: '琴', candidateCount: 3 },
  { id: 'a4', name: '松风', era: '清', category: '古琴', image: '琴', candidateCount: 2 }
])

const selectedArtifact = computed(() => {
  return artifacts.value.find((item) => item.id === selectedArtifactId.value) || artifacts.value[0]
})

const compareObjects = computed(() => {
  const ids = new Set(compareList.value.map((id) => String(id)))
  return queueArtifacts.value.filter((item) => ids.has(String(item.id)))
})

function toggleCompare(id) {
  const sid = String(id)
  if (compareList.value.some((x) => String(x) === sid)) {
    compareList.value = compareList.value.filter((item) => String(item) !== sid)
    return
  }
  // Only allow IDs that are already in the real queue (prevent mock IDs)
  const isRealNode = queueArtifacts.value.some((item) => String(item.id) === sid)
  if (!isRealNode) return
  compareList.value = [...compareList.value.map(String), sid].slice(-3)
}

function handleArtifactImagesChange(payload) {
  selectedNodeName.value = payload?.nodeName || ''
  selectedNodeImages.value = payload?.imagePaths || []
}

function handleArtifactTextChange(payload) {
  if (payload?.nodeName) {
    selectedNodeName.value = payload.nodeName
  }
  selectedNodeSourceText.value = payload?.sourceText || ''
}

function enqueueArtifactFromGraph(payload) {
  const id = String(payload?.id || '')
  if (!id) return
  const existingIndex = queueArtifacts.value.findIndex((item) => String(item.id) === id)
  if (existingIndex >= 0) {
    queueArtifacts.value.splice(existingIndex, 1)
  }
  queueArtifacts.value.push({
    id,
    name: payload?.name || id,
    era: payload?.raw?.era || '',
    category: payload?.raw?.category || '',
    image: payload?.raw?.image || '文'
  })
}

function removeFromQueue(id) {
  const sid = String(id)
  queueArtifacts.value = queueArtifacts.value.filter((item) => String(item.id) !== sid)
  // Keep compareList in sync
  if (compareList.value.some((x) => String(x) === sid)) {
    compareList.value = compareList.value.filter((item) => String(item) !== sid)
  }
}

function handleGraphContextChange(payload) {
  graphContext.value = payload || graphContext.value
}

function handleAddSynthesisSegments(newSegments) {
  const chain = [...synthesisSegments.value]
  ;(newSegments || []).forEach((seg) => {
    if (seg.sourceKey && chain.some((s) => s.sourceKey === seg.sourceKey)) return
    const prev = chain[chain.length - 1]
    const isCompare = String(seg.kind || '').startsWith('compare-')
    const prevIsCompare = prev && String(prev.kind || '').startsWith('compare-')
    chain.push({
      ...seg,
      spliceOk: isCompare || prevIsCompare ? true : segmentsCanSplice(prev, seg),
    })
  })
  if (chain.length === synthesisSegments.value.length) return
  synthesisSegments.value = chain
  synthesisHighlightAll.value = true
  synthesisSelectedSegmentId.value = ''
}

function clearSynthesisSelection() {
  synthesisSelectedSegmentId.value = ''
  synthesisHighlightAll.value = false
}

function onSynthesisSelectSegment(id) {
  synthesisSelectedSegmentId.value = String(id)
  synthesisHighlightAll.value = false
}

function onSynthesisRemoveSegment(id) {
  const sid = String(id)
  const next = synthesisSegments.value.filter((s) => String(s.id) !== sid)
  next.forEach((seg, i) => {
    if (i === 0) seg.spliceOk = true
    else seg.spliceOk = segmentsCanSplice(next[i - 1], seg)
  })
  synthesisSegments.value = next
  if (synthesisSelectedSegmentId.value === sid) {
    synthesisSelectedSegmentId.value = ''
    synthesisHighlightAll.value = next.length > 0
  }
}

function onSynthesisHighlightAll() {
  synthesisHighlightAll.value = true
  synthesisSelectedSegmentId.value = ''
}

function onSynthesisClear() {
  synthesisSegments.value = []
  synthesisSelectedSegmentId.value = ''
  synthesisHighlightAll.value = false
}

watch(mode, (m) => {
  if (m === 'artifact') {
    onSynthesisClear()
  }
  if (m === 'compare') activeTab.value = 'evidence'
  else if (m === 'discovery') activeTab.value = 'candidate'
  else activeTab.value = 'evidence'
})

function handleAddCandidate(candidate) {
  if (!candidate?.candidateNodeId) return
  const id = String(candidate.candidateNodeId)
  const exists = queueArtifacts.value.some((item) => String(item.id) === id)
  if (exists) return
  queueArtifacts.value.push({
    id,
    name: candidate.candidateNodeName || id,
    era: '',
    category: '候选实体',
    image: '候'
  })
}

// Defensive sync: ensure compareList never contains IDs that are no longer in the real queue
watch(queueArtifacts, (currentQueue) => {
  const queueIds = new Set(currentQueue.map((item) => String(item.id)))
  const filtered = compareList.value.filter((id) => queueIds.has(String(id)))
  if (filtered.length !== compareList.value.length) {
    compareList.value = filtered
  }
}, { deep: true })
</script>

<template>
  <div class="app-shell">
    <TopTaskBar
      :mode="mode"
      :focus-mode="focusMode"
      :selected-count="compareList.length || 1"
      @change-mode="mode = $event"
      @change-focus="focusMode = $event"
    />

    <main class="workbench-grid" :class="`focus-${focusMode}`">
      <LeftArtifactRail
        :artifacts="artifacts"
        :selected-id="selectedArtifactId"
        :compare-list="compareList"
        @select="selectedArtifactId = $event"
        @toggle-compare="toggleCompare"
      />

      <MainVisualizationCanvas
        :mode="mode"
        :artifact="selectedArtifact"
        :compare-list="compareObjects"
      />

      <RightInsightRail
        :mode="mode"
        :artifact="selectedArtifact"
        :active-tab="activeTab"
        @change-tab="activeTab = $event"
      />
    </main>

    <BottomMiniStrip :mode="mode" :compare-count="compareList.length" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import TopTaskBar from './components/TopTaskBar.vue'
import LeftArtifactRail from './components/LeftArtifactRail.vue'
import MainVisualizationCanvas from './components/MainVisualizationCanvas.vue'
import RightInsightRail from './components/RightInsightRail.vue'
import BottomMiniStrip from './components/BottomMiniStrip.vue'

const mode = ref('artifact')
const focusMode = ref('visual')
const activeTab = ref('evidence')
const selectedArtifactId = ref('a1')
const compareList = ref(['a1', 'a2'])

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
  return artifacts.value.filter((item) => compareList.value.includes(item.id))
})

function toggleCompare(id) {
  if (compareList.value.includes(id)) {
    compareList.value = compareList.value.filter((item) => item !== id)
    return
  }
  compareList.value = [...compareList.value, id].slice(-3)
}
</script>

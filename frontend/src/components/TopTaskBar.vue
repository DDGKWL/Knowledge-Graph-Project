<template>
  <header class="topbar panel">
    <div class="brand-group">
      <div>
        <div class="eyebrow">Artifact Knowledge Workbench</div>
        <h1>文物知识可视分析工坊</h1>
      </div>
      <div class="meta-pills">
        <span class="pill">当前模式：{{ modeLabel }}</span>
        <span class="pill">已选对象：{{ selectedCount }}</span>
      </div>
    </div>

    <div class="toolbar-group">
      <div class="segmented-control">
        <button
          v-for="item in modeItems"
          :key="item.value"
          class="seg-btn"
          :class="{ active: mode === item.value }"
          @click="$emit('change-mode', item.value)"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="segmented-control compact">
        <button class="seg-btn" :class="{ active: focusMode === 'visual' }" @click="$emit('change-focus', 'visual')">主视图</button>
        <button class="seg-btn" :class="{ active: focusMode === 'evidence' }" @click="$emit('change-focus', 'evidence')">证据优先</button>
        <button class="seg-btn" :class="{ active: focusMode === 'balanced' }" @click="$emit('change-focus', 'balanced')">均衡</button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  mode: { type: String, required: true },
  focusMode: { type: String, required: true },
  selectedCount: { type: Number, required: true }
})

defineEmits(['change-mode', 'change-focus'])

const modeItems = [
  { value: 'artifact', label: '单文物' },
  { value: 'compare', label: '比较' },
  { value: 'discovery', label: '发现' }
]

const modeLabel = computed(() => {
  return modeItems.find((item) => item.value === props.mode)?.label || '单文物'
})
</script>

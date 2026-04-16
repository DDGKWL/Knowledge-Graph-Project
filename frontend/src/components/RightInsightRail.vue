<template>
  <aside class="right-rail panel">
    <div class="section-title">上下文协同</div>

    <div class="mini-mode-map tabs">
      <button class="mode-chip" :class="{ active: activeTab === 'evidence' }" @click="$emit('change-tab', 'evidence')">证据</button>
      <button class="mode-chip" :class="{ active: activeTab === 'candidate' }" @click="$emit('change-tab', 'candidate')">候选</button>
      <button class="mode-chip" :class="{ active: activeTab === 'ai' }" @click="$emit('change-tab', 'ai')">AI</button>
    </div>

    <div class="context-card">
      <div class="context-key">当前对象</div>
      <div class="context-value">{{ artifact.name }}</div>
      <div class="context-sub">模式：{{ modeText }}</div>
    </div>

    <div class="insight-stack">
      <div class="placeholder-block vertical"><div class="placeholder-title">{{ tabTitle }}</div></div>
      <div class="placeholder-block vertical"><div class="placeholder-title">联动摘要</div></div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  mode: { type: String, required: true },
  artifact: { type: Object, required: true },
  activeTab: { type: String, required: true }
})

defineEmits(['change-tab'])

const tabTitle = computed(() => {
  if (props.activeTab === 'candidate') return '候选诊断'
  if (props.activeTab === 'ai') return '结构化建议'
  return '来源证据'
})

const modeText = computed(() => {
  if (props.mode === 'compare') return '比较'
  if (props.mode === 'discovery') return '发现'
  return '单文物'
})
</script>

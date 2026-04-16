<template>
  <section class="visual-canvas panel">
    <div class="canvas-header">
      <div>
        <div class="section-title">知识主画布</div>
        <div class="section-subtitle">
          让可视化成为页面主角，只保留一个主分析焦点。
        </div>
      </div>
      <div class="canvas-tags">
        <span class="canvas-tag">{{ modeLabel }}</span>
        <span class="canvas-tag emphasis">{{ artifact.name }}</span>
      </div>
    </div>

    <div v-if="mode === 'artifact'" class="canvas-content artifact-layout">
      <div class="artifact-center-block placeholder-block large">
        <div class="placeholder-title">主实体视图</div>
      </div>
      <div class="artifact-side-grid">
        <div class="placeholder-block"><div class="placeholder-title">基础层</div></div>
        <div class="placeholder-block"><div class="placeholder-title">特有层</div></div>
        <div class="placeholder-block"><div class="placeholder-title">背景层</div></div>
      </div>
    </div>

    <div v-else-if="mode === 'compare'" class="canvas-content compare-layout">
      <div class="compare-main-row">
        <div class="placeholder-block"><div class="placeholder-title">共享结构</div></div>
        <div class="placeholder-block"><div class="placeholder-title">差异结构</div></div>
      </div>
      <div class="compare-sub-row">
        <div class="placeholder-block"><div class="placeholder-title">缺失结构</div></div>
        <div class="placeholder-block"><div class="placeholder-title">冲突结构</div></div>
        <div class="placeholder-block"><div class="placeholder-title">数值比较</div></div>
      </div>
    </div>

    <div v-else class="canvas-content discovery-layout">
      <div class="placeholder-block large"><div class="placeholder-title">关系扩展主图</div></div>
      <div class="discovery-grid">
        <div class="placeholder-block"><div class="placeholder-title">解释链</div></div>
        <div class="placeholder-block"><div class="placeholder-title">新知识机会</div></div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  mode: { type: String, required: true },
  artifact: { type: Object, required: true },
  compareList: { type: Array, required: true }
})

const modeLabel = computed(() => {
  if (props.mode === 'compare') return `比较视图 · ${props.compareList.length} 件`
  if (props.mode === 'discovery') return '扩展发现'
  return '单文物结构'
})
</script>

<template>
  <div class="panel-card canvas-card">
    <div class="panel-header">
      <div>
        <h2>主工作区</h2>
        <p class="subtle">后续可接入 PDF、图谱、比较与发现可视化</p>
      </div>
      <span class="tag">{{ viewLabel }}</span>
    </div>

    <div class="tab-row">
      <button :class="['tab', mainView === 'source' ? 'active' : '']">来源</button>
      <button :class="['tab', mainView === 'graph' ? 'active' : '']">图谱</button>
      <button :class="['tab', mainView === 'compare' ? 'active' : '']">比较</button>
      <button :class="['tab', mainView === 'discover' ? 'active' : '']">发现</button>
    </div>

    <div class="canvas-layout">
      <div class="canvas-main dashed-box">
        <h3>{{ canvasTitle }}</h3>
        <p>{{ canvasText }}</p>
      </div>

      <div class="canvas-side">
        <div class="mini-card dashed-box">
          <h4>证据 / 候选区占位</h4>
          <p>后续接 PDF、OCR、高亮定位、候选知识列表。</p>
        </div>

        <div class="mini-card dashed-box">
          <h4>详情区占位</h4>
          <p>后续接节点详情、来源页、差异摘要、字段对比。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  mode: {
    type: String,
    required: true
  },
  mainView: {
    type: String,
    required: true
  }
})

const viewNames = {
  source: '来源视图',
  graph: '图谱视图',
  compare: '比较视图',
  discover: '发现视图'
}

const canvasByView = {
  source: {
    title: '来源材料浏览模板',
    text: '这里预留给 PDF 页面、OCR 文本叠加、高亮证据与页码定位。'
  },
  graph: {
    title: '知识图谱分析模板',
    text: '这里预留给单文物结构视图、层次卡片和关系组织。'
  },
  compare: {
    title: '多文物比较模板',
    text: '这里预留给共享结构、差异结构、缺失项和冲突项对比。'
  },
  discover: {
    title: '扩展发现模板',
    text: '这里预留给两跳扩展网络、路径解释与新增建议。'
  }
}

const viewLabel = computed(() => viewNames[props.mainView] || '主视图')
const canvasTitle = computed(() => canvasByView[props.mainView]?.title || '模板区')
const canvasText = computed(() => canvasByView[props.mainView]?.text || '待开发')
</script>

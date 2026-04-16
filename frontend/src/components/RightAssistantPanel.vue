<template>
  <div class="panel-card">
    <div class="panel-header">
      <h2>LLM 协同区</h2>
      <span class="tag">结构协商</span>
    </div>

    <section class="panel-section">
      <h3>当前上下文</h3>
      <ul class="context-list">
        <li>模式：{{ modeLabel }}</li>
        <li>主实体：古琴“襄”</li>
        <li>当前证据：第 12 页 OCR 片段</li>
        <li>当前任务：判断候选属性是否合理</li>
      </ul>
    </section>

    <section class="panel-section">
      <h3>快捷提问</h3>
      <button class="full-button">解释为什么归到这一层</button>
      <button class="full-button">判断是属性还是关系</button>
      <button class="full-button">给出补充建议</button>
    </section>

    <section class="panel-section dashed-box">
      <h3>结构化建议卡片</h3>
      <p>action_type: move_layer</p>
      <p>target: 断纹</p>
      <p>reason: 与实体特有工艺相关</p>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  mode: {
    type: String,
    required: true
  }
})

const labels = {
  single: '单文物模式',
  candidate: '候选校验模式',
  compare: '多文物比较模式',
  discovery: '扩展发现模式'
}

const modeLabel = computed(() => labels[props.mode] || '未定义模式')
</script>

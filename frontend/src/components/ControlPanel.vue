<template>
  <div class="panel-card">
    <div class="panel-header">
      <h2>控制区</h2>
      <span class="tag">必要结构</span>
    </div>

    <section class="panel-section">
      <h3>当前模式</h3>
      <p>{{ modeLabel }}</p>
    </section>

    <section class="panel-section">
      <h3>图层显示</h3>
      <label><input type="checkbox" checked /> 公有基础层</label>
      <label><input type="checkbox" checked /> 实体特有层</label>
      <label><input type="checkbox" /> 背景扩展层</label>
      <label><input type="checkbox" checked /> 候选知识</label>
    </section>

    <section class="panel-section">
      <h3>快速过滤</h3>
      <input type="text" placeholder="搜索主实体" />
      <select>
        <option>全部朝代</option>
        <option>唐</option>
        <option>宋</option>
        <option>明</option>
        <option>清</option>
      </select>
    </section>

    <section class="panel-section">
      <h3>全局操作</h3>
      <div class="button-group">
        <button>重置</button>
        <button>导出</button>
      </div>
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

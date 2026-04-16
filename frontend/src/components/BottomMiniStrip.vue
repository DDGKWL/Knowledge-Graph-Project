<template>
  <footer class="bottom-strip panel">
    <div class="strip-item">
      <span class="strip-label">当前模式</span>
      <strong>{{ modeText }}</strong>
    </div>
    <div class="strip-item">
      <span class="strip-label">比较对象</span>
      <strong>{{ compareCount }}</strong>
    </div>
    <div class="strip-item">
      <span class="strip-label">状态</span>
      <strong>单页工作台</strong>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  mode: { type: String, required: true },
  compareCount: { type: Number, required: true }
})

const modeText = computed(() => {
  if (props.mode === 'compare') return '多文物比较'
  if (props.mode === 'discovery') return '扩展发现'
  return '单文物理解'
})
</script>

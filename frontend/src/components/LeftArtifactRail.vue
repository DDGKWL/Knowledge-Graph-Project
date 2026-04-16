<template>
  <aside class="left-rail panel">
    <div class="section-title">结构入口</div>

    <div class="mini-mode-map">
      <button class="mode-chip active">对象</button>
      <button class="mode-chip">图层</button>
      <button class="mode-chip">比较篮</button>
    </div>

    <div class="artifact-card-list">
      <button
        v-for="item in artifacts"
        :key="item.id"
        class="artifact-card"
        :class="{ selected: selectedId === item.id }"
        @click="$emit('select', item.id)"
      >
        <div class="artifact-thumb">{{ item.image }}</div>
        <div class="artifact-main">
          <div class="artifact-name-row">
            <span class="artifact-name">{{ item.name }}</span>
            <span class="artifact-era">{{ item.era }}</span>
          </div>
          <div class="artifact-sub">{{ item.category }}</div>
          <div class="artifact-metrics">
            <span>候选 {{ item.candidateCount }}</span>
            <span class="compare-dot" :class="{ on: compareList.includes(item.id) }"></span>
          </div>
        </div>
        <div class="compare-toggle" @click.stop="$emit('toggle-compare', item.id)">
          {{ compareList.includes(item.id) ? '移出' : '加入' }}
        </div>
      </button>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  artifacts: { type: Array, required: true },
  selectedId: { type: String, required: true },
  compareList: { type: Array, required: true }
})

defineEmits(['select', 'toggle-compare'])
</script>

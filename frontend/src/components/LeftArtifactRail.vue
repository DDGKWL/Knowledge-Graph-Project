<template>
  <aside class="left-rail panel">
    <div class="section-title">结构入口</div>

    <div class="mini-mode-map">
      <button
        type="button"
        class="mode-chip"
        :class="{ active: activePanel === 'objects' }"
        @click="activePanel = 'objects'"
      >
        对象
      </button>
      <button
        type="button"
        class="mode-chip"
        :class="{ active: activePanel === 'books' }"
        @click="activePanel = 'books'"
      >
        书目
      </button>
      <button
        type="button"
        class="mode-chip"
        :class="{ active: activePanel === 'compare' }"
        @click="activePanel = 'compare'"
      >
        比较栏
      </button>
    </div>

    <div v-if="activePanel === 'books'" class="book-panel">
      <p class="book-panel-hint">选择要在主图中加载的文献（至少 1 本）</p>
      <div v-if="!availableBooks.length" class="compare-basket-empty">正在加载书目…</div>
      <label
        v-for="book in availableBooks"
        :key="bookCode(book)"
        class="book-panel-item"
      >
        <input
          type="checkbox"
          :checked="selectedBooks.includes(bookCode(book))"
          @change="$emit('toggle-book', bookCode(book))"
        />
        <span
          class="book-panel-dot"
          :style="{ background: bookColor(bookCode(book)) }"
          aria-hidden="true"
        />
        <span class="book-panel-name">{{ bookLabel(book) }}</span>
      </label>
    </div>

    <div v-else-if="activePanel === 'compare'" class="artifact-card-list">
      <div v-if="compareArtifacts.length === 0" class="compare-basket-empty">
        在「对象」列表中将文物「加入」比较后，会显示在这里
      </div>
      <div
        v-for="item in compareArtifacts"
        :key="item.id"
        class="artifact-card compare-only-card"
      >
        <div class="artifact-thumb">{{ item.image }}</div>
        <div class="artifact-main">
          <div class="artifact-name-row">
            <span class="artifact-name">{{ item.name }}</span>
          </div>
          <div class="artifact-sub">{{ item.id }}</div>
        </div>
        <div class="compare-toggle" @click="$emit('toggle-compare', item.id)">移出</div>
      </div>
    </div>

    <div v-else class="artifact-card-list">
      <div v-if="queueArtifacts.length === 0" class="compare-basket-empty">
        点击图谱中的文物节点后会加入这里
      </div>
      <div
        v-for="item in queueArtifacts"
        :key="item.id"
        class="artifact-card"
        :class="{ selected: selectedId === item.id }"
        @click="$emit('select', item.id)"
      >
        <span class="compare-basket-remove" @click.stop="$emit('remove-from-queue', item.id)">×</span>
        <div class="artifact-thumb">{{ item.image }}</div>
        <div class="artifact-main">
          <div class="artifact-name-row">
            <span class="artifact-name">{{ item.name }}</span>
            <span class="artifact-era">{{ item.era || '-' }}</span>
          </div>
          <div class="artifact-sub">{{ item.category || '文物节点' }}</div>
          <div class="artifact-metrics">
            <span>ID {{ item.id }}</span>
            <span class="compare-dot" :class="{ on: inCompareList(item.id) }"></span>
          </div>
        </div>
        <div class="compare-toggle" @click.stop="$emit('toggle-compare', item.id)">
          {{ inCompareList(item.id) ? '移出' : '加入' }}
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import { BOOK_COLOR_MAP } from '@/utils/graphConfig'
import { bookCode, bookLabel } from '@/utils/bookUtils'

const props = defineProps({
  queueArtifacts: { type: Array, default: () => [] },
  selectedId: { type: String, required: true },
  compareList: { type: Array, default: () => [] },
  availableBooks: { type: Array, default: () => [] },
  selectedBooks: { type: Array, default: () => [] },
})

defineEmits(['select', 'remove-from-queue', 'toggle-compare', 'toggle-book'])

const activePanel = ref('objects')

function bookColor(book) {
  const key = String(book || '').trim().toLowerCase()
  return BOOK_COLOR_MAP[key] || '#888'
}

function inCompareList(nodeId) {
  return props.compareList.some((x) => String(x) === String(nodeId))
}

const compareArtifacts = computed(() => {
  const ids = props.compareList.map((id) => String(id))
  const byId = new Map(props.queueArtifacts.map((item) => [String(item.id), item]))
  return ids
    .map((id) => {
      const item = byId.get(id)
      if (item) return item
      return { id, name: id, image: '文' }
    })
    .filter(Boolean)
})
</script>

<style scoped>
.book-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  overflow: auto;
}

.book-panel-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--muted, #7a6f62);
}

.book-panel-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(184, 159, 119, 0.28);
  background: rgba(255, 255, 255, 0.55);
  cursor: pointer;
  user-select: none;
  font-size: 13px;
}

.book-panel-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.book-panel-name {
  font-weight: 600;
  color: var(--text, #3f3427);
}

.compare-only-card {
  cursor: default;
}
</style>

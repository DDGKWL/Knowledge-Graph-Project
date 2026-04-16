<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="title-group">
        <h1>文物知识构建与可视分析系统</h1>
        <p>Vue 前端模板 · 单页工作台</p>
      </div>

      <div class="toolbar">
        <select v-model="mode">
          <option value="single">单文物模式</option>
          <option value="candidate">候选校验模式</option>
          <option value="compare">多文物比较模式</option>
          <option value="discovery">扩展发现模式</option>
        </select>

        <select v-model="mainView">
          <option value="source">来源视图</option>
          <option value="graph">图谱视图</option>
          <option value="compare">比较视图</option>
          <option value="discover">发现视图</option>
        </select>

        <button>保存工作区</button>
      </div>
    </header>

    <main class="workspace">
      <aside class="left-panel">
        <ControlPanel :mode="mode" />
      </aside>

      <section class="center-panel">
        <MainCanvas :mode="mode" :main-view="mainView" />
      </section>

      <aside class="right-panel">
        <RightAssistantPanel :mode="mode" />
      </aside>
    </main>

    <footer class="bottom-bar">
      <BottomStatusBar />
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ControlPanel from './components/ControlPanel.vue'
import MainCanvas from './components/MainCanvas.vue'
import RightAssistantPanel from './components/RightAssistantPanel.vue'
import BottomStatusBar from './components/BottomStatusBar.vue'

const mode = ref('single')
const mainView = ref('graph')
</script>

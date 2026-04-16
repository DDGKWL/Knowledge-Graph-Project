<template>
  <div class="app-shell">
    <header class="top-bar">
      <div class="brand-panel">
        <div class="seal-mark"></div>
        <div class="brand-copy">
          <div class="brand-cn">数字文博知识构建与可视分析工作台</div>
          <div class="brand-en">Digital Heritage Knowledge Workbench</div>
        </div>
      </div>

      <div class="top-actions">
        <button v-for="item in modes" :key="item" class="ghost-btn">{{ item }}</button>
      </div>
    </header>

    <main class="workspace-grid">
      <aside class="left-rail heritage-panel">
        <div class="panel-header">
          <div class="panel-index">壹</div>
          <div class="panel-title-group">
            <h2>对象入口</h2>
            <p>Entry</p>
          </div>
        </div>

        <div class="rail-stack">
          <div class="empty-slot short"></div>
          <div class="empty-slot medium"></div>
          <div class="empty-slot tall"></div>
          <div class="empty-slot tall"></div>
        </div>
      </aside>

      <section class="center-stage heritage-panel">
        <div class="panel-header panel-header-wide">
          <div class="panel-index">贰</div>
          <div class="panel-title-group panel-title-flex">
            <div>
              <h2>主分析画布</h2>
              <p>Main Analysis Canvas</p>
            </div>
            <div class="sub-switches">
              <button class="switch-btn active">结构</button>
              <button class="switch-btn">比较</button>
              <button class="switch-btn">发现</button>
            </div>
          </div>
        </div>

        <div class="center-grid">
          <div class="hero-canvas empty-slot"></div>
          <div class="center-side">
            <div class="empty-slot side-top"></div>
            <div class="empty-slot side-bottom"></div>
          </div>
        </div>
      </section>

      <aside class="right-rail heritage-panel">
        <div class="panel-header">
          <div class="panel-index">叁</div>
          <div class="panel-title-group">
            <h2>证据与协同</h2>
            <p>Evidence & Collaboration</p>
          </div>
        </div>

        <div class="tab-strip">
          <button class="switch-btn active">证据</button>
          <button class="switch-btn">候选</button>
          <button class="switch-btn">讨论</button>
        </div>

        <div class="rail-stack right-stack">
          <div class="empty-slot medium"></div>
          <div class="empty-slot tall"></div>
          <div class="empty-slot tall"></div>
        </div>
      </aside>
    </main>

    <footer class="bottom-strip heritage-panel">
      <div class="strip-chip" v-for="n in 5" :key="n">
        <div class="chip-dot"></div>
        <div class="chip-line"></div>
      </div>
    </footer>
  </div>
</template>

<script setup>
const modes = ['单文物', '比较分析', '知识扩展']
</script>

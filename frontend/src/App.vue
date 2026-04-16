<template>
  <div class="app-shell">
    <header class="top-bar shell-panel">
      <div class="brand-block">
        <div class="brand-mark"></div>
        <div class="brand-copy">
          <div class="brand-title">Artifact Knowledge Visual Analytics</div>
          <div class="brand-subtitle">Empty layout shell for redesign and later interaction development</div>
        </div>
      </div>

      <div class="top-actions">
        <div class="pill-group">
          <button v-for="item in modes" :key="item" class="pill-btn">{{ item }}</button>
        </div>
        <div class="pill-group compact">
          <button class="pill-btn ghost">Save</button>
          <button class="pill-btn ghost">Export</button>
        </div>
      </div>
    </header>

    <main class="workspace-grid">
      <section class="left-rail shell-panel">
        <div class="section-head">
          <span class="section-tag">A</span>
          <div>
            <h2>Entry</h2>
            <p>Structure entry and filter shell</p>
          </div>
        </div>

        <div class="rail-stack">
          <div class="empty-box soft h-56"></div>
          <div class="empty-box soft h-140"></div>
          <div class="empty-box soft h-140"></div>
          <div class="empty-box soft h-140"></div>
        </div>
      </section>

      <section class="center-stage shell-panel">
        <div class="section-head center-head">
          <span class="section-tag">B</span>
          <div>
            <h2>Knowledge Exploration</h2>
            <p>Main canvas only, all inner content intentionally empty</p>
          </div>
          <div class="canvas-tabs">
            <button class="tab-btn active">Structure</button>
            <button class="tab-btn">Compare</button>
            <button class="tab-btn">Discover</button>
          </div>
        </div>

        <div class="canvas-layout">
          <div class="canvas-primary empty-box h-full"></div>
          <div class="canvas-side-stack">
            <div class="empty-box h-half"></div>
            <div class="empty-box h-half"></div>
          </div>
        </div>
      </section>

      <section class="right-rail shell-panel">
        <div class="section-head">
          <span class="section-tag">C</span>
          <div>
            <h2>Evidence & Interpretation</h2>
            <p>Assistant rail shell</p>
          </div>
        </div>

        <div class="rail-tabs">
          <button class="tab-btn active">Evidence</button>
          <button class="tab-btn">Candidate</button>
          <button class="tab-btn">AI</button>
        </div>

        <div class="rail-stack">
          <div class="empty-box h-96"></div>
          <div class="empty-box h-180"></div>
          <div class="empty-box h-180"></div>
        </div>
      </section>
    </main>

    <footer class="bottom-strip shell-panel">
      <div class="status-chip" v-for="n in 5" :key="n">
        <div class="status-dot"></div>
        <div class="status-line"></div>
      </div>
    </footer>
  </div>
</template>

<script setup>
const modes = ['Single Artifact', 'Compare', 'Enrich']
</script>

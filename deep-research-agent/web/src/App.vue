<template>
  <div class="app-container">
    <ParticleBg />
    <header class="app-header">
      <h1 class="app-title">Deep Research Agent</h1>
      <p class="app-subtitle">多智能体深度研究系统</p>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import ParticleBg from './components/ParticleBg.vue'
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  position: relative;
}
.app-header {
  text-align: center;
  padding: 2rem 1rem 1rem;
  position: relative;
  z-index: 1;
}
.app-title {
  font-size: 2rem;
  background: linear-gradient(135deg, #00d4ff, #7b2fff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}
.app-subtitle {
  color: #8892b0;
  margin: 0.5rem 0 0;
  font-size: 1rem;
}
.app-main {
  position: relative;
  z-index: 1;
  max-width: 960px;
  margin: 0 auto;
  padding: 1rem;
}
</style>

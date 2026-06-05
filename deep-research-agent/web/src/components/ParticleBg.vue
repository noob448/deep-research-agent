<template>
  <VueParticles
    id="tsparticles"
    class="particle-container"
    :options="particleOptions"
  />
</template>

<script setup>
const particleOptions = {
  fullScreen: { enable: false },
  fpsLimit: 60,
  particles: {
    color: { value: '#00f0ff' },
    links: {
      color: '#00f0ff',
      distance: 150,
      enable: true,
      opacity: 0.15,
      width: 1
    },
    move: {
      enable: true,
      speed: 0.6,
      direction: 'none',
      random: true,
      straight: false,
      outModes: { default: 'bounce' }
    },
    number: {
      density: { enable: true },
      value: 60
    },
    opacity: {
      value: { min: 0.1, max: 0.4 },
      animation: {
        enable: true,
        speed: 0.5,
        minimumValue: 0.1
      }
    },
    shape: { type: 'circle' },
    size: {
      value: { min: 1, max: 2.5 }
    }
  },
  interactivity: {
    events: {
      onHover: {
        enable: true,
        mode: 'grab'
      }
    },
    modes: {
      grab: {
        distance: 140,
        links: {
          opacity: 0.3
        }
      }
    }
  },
  detectRetina: true
}
</script>

<style scoped>
.particle-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}

.particle-container :deep(canvas) {
  pointer-events: auto !important;
}
</style>

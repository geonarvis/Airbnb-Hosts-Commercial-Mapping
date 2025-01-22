<template>
  <div class="loading-spinner">
    <div class="progress-container">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
      </div>
    </div>
    <div class="loading-text">
      <div class="loading-title">Loading city data...</div>
      <div class="loading-step">{{ currentStep }}</div>
      <div class="loading-note">Free AWS server = Slow Speed 🐌</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoadingSpinner',
  props: {
    progress: {
      type: Number,
      default: 0
    },
    currentStep: {
      type: String,
      default: 'Loading basic info...'
    }
  }
}
</script>

<style scoped>
.loading-spinner {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 9999;
  background-color: rgba(255, 255, 255, 0.95);
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  min-width: 300px;
  pointer-events: none;
}

.progress-container {
  width: 100%;
}

.progress-bar {
  width: 100%;
  height: 4px;
  background-color: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: #4f46e5;
  transition: width 0.3s ease;
}

.loading-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.loading-title {
  color: #4f46e5;
  font-weight: 600;
  font-size: 1.1rem;
}

.loading-step {
  font-size: 0.9rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.loading-note {
  font-size: 0.8rem;
  color: #9ca3af;
  font-style: italic;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px dashed #e5e7eb;
  width: 100%;
  text-align: center;
}
</style> 
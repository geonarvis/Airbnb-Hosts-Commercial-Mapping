<template>
  <button
    class="about-button"
    :class="{ active: aboutToggle }"
    @click="$emit('toggle')"
  >
    <span>{{ aboutToggle ? "×" : "i" }}</span>
  </button>
</template>

<script>
export default {
  name: 'AboutButton',
  props: {
    aboutToggle: {
      type: Boolean,
      default: false
    }
  },
  emits: ['toggle']
}
</script>

<style>
.about-button {
  position: fixed;
  left: calc(var(--sidebar-width) + 8px);
  top: 1rem;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #fff187;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #000000;
  z-index: 30;
  transition: left 0.3s ease;
}

.about-button:hover {
  background-color: #ffd000;
}

.about-button.active {
  background-color: #fff187;
  color: #000000;
}

.sidebar-container.collapsed ~ .about-button {
  left: 8px;
}
</style> 
<template>
  <div class="loading-container">
    <div class="flex justify-center items-center">
      <div class="animate-spin rounded-full h-10 w-10 border-t-4 border-b-4 border-green-500"></div>
    </div>
    <div class="ml-2 text-RobotoMono text-header">Loading</div>
  </div>
</template>

<script>
export default {
  name: 'LoadingSpinner'
}
</script>

<style scoped>
.loading-container {
  position: absolute;
  right: 0;
  top: 0;
  z-index: 10;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  margin: 1rem;
}
</style> 
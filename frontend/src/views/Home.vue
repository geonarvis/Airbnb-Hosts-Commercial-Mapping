<template>
  <div class="home-container">
    <MapView 
      :isSidebarCollapsed="isSidebarCollapsed"
      :selectedLocation="selectedLocation"
      :selectedHostTypes="selectedHostTypes"
      :currentTime="currentTime"
      :isHexMode="isHexMode"
      :pointStyle="pointStyle"
    />
    <Sidebar 
      :aboutToggle="aboutToggle" 
      @collapse-change="handleSidebarCollapse" 
      @city-selected="handleCitySelect"
      @time-changed="handleTimeChange"
      @host-types-changed="handleHostTypesChange"
      @view-mode-changed="handleViewModeChange"
      @loading="handleLoading"
      @style-changed="handleStyleChange"
      :class="{ 'collapsed': isSidebarCollapsed }"
    />
    <AboutButton 
      :aboutToggle="aboutToggle" 
      @toggle="aboutToggle = !aboutToggle" 
      :class="{ 'z-20': true }"
    />
    <LoadingSpinner 
      v-if="loadingState.show" 
      :progress="loadingState.progress"
      :currentStep="loadingState.step"
    />
  </div>
</template>

<script>
import { ref } from 'vue'
import MapView from '../components/MapView.vue'
import Sidebar from '../components/Sidebar.vue'
import AboutButton from '../components/AboutButton.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

export default {
  name: 'Home',
  components: {
    MapView,
    Sidebar,
    AboutButton,
    LoadingSpinner
  },
  setup() {
    const aboutToggle = ref(false)
    const loadingState = ref({
      show: false,
      progress: 0,
      step: ''
    })
    const isSidebarCollapsed = ref(false)
    const selectedLocation = ref(null)
    const selectedHostTypes = ref([])
    const currentTime = ref(null)
    const isHexMode = ref(false)
    const pointStyle = ref({
      size: 4,
      opacity: 0.8
    })

    const handleSidebarCollapse = (collapsed) => {
      isSidebarCollapsed.value = collapsed
    }

    const handleCitySelect = (location) => {
      selectedLocation.value = location
    }

    const handleTimeChange = (timestamp) => {
      const timeValue = Number(timestamp)
      currentTime.value = timeValue
      console.log('Time changed:', new Date(timeValue))
    }

    const handleHostTypesChange = (types) => {
      selectedHostTypes.value = types
    }

    const handleViewModeChange = (mode) => {
      isHexMode.value = mode
    }

    const handleLoading = (state) => {
      console.log('Loading state changed:', state)
      loadingState.value = state
    }

    const handleStyleChange = (style) => {
      pointStyle.value = style
    }

    return {
      aboutToggle,
      loadingState,
      isSidebarCollapsed,
      handleSidebarCollapse,
      selectedLocation,
      handleCitySelect,
      handleTimeChange,
      selectedHostTypes,
      currentTime,
      handleHostTypesChange,
      isHexMode,
      handleViewModeChange,
      handleLoading,
      pointStyle,
      handleStyleChange
    }
  }
}
</script>

<style>
.home-container {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

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

.loading-spinner {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 2rem;
  border-radius: 1rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}
</style>

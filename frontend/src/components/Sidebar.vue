<template>
  <div 
    id="sidebar" 
    class="sidebar-container transition-all duration-300"
    :class="{ 'collapsed': isCollapsed }"
  >
    <div class="sidebar-content" :class="{ 'opacity-0': isCollapsed }">
      <div class="title-box inline-flex" v-show="!aboutToggle">
        <h1 class="font-Roboto text-title text-bold">Airbnb Hosts Visualization</h1>
        <div class="ml-2 text-gray-75 text-detail self-end">
          v.{{ version }}
        </div>
      </div>

      <div v-show="!aboutToggle" class="controls-section mt-4">
        <div class="city-select mb-4">
          <label class="block text-sm font-medium text-gray-500 mb-2">City Select</label>
          <div class="relative">
            <select 
              v-model="selectedCity" 
              @change="onCityChange"
              class="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">Select a city below</option>
              <option v-for="city in cities" :key="city" :value="city">
                {{ city }}
              </option>
            </select>
          </div>
          <div class="mt-2">
            <button
              @click="toggleViewMode"
              class="w-full p-2 text-sm bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {{ isHexMode ? 'Switch to Points' : 'Switch to Hexagons' }}
            </button>
          </div>
        </div>

        <div v-if="cityInfo" class="time-slider mb-4">
          <label class="block text-sm font-medium text-gray-500 mb-2">Time Point Choose</label>
          <div class="time-range flex justify-between text-xs text-gray-500 mb-1">
            <span>{{ formatDate(timeRange[0]) }}</span>
            <span class="current-time" :class="{ 'text-gray-400': currentTime !== internalTime }">
              {{ formatDate(internalTime) }}
            </span>
            <span>{{ formatDate(timeRange[1]) }}</span>
          </div>
          <div class="relative pt-1">
            <input
              type="range"
              v-model="currentTime"
              :min="timeRange[0]"
              :max="timeRange[1]"
              :step="2629746000"
              class="
                w-full
                h-2
                rounded-lg
                appearance-none
                cursor-pointer
                range-slider
              "
              @input="onTimeChange"
            />
          </div>
        </div>

        <div v-if="cityInfo" class="host-types mb-4">
          <label class="block text-sm font-medium text-gray-500 mb-2">Host Type Select</label>
          <div class="space-y-2">
            <label v-for="(label, category) in hostTypeLabels" 
              :key="category" 
              class="flex items-center cursor-pointer"
            >
              <input 
                type="checkbox"
                v-model="selectedHostTypes"
                :value="category"
                class="checkbox-input"
              >
              <span class="ml-2 text-sm text-gray-600">{{ label }}</span>
            </label>
          </div>
        </div>

        <div v-if="cityInfo" class="yearly-stats mb-4">
          <div class="flex justify-between items-center mb-2">
            <label class="text-sm font-medium text-gray-500">
              Listing Count Statistics - {{ isListingMode ? 'Listings' : 'Hosts' }}
            </label>
            <button
              @click="isListingMode = !isListingMode"
              class="px-2 py-1 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {{ isListingMode ? 'Show Host Data' : 'Show Listing Data' }}
            </button>
          </div>
          <apexchart
            type="bar"
            height="350"
            :options="chartOptions"
            :series="chartSeries"
          />
          <apexchart
            type="line"
            height="250"
            :options="lineChartOptions"
            :series="lineChartSeries"
          />
        </div>
      </div>

      <About v-if="aboutToggle" />
    </div>

    <button 
      class="toggle-button"
      @click="toggleSidebar"
      :class="{ 'collapsed': isCollapsed }"
    >
      <span class="arrow-icon">
        {{ isCollapsed ? '❯' : '❮' }}
      </span>
    </button>
  </div>
</template>

<script>
import About from './About.vue'
import { computed, ref, onMounted, watch, onUnmounted } from 'vue'
import { useStore } from 'vuex'
import api from '../api'
import { debounce } from 'lodash'
import VueApexCharts from 'vue3-apexcharts'

export default {
  name: 'Sidebar',
  components: {
    About,
    apexchart: VueApexCharts
  },
  props: {
    aboutToggle: {
      type: Boolean,
      required: true
    }
  },
  setup(props, { emit }) {
    const store = useStore()
    const version = computed(() => store.state.version)
    const isCollapsed = ref(false)
    const cities = ref([])
    const selectedCity = ref('')
    const cityInfo = ref(null)
    const timeRange = ref([0, 0])
    const currentTime = ref(0)
    const selectedHostTypes = ref([])
    const isHexMode = ref(false)
    const hostTypeLabels = ref({
      highly_commercial: 'Highly Commercial',
      commercial: 'Commercial',
      semi_commercial: 'Semi-Commercial',
      dual_host: 'Dual Host',
      single_host: 'Single Host'
    })

    const internalTime = ref(0)
    const isListingMode = ref(true)  // 默认显示房源数据

    const debouncedTimeChange = debounce((value) => {
      emit('time-changed', value)
    }, 1000)

    const toggleSidebar = () => {
      isCollapsed.value = !isCollapsed.value
      emit('collapse-change', isCollapsed.value)
    }

    const formatDate = (timestamp) => {
      const date = new Date(parseInt(timestamp))
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long'
      })
    }

    const fetchCities = async () => {
      try {
        const response = await api.get('/cities')
        cities.value = response.data.cities
      } catch (error) {
        console.error('Failed to fetch city list:', error)
      }
    }

    const onCityChange = async () => {
      console.log('City change started:', selectedCity.value)
      if (!selectedCity.value) {
        cityInfo.value = null
        selectedHostTypes.value = []
        emit('loading', { show: false })
        return
      }
      
      try {
        emit('loading', { 
          show: true, 
          progress: 0, 
          step: 'Loading basic info...' 
        })
        
        const response = await api.get(`/city/${selectedCity.value}`)
        console.log('Basic info loaded:', response.data)
        
        emit('loading', { 
          show: true, 
          progress: 30, 
          step: 'Loading city statistics...' 
        })
        
        cityInfo.value = response.data
        selectedHostTypes.value = []
        
        // Update time range
        timeRange.value = [
          new Date(cityInfo.value.time_window.earliest).getTime(),
          new Date(cityInfo.value.time_window.latest).getTime()
        ]
        
        const timeWindowMiddle = Math.floor(
          (timeRange.value[0] + timeRange.value[1]) / 2
        )
        currentTime.value = timeWindowMiddle
        internalTime.value = timeWindowMiddle
        
        emit('loading', { 
          show: true, 
          progress: 60, 
          step: 'Loading host rankings...' 
        })
        await updateHostRanking()
        
        emit('loading', { 
          show: true, 
          progress: 80, 
          step: 'Loading yearly statistics...' 
        })
        await updateYearlyStats(selectedCity.value)
        
        emit('city-selected', {
          city: selectedCity.value,
          center: {
            latitude: cityInfo.value.center.latitude,
            longitude: cityInfo.value.center.longitude
          },
          zoom: 12
        })
        emit('loading', { show: true, progress: 100, step: 'Complete!' })
      } catch (error) {
        console.error('Failed to fetch city info:', {
          error,
          city: selectedCity.value,
          stack: error.stack
        })
        emit('loading', { show: false })
        return
      } finally {
        console.log('City change completed')
        setTimeout(() => {
          emit('loading', { show: false })
        }, 500)
      }
    }

    const onTimeChange = () => {
      internalTime.value = currentTime.value
      debouncedTimeChange(currentTime.value)
      updateHostRanking()
    }

    const debouncedUpdateHostRanking = debounce(async () => {
      if (!selectedCity.value || !currentTime.value) return
      
      try {
        const date = new Date(Number(currentTime.value))
        const timeStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
        
        const response = await api.get(
          `/city/${selectedCity.value}/host_ranking`,
          {
            params: {
              time_point: timeStr
            }
          }
        )
        
        // 更新房东类型标签，显示每种类型的范围
        if (response.data.host_categories) {
          const categories = response.data.host_categories
          hostTypeLabels.value = {
            highly_commercial: `Highly Commercial (${categories.highly_commercial.range?.min || 0}-${categories.highly_commercial.range?.max || 0} listings)`,
            commercial: `Commercial (${categories.commercial.range?.min || 0}-${categories.commercial.range?.max || 0} listings)`,
            semi_commercial: `Semi-Commercial (${categories.semi_commercial.range?.min || 0}-${categories.semi_commercial.range?.max || 0} listings)`,
            dual_host: 'Dual Host (2 listings)',
            single_host: 'Single Host (1 listing)'
          }
        }
      } catch (error) {
        console.error('Failed to fetch host ranking:', error)
      }
    }, 500)

    const updateHostRanking = () => {
      debouncedUpdateHostRanking()
    }

    // 监听房东类型选择变化
    watch(selectedHostTypes, (newTypes) => {
      if (selectedCity.value && cityInfo.value) {
        emit('host-types-changed', newTypes)
      }
    })

    const toggleViewMode = () => {
      isHexMode.value = !isHexMode.value
      emit('view-mode-changed', isHexMode.value)
    }

    const chartOptions = ref({
      chart: {
        stacked: true,
        toolbar: { show: false },
        type: 'bar'
      },
      plotOptions: {
        bar: {
          horizontal: false,
          columnWidth: '70%',
          distributed: false,
          borderRadius: 0,
          rangeBarOverlap: true,
          rangeBarGroupRows: false
        }
      },
      xaxis: {
        categories: [],
        title: {
          text: 'Year'
        },
        labels: {
          rotate: -45,
          style: {
            fontSize: '12px'
          }
        },
        tickPlacement: 'on'
      },
      yaxis: [
        {
          title: { text: 'Percentage (%)' },
          max: 100,
          labels: {
            formatter: function(val) {
              return val.toFixed(0) + '%'
            }
          }
        }
      ],
      colors: ['#4169E1', '#32CD32', '#FFD700', '#FFA500', '#FF4500'],
      dataLabels: {
        enabled: true,
        formatter: function(val) {
          if (val > 5) {
            return Math.round(val)
          }
          return ''
        },
        style: {
          colors: ['#000000'],
          fontSize: '11px',
          fontWeight: 400
        }
      },
      legend: {
        show: false
      },
      tooltip: {
        shared: true,
        intersect: false,
        followCursor: true,
        y: {
          formatter: function(val) {
            return val.toFixed(1) + '%'
          }
        },
        fixed: {
          enabled: false
        },
        position: 'top',
        marker: {
          show: false
        }
      }
    })

    const chartSeries = ref([])
    const lineChartSeries = ref([])

    const lineChartOptions = ref({
      chart: {
        type: 'line',
        toolbar: { show: false }
      },
      stroke: {
        width: 2,
        curve: 'smooth'
      },
      xaxis: {
        categories: [],
        type: 'numeric',
        labels: {
          formatter: (val) => Math.round(val),
          style: {
            fontSize: '12px'
          }
        },
        title: {
          text: 'Year'
        }
      },
      yaxis: {
        title: { text: 'Number' },
        labels: {
          formatter: (val) => Math.round(val)
        }
      },
      colors: ['#4169E1', '#32CD32', '#FFD700', '#FFA500', '#FF4500'],
      legend: {
        position: 'bottom'
      },
      markers: {
        size: 0
      }
    })

    const updateYearlyStats = async (cityName) => {
      try {
        const response = await api.get(`/city/${cityName}/yearly_stats`)
        
        const stats = response.data.yearly_stats
        const startYear = new Date(cityInfo.value.time_window.earliest).getFullYear() + 1
        const endYear = new Date(cityInfo.value.time_window.latest).getFullYear()
        const years = []
        for (let year = startYear; year <= endYear; year++) {
          years.push(year)
        }
        
        // 更新柱状图配置
        chartOptions.value = {
          ...chartOptions.value,
          xaxis: {
            ...chartOptions.value.xaxis,
            categories: years,
            type: 'numeric',
            tickAmount: years.length,
            labels: {
              formatter: (val) => Math.round(val),
              rotate: -45,
              style: {
                fontSize: '12px'
              }
            }
          }
        }
        
        // 更新折线图配置
        lineChartOptions.value = {
          ...lineChartOptions.value,
          xaxis: {
            ...lineChartOptions.value.xaxis,
            categories: years
          }
        }
        
        // 准备堆叠柱状图数据
        chartSeries.value = [
          {
            name: 'Single Host',
            type: 'bar',
            data: years.map(year => stats[year.toString()][isListingMode.value ? 'listing_percentages' : 'percentages'].single_host)
          },
          {
            name: 'Dual Host',
            type: 'bar',
            data: years.map(year => stats[year.toString()][isListingMode.value ? 'listing_percentages' : 'percentages'].dual_host)
          },
          {
            name: 'Semi Commercial',
            type: 'bar',
            data: years.map(year => stats[year.toString()][isListingMode.value ? 'listing_percentages' : 'percentages'].semi_commercial)
          },
          {
            name: 'Commercial',
            type: 'bar',
            data: years.map(year => stats[year.toString()][isListingMode.value ? 'listing_percentages' : 'percentages'].commercial)
          },
          {
            name: 'Highly Commercial',
            type: 'bar',
            data: years.map(year => stats[year.toString()][isListingMode.value ? 'listing_percentages' : 'percentages'].highly_commercial)
          }
        ]
        
        // 准备折线图数据
        lineChartSeries.value = [
          {
            name: 'Single Host',
            type: 'line',
            data: years.map(year => stats[year.toString()][isListingMode.value ? 'listing_counts' : 'counts'].single_host)
          },
          {
            name: 'Dual Host',
            type: 'line',
            data: years.map(year => stats[year.toString()][isListingMode.value ? 'listing_counts' : 'counts'].dual_host)
          },
          {
            name: 'Semi Commercial',
            type: 'line',
            data: years.map(year => stats[year.toString()][isListingMode.value ? 'listing_counts' : 'counts'].semi_commercial)
          },
          {
            name: 'Commercial',
            type: 'line',
            data: years.map(year => stats[year.toString()][isListingMode.value ? 'listing_counts' : 'counts'].commercial)
          },
          {
            name: 'Highly Commercial',
            type: 'line',
            data: years.map(year => stats[year.toString()][isListingMode.value ? 'listing_counts' : 'counts'].highly_commercial)
          }
        ]

      } catch (error) {
        console.error('Failed to fetch yearly stats:', error)
      }
    }

    // 添加对 isListingMode 的监听
    watch(isListingMode, () => {
      if (selectedCity.value) {
        updateYearlyStats(selectedCity.value)
      }
    })

    onMounted(() => {
      fetchCities()
    })

    onUnmounted(() => {
      debouncedTimeChange.cancel()
      debouncedUpdateHostRanking.cancel()
    })

    return {
      version,
      isCollapsed,
      toggleSidebar,
      cities,
      selectedCity,
      cityInfo,
      timeRange,
      currentTime,
      internalTime,
      onCityChange,
      onTimeChange,
      formatDate,
      selectedHostTypes,
      hostTypeLabels,
      isHexMode,
      toggleViewMode,
      chartOptions,
      chartSeries,
      lineChartOptions,
      lineChartSeries,
      isListingMode
    }
  }
}
</script>

<style>
.sidebar-container {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  position: fixed;
  left: 0;
  top: 0;
  height: 100%;
  background-color: white;
  font-family: Roboto, sans-serif;
  overflow: visible;
  box-shadow: 2px 0 10px rgba(0,0,0,0.1);
  transform: translateX(0);
  transition: transform 0.3s ease;
  z-index: 40;
}

.sidebar-container.collapsed {
  transform: translateX(-100%);
}

.sidebar-content {
  padding: 1rem;
  width: var(--sidebar-width);
  height: 100%;
  overflow-y: auto;
  transition: opacity 0.2s ease;
  background-color: white;
}

.toggle-button {
  position: absolute;
  right: -32px;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 64px;
  background-color: white;
  border: none;
  border-radius: 0 8px 8px 0;
  box-shadow: 2px 0 10px rgba(0,0,0,0.1);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.toggle-button:hover {
  background-color: #f0f0f0;
}

.toggle-button.collapsed {
  right: -32px;
  left: auto;
}

.arrow-icon {
  font-size: 20px;
  line-height: 1;
  color: #666;
  user-select: none;
}

/* 自定义下拉框样式 */
.custom-select {
  position: relative;
}

.select-input {
  appearance: none;
  background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
  padding-right: 2.5rem;
}

.range-slider {
  -webkit-appearance: none;
  background: #e5e7eb;
  height: 4px;
  border-radius: 2px;
  outline: none;
}

.range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  background: #ffffff;
  border: 2px solid #4f46e5;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  position: relative;
  z-index: 2;
}

.range-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}

.range-slider::-webkit-slider-thumb:active {
  transform: scale(1.1);
  background: #4f46e5;
  border-color: #4f46e5;
}

.range-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  background: #ffffff;
  border: 2px solid #4f46e5;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
}

.range-slider::-moz-range-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.15);
}

.range-slider::-moz-range-thumb:active {
  transform: scale(1.1);
  background: #4f46e5;
  border-color: #4f46e5;
}

.range-slider::-moz-range-progress {
  background-color: #4f46e5;
  height: 6px;
  border-radius: 3px;
}

.range-slider::-moz-range-track {
  background-color: #e5e7eb;
  height: 6px;
  border-radius: 3px;
}

.time-slider {
  position: relative;
  padding-top: 24px;
}

.time-range {
  position: relative;
  padding: 0 8px;
}

.current-time {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  color: #4f46e5;
  font-weight: 500;
  transition: color 0.3s ease;
}

.current-time.text-gray-400 {
  color: #9ca3af;
}

/* 自定义复选框样式 */
.checkbox-input {
  appearance: none;
  width: 16px;
  height: 16px;
  border: 2px solid #d1d5db;
  border-radius: 4px;
  margin-right: 8px;
  cursor: pointer;
  position: relative;
  background-color: white;
  transition: all 0.2s ease;
}

.checkbox-input:checked {
  background-color: #4f46e5;
  border-color: #4f46e5;
  background-image: url("data:image/svg+xml,%3csvg viewBox='0 0 16 16' fill='white' xmlns='http://www.w3.org/2000/svg'%3e%3cpath d='M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z'/%3e%3c/svg%3e");
  background-size: 100% 100%;
  background-position: center;
  background-repeat: no-repeat;
}

.checkbox-input:focus {
  outline: none;
  box-shadow: 0 0 0 2px #fff, 0 0 0 4px #4f46e5;
}

.host-types {
  padding: 8px 0;
}

.host-types label {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  cursor: pointer;
}

.host-types label:last-child {
  margin-bottom: 0;
}
</style> 
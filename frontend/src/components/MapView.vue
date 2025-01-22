<template>
  <div class="map-wrapper">
    <div id="map" class="map-container"></div>
  </div>
</template>

<script>
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { mapOptions } from '../assets/data'
import { onMounted, onUnmounted, watch } from 'vue'
import api from '../api'
import { debounce } from 'lodash'

export default {
  name: 'MapView',
  props: {
    isSidebarCollapsed: {
      type: Boolean,
      default: false
    },
    selectedLocation: {
      type: Object,
      default: () => null
    },
    selectedHostTypes: {
      type: Array,
      default: () => []
    },
    currentTime: {
      type: Number,
      default: null
    },
    isHexMode: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    let map = null
    let currentCenter = null
    let mousePosition = null
    let hexLayer = null
    const layerColors = {
      highly_commercial: '#FF0000',  // 红色
      commercial: '#FFA500',         // 橙色
      semi_commercial: '#FFFF00',    // 黄色
      dual_host: '#00FF00',         // 绿色
      single_host: '#0000FF'        // 蓝色
    }
    let popup = null

    onMounted(() => {
      mapboxgl.accessToken = 'pk.eyJ1Ijoia3BmdWkiLCJhIjoiY2p6MWcxMXl4MDFlbTNsbDc1bnp6N3FjYSJ9.66qFOXwI661MOPOf7x96yA'
      map = new mapboxgl.Map({
        ...mapOptions,
        container: 'map'
      })

      // 创建 popup
      popup = new mapboxgl.Popup({
        closeButton: false,
        closeOnClick: false
      })

      map.on('load', () => {
        console.debug('map loaded')
        // 为每种类型创建图层
        Object.entries(layerColors).forEach(([type, color]) => {
          map.addSource(`listings-${type}`, {
            type: 'geojson',
            data: {
              type: 'FeatureCollection',
              features: []
            }
          })
          
          map.addLayer({
            id: `listings-layer-${type}`,
            type: 'circle',
            source: `listings-${type}`,
            paint: {
              'circle-radius': 3,
              'circle-color': color,
              'circle-opacity': 0.35
            }
          })
        })

        // 添加网格图层的交互事件
        map.on('mousemove', 'hexgrid-layer', (e) => {
          if (e.features.length > 0) {
            map.getCanvas().style.cursor = 'pointer'
            
            const feature = e.features[0]
            const coordinates = e.lngLat
            
            // 构建弹出框内容
            const content = `
              <div class="popup-content">
                <div class="font-medium">Hex ID: ${feature.properties.id}</div>
                <div>Listings Count: ${feature.properties.points_count}</div>
              </div>
            `
            
            popup
              .setLngLat(coordinates)
              .setHTML(content)
              .addTo(map)
          }
        })

        map.on('mouseleave', 'hexgrid-layer', () => {
          map.getCanvas().style.cursor = ''
          popup.remove()
        })
      })

      map.on('mousemove', (e) => {
        mousePosition = e.lngLat
      })

      // 添加对密度轮廓的更新
      const updateDensityContours = async () => {
        // 直接返回，不执行密度轮廓的更新
        return;
      }
    })

    const updateListings = async (hostType) => {
      if (!props.selectedLocation?.city || !props.currentTime) {
        return
      }
      
      const date = new Date(Number(props.currentTime))
      const timeStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
      
      try {
        const response = await api.get(
          `/city/${props.selectedLocation.city}/listings_by_categories`,
          {
            params: {
              time_point: timeStr,
              categories: hostType
            }
          }
        )
        
        if (!response.data || !response.data.listings) {
          console.error('Invalid response format:', response.data)
          return
        }
        
        const features = response.data.listings.map(listing => ({
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [listing.longitude, listing.latitude]
          },
          properties: {
            host_id: listing.host_id,
            name: listing.name,
            price: listing.price
          }
        }))
        
        if (map.getSource(`listings-${hostType}`)) {
          map.getSource(`listings-${hostType}`).setData({
            type: 'FeatureCollection',
            features: features
          })
        }
      } catch (error) {
        console.error('Failed to fetch listings:', error)
      }
    }


    // 清除特定类型的图层数据
    const clearListings = (hostType) => {
      if (map.getSource(`listings-${hostType}`)) {
        map.getSource(`listings-${hostType}`).setData({
          type: 'FeatureCollection',
          features: []
        })
      }
    }

    watch(() => props.selectedLocation, (newLocation) => {
      if (!newLocation?.center?.latitude || !newLocation?.center?.longitude) {
        return;
      }

      if (newLocation && map) {
        const offset = [
          window.innerWidth * 0.2,
          0
        ]

        map.flyTo({
          center: [
            Number(newLocation.center.longitude),
            Number(newLocation.center.latitude)
          ],
          zoom: newLocation.zoom || 12,
          duration: 1000,
          offset: offset,
          around: mousePosition || [
            Number(newLocation.center.longitude),
            Number(newLocation.center.latitude)
          ]
        })
      }
    })

    // 添加一个变量来跟踪最后更新时间
    let lastUpdateTime = 0

    // 监听房东类型和时间变化
    watch(
      [() => props.selectedHostTypes, () => props.currentTime],
      async (newValue, oldValue) => {
        if (!map) {
          console.log('Map not ready yet')
          return
        }
        
        const [newTypes, newTime] = newValue
        const [oldTypes, oldTime] = oldValue || [[], null]
        
        // 如果只是时间变化，并且变化间隔小于 1000ms，不更新
        if (newTime !== oldTime && Date.now() - lastUpdateTime < 1000) {
          return
        }
        
        // 更新最后更新时间
        lastUpdateTime = Date.now()
        
        if (props.isHexMode) {
          updateHexGrid()
          return
        }
        
        // 如果时间发生变化，更新所有已选类型的房源
        if (newTime !== oldTime) {
          console.log('Time changed, updating all selected types')
          for (const type of newTypes) {
            await updateListings(type)
          }
        } else {
          // 如果只是类型发生变化，则只处理变化的类型
          const oldSet = new Set(oldTypes || [])
          const newSet = new Set(newTypes)
          
          // 处理新增的类型
          for (const type of newSet) {
            if (!oldSet.has(type)) {
              await updateListings(type)
            }
          }
          
          // 处理移除的类型
          for (const type of oldSet) {
            if (!newSet.has(type)) {
              clearListings(type)
            }
          }
        }
      },
      { deep: true }
    )

    // 创建防抖的网格更新函数
    const debouncedUpdateHexGrid = debounce(async () => {
      if (!props.selectedLocation?.city || !props.currentTime || props.selectedHostTypes.length === 0) {
        if (map.getLayer('hexgrid-layer')) {
          map.setLayoutProperty('hexgrid-layer', 'visibility', 'none')
        }
        return
      }
      
      try {
        const date = new Date(Number(props.currentTime))
        const timeStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
        
        const response = await api.get(
          `/city/${props.selectedLocation.city}/hexgrid`,
          {
            params: {
              time_point: timeStr,
              categories: props.selectedHostTypes.join(',')
            }
          }
        )
        
        if (!map.getSource('hexgrid')) {
          map.addSource('hexgrid', {
            type: 'geojson',
            data: {
              type: 'FeatureCollection',
              features: []
            }
          })
          
          map.addLayer({
            id: 'hexgrid-layer',
            type: 'fill',
            source: 'hexgrid',
            paint: {
              'fill-color': [
                'interpolate',
                ['linear'],
                ['get', 'points_count'],
                0, 'rgba(0, 0, 0, 0)',    // 完全透明
                1, '#FBD0A9',             // 非常浅的橙色
                5, '#FB8861',             // 浅橙色
                15, '#E75263',            // 红色
                30, '#B53679',            // 紫红色
                50, '#6C1F81',            // 深紫色
                100, '#2B115E'            // 非常深的紫色
              ],
              'fill-opacity': 0.70        // 稍微提高了不透明度
            }
          })
        }
        
        const features = response.data.hexagons.map(hex => ({
          type: 'Feature',
          properties: {
            id: hex.id,
            points_count: hex.points_count
          },
          geometry: {
            type: 'Polygon',
            coordinates: [
              hex.boundary.map(coord => [coord[1], coord[0]])
            ]
          }
        }))
        
        if (map.getLayer('hexgrid-layer')) {
          map.setLayoutProperty('hexgrid-layer', 'visibility', 'visible')
        }
        
        map.getSource('hexgrid').setData({
          type: 'FeatureCollection',
          features: features
        })
        
      } catch (error) {
        console.error('Failed to fetch hexgrid:', error)
      }
    }, 1000)  // 使用与滑动条相同的延迟时间

    // 修改原有的 updateHexGrid 函数
    const updateHexGrid = () => {
      debouncedUpdateHexGrid()
    }

    // 监听视图模式变化
    watch(() => props.isHexMode, (newMode) => {
      if (!map) return
      
      if (newMode) {
        // 隐藏散点图层
        Object.keys(layerColors).forEach(type => {
          if (map.getLayer(`listings-layer-${type}`)) {
            map.setLayoutProperty(`listings-layer-${type}`, 'visibility', 'none')
          }
        })
        // 立即更新网格
        updateHexGrid()
      } else {
        // 显示散点图层
        Object.keys(layerColors).forEach(type => {
          if (map.getLayer(`listings-layer-${type}`)) {
            map.setLayoutProperty(`listings-layer-${type}`, 'visibility', 'visible')
          }
        })
        // 隐藏网格图层
        if (map.getLayer('hexgrid-layer')) {
          map.setLayoutProperty('hexgrid-layer', 'visibility', 'none')
        }
      }
    })

    // 使用防抖和批处理
    const updateCity = debounce(async (cityName) => {
      if (!cityName) return
      
      try {
        const [basicData, listingsData] = await Promise.all([
          api.get(`/city/${cityName}`),
          api.get(`/city/${cityName}/listings_by_categories`)
        ])
        
        // 批量处理数据更新
        requestAnimationFrame(() => {
          updateMapData(basicData.data)
          updateListings(listingsData.data)
        })
        
      } catch (error) {
        console.error('Failed to update city:', error)
      }
    }, 300)

    onUnmounted(() => {
      if (map) {
        if (popup) popup.remove()
        map.remove()
      }
      debouncedUpdateHexGrid.cancel()
    })

    return {}
  }
}
</script>

<style>
.map-wrapper {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  overflow: hidden;
}

.map-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

/* 使用 CSS 变量控制地图容器的宽度和位置 */
.map-wrapper {
  padding-left: var(--sidebar-width);
  transition: padding-left 0.3s ease;
}

.map-wrapper:has(+ .sidebar-container.collapsed) {
  padding-left: 0;
}

.popup-content {
  padding: 8px;
  font-size: 12px;
  line-height: 1.4;
}

.mapboxgl-popup {
  z-index: 1;
}

.mapboxgl-popup-content {
  padding: 10px;
  border-radius: 4px;
  background-color: rgba(255, 255, 255, 0.95);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style> 
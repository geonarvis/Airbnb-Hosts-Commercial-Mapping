import { createApp } from 'vue'
import App from './App.vue'
import store from './store/index.js'
import router from './router/index.js'
import './index.css'
import VueApexCharts from 'vue3-apexcharts'

const app = createApp(App)
app.use(store)
app.use(router)
app.use(VueApexCharts)
app.mount('#app')

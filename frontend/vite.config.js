import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: '/airbnb-hosts-visualization/',  // 添加这行，指定基础路径
  plugins: [vue()],
  server: {
    hmr: {
      overlay: true
    }
  }
})
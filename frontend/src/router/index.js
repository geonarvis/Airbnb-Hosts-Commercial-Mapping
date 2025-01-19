import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/about',
    name: 'About',
    component: () => import('../components/About.vue')
  }
]

const router = createRouter({
  history: createWebHistory('/airbnb-hosts-visualization/'),  // 修改这里
  routes
})

export default router
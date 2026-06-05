import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Research',
    component: () => import('@/views/ResearchView.vue')
  }
]

export default createRouter({
  history: createWebHistory(),
  routes
})

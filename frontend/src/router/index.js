import { createRouter, createWebHistory } from 'vue-router'
import SalesTwin from '../views/SalesTwin.vue'

const routes = [
  {
    path: '/',
    redirect: '/sales-twin'
  },
  {
    path: '/sales-twin',
    name: 'SalesTwin',
    component: SalesTwin
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '市场看板' } },
  { path: '/screener', component: () => import('@/views/ScreenerView.vue'), meta: { title: '选股' } },
  { path: '/kline/:code?', component: () => import('@/views/KlineView.vue'), meta: { title: 'K线分析' } },
  { path: '/ai', component: () => import('@/views/AIView.vue'), meta: { title: 'AI信号' } },
  { path: '/portfolio', component: () => import('@/views/PortfolioView.vue'), meta: { title: '持仓管理' } },
  { path: '/backtest', component: () => import('@/views/BacktestView.vue'), meta: { title: '回测' } },
  { path: '/settings', component: () => import('@/views/SettingsView.vue'), meta: { title: '设置' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.afterEach((to) => {
  document.title = `${to.meta.title || ''} - Stock AI Analyzer`
})

export default router

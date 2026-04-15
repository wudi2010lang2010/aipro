<template>
  <el-container class="app-container">
    <!-- 左侧导航 -->
    <el-aside width="180px" class="aside">
      <div class="logo">
        <span class="logo-icon">📈</span>
        <span class="logo-text">Stock AI</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#1a1a2e"
        text-color="#a0a8c0"
        active-text-color="#4fc3f7"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
      <!-- 底部状态 -->
      <div class="status-bar">
        <el-tag :type="wsConnected ? 'success' : 'danger'" size="small" round>
          {{ wsConnected ? '实时' : '离线' }}
        </el-tag>
        <span class="status-time">{{ lastUpdate }}</span>
      </div>
    </el-aside>

    <!-- 右侧内容 -->
    <el-main class="main-content">
      <router-view v-slot="{ Component }">
        <keep-alive :include="['DashboardView']">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMarketStore } from '@/stores/market'
import { useWebSocket } from '@/composables/useWebSocket'

const route = useRoute()
const marketStore = useMarketStore()

const menuItems = [
  { path: '/dashboard', label: '市场看板', icon: 'DataLine' },
  { path: '/screener',  label: '选股',     icon: 'Search' },
  { path: '/kline',     label: 'K线分析',  icon: 'TrendCharts' },
  { path: '/ai',        label: 'AI信号',   icon: 'MagicStick' },
  { path: '/portfolio', label: '持仓管理', icon: 'Wallet' },
  { path: '/backtest',  label: '回测',     icon: 'Timer' },
  { path: '/settings',  label: '设置',     icon: 'Setting' },
]

const activeMenu = computed(() => '/' + route.path.split('/')[1])
const lastUpdate = computed(() => marketStore.lastUpdate)

const { connected: wsConnected, connect } = useWebSocket((msg) => {
  if (msg.type === 'quote') marketStore.updateFromWs(msg.data)
})

onMounted(() => {
  connect()
  marketStore.fetchAll()
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0f0f1a; color: #e0e6f0; font-family: 'Segoe UI', sans-serif; }

.app-container { height: 100vh; overflow: hidden; }

.aside {
  background: #1a1a2e;
  border-right: 1px solid #2a2a4a;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  border-bottom: 1px solid #2a2a4a;
  flex-shrink: 0;
}
.logo-icon { font-size: 24px; }
.logo-text { font-size: 16px; font-weight: 700; color: #4fc3f7; }

.el-menu {
  border: none !important;
  flex: 1;
  overflow-y: auto;
}
.el-menu-item {
  border-radius: 8px;
  margin: 2px 8px;
}
.el-menu-item.is-active {
  background: rgba(79, 195, 247, 0.15) !important;
}

.status-bar {
  padding: 12px 16px;
  border-top: 1px solid #2a2a4a;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.status-time { font-size: 11px; color: #606880; }

.main-content {
  background: #0f0f1a;
  overflow-y: auto;
  padding: 20px;
}

/* Element Plus 深色主题覆盖 */
.el-menu--vertical { background-color: #1a1a2e !important; }
.el-menu-item:hover { background-color: rgba(79, 195, 247, 0.08) !important; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #1a1a2e; }
::-webkit-scrollbar-thumb { background: #3a3a5a; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #4a4a6a; }
</style>

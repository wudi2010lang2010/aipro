<template>
  <div class="dashboard">
    <!-- 页面标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">市场看板</h2>
        <el-tag :type="marketStore.isOpen ? 'success' : 'info'" size="small" round>
          {{ marketStore.marketStatus.desc || (marketStore.isOpen ? '交易中' : '已收盘') }}
        </el-tag>
      </div>
      <div class="header-right">
        <span class="update-time" v-if="marketStore.lastUpdate">
          <el-icon><RefreshRight /></el-icon>
          更新于 {{ marketStore.lastUpdate }}
        </span>
        <el-button size="small" :loading="loading" @click="refresh" circle>
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 四大指数卡片 -->
    <div class="indices-grid">
      <div
        v-for="idx in marketStore.indices"
        :key="idx.ts_code"
        class="index-card"
        :class="getChangeClass(idx.pct_chg)"
      >
        <div class="index-name">{{ idx.name }}</div>
        <div class="index-price">{{ formatPrice(idx.close) }}</div>
        <div class="index-change">
          <span class="change-val" :style="changeStyle(idx.change)">
            {{ formatChange(idx.change) }}
          </span>
          <span class="change-pct" :style="changeStyle(idx.pct_chg)">
            {{ formatPct(idx.pct_chg) }}
          </span>
        </div>
        <div class="index-meta">
          <span>量比 {{ idx.vol_ratio ?? '--' }}</span>
          <span>{{ formatVol(idx.vol) }}</span>
        </div>
        <!-- 涨跌色指示条 -->
        <div class="index-bar" :style="indexBarStyle(idx.pct_chg)"></div>
      </div>

      <!-- 骨架屏（无数据时） -->
      <template v-if="!marketStore.indices.length">
        <el-skeleton
          v-for="i in 4"
          :key="i"
          class="index-card skeleton-card"
          animated
        >
          <template #template>
            <el-skeleton-item variant="text" style="width: 60%; margin-bottom: 8px" />
            <el-skeleton-item variant="text" style="width: 80%; height: 28px; margin-bottom: 8px" />
            <el-skeleton-item variant="text" style="width: 50%" />
          </template>
        </el-skeleton>
      </template>
    </div>

    <!-- 主内容区：涨幅榜 + 板块排名 -->
    <div class="main-grid">
      <!-- 涨幅榜 -->
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">
            <el-icon color="#f56565"><TrendCharts /></el-icon>
            涨幅榜 Top{{ marketStore.topGainers.length || 20 }}
          </span>
          <el-radio-group v-model="gainersFilter" size="small" @change="onFilterChange">
            <el-radio-button label="all" value="all">全部</el-radio-button>
            <el-radio-button label="up" value="up">涨幅</el-radio-button>
            <el-radio-button label="down" value="down">跌幅</el-radio-button>
          </el-radio-group>
        </div>

        <el-table
          :data="filteredGainers"
          size="small"
          height="480"
          stripe
          class="gainer-table"
          :row-class-name="rowClassName"
          @row-click="onRowClick"
        >
          <el-table-column type="index" width="36" label="#" align="center" />
          <el-table-column prop="name" label="名称" min-width="80">
            <template #default="{ row }">
              <div class="stock-name">
                <span>{{ row.name }}</span>
                <span class="stock-code">{{ formatCode(row.ts_code) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="现价" min-width="72" align="right">
            <template #default="{ row }">
              <span class="mono" :style="changeStyle(row.pct_chg)">
                {{ formatPrice(row.close ?? row.price) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="涨跌幅" width="82" align="right">
            <template #default="{ row }">
              <span class="pct-badge mono" :class="getChangeClass(row.pct_chg)">
                {{ formatPct(row.pct_chg) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="成交额" min-width="72" align="right">
            <template #default="{ row }">
              <span class="mono amount-text">
                {{ formatAmount(row.amount) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 板块排名 -->
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">
            <el-icon color="#48bb78"><Grid /></el-icon>
            板块排名
          </span>
          <el-select v-model="sectorSort" size="small" style="width: 100px" @change="onSectorSortChange">
            <el-option label="涨幅排序" value="desc" />
            <el-option label="跌幅排序" value="asc" />
          </el-select>
        </div>

        <div class="sector-list" v-if="sortedSectors.length">
          <div
            v-for="(sec, idx) in sortedSectors"
            :key="sec.name || idx"
            class="sector-item"
          >
            <div class="sector-row">
              <div class="sector-left">
                <span class="sector-rank">{{ idx + 1 }}</span>
                <span class="sector-name">{{ sec.name }}</span>
              </div>
              <div class="sector-right">
                <span class="sector-pct mono" :style="changeStyle(sec.pct_chg)">
                  {{ formatPct(sec.pct_chg) }}
                </span>
                <span class="sector-leader" v-if="sec.leader_name">
                  {{ sec.leader_name }}
                </span>
              </div>
            </div>
            <el-progress
              :percentage="progressPct(sec.pct_chg)"
              :color="progressColor(sec.pct_chg)"
              :stroke-width="4"
              :show-text="false"
              class="sector-progress"
            />
          </div>
        </div>

        <!-- 骨架屏 -->
        <div v-else class="sector-list">
          <el-skeleton
            v-for="i in 10"
            :key="i"
            animated
            style="margin-bottom: 14px"
          >
            <template #template>
              <div style="display: flex; justify-content: space-between; margin-bottom: 4px">
                <el-skeleton-item variant="text" style="width: 40%" />
                <el-skeleton-item variant="text" style="width: 15%" />
              </div>
              <el-skeleton-item variant="text" style="width: 100%; height: 4px" />
            </template>
          </el-skeleton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMarketStore } from '@/stores/market'

const marketStore = useMarketStore()
const router = useRouter()

const loading = ref(false)
const gainersFilter = ref('all')
const sectorSort = ref('desc')

// ────────────────────────────────────────────────
// 计算属性
// ────────────────────────────────────────────────
const filteredGainers = computed(() => {
  const list = marketStore.topGainers
  if (gainersFilter.value === 'up')   return list.filter(s => (s.pct_chg ?? 0) > 0)
  if (gainersFilter.value === 'down') return list.filter(s => (s.pct_chg ?? 0) < 0)
  return list
})

const sortedSectors = computed(() => {
  const list = [...(marketStore.sectors || [])]
  return list.sort((a, b) =>
    sectorSort.value === 'desc'
      ? (b.pct_chg ?? 0) - (a.pct_chg ?? 0)
      : (a.pct_chg ?? 0) - (b.pct_chg ?? 0)
  )
})

// ────────────────────────────────────────────────
// 格式化工具
// ────────────────────────────────────────────────
function formatPrice(val) {
  if (val == null || val === '') return '--'
  return Number(val).toFixed(2)
}

function formatChange(val) {
  if (val == null || val === '') return '--'
  const n = Number(val)
  return (n >= 0 ? '+' : '') + n.toFixed(2)
}

function formatPct(val) {
  if (val == null || val === '') return '--'
  const n = Number(val)
  return (n >= 0 ? '+' : '') + n.toFixed(2) + '%'
}

function formatAmount(val) {
  if (val == null || val === '') return '--'
  const n = Number(val)
  if (n >= 1e8) return (n / 1e8).toFixed(1) + '亿'
  if (n >= 1e4) return (n / 1e4).toFixed(1) + '万'
  return n.toFixed(0)
}

function formatVol(val) {
  if (val == null || val === '') return '--'
  const n = Number(val)
  if (n >= 1e8) return (n / 1e8).toFixed(1) + '亿手'
  if (n >= 1e4) return (n / 1e4).toFixed(0) + '万手'
  return n + '手'
}

function formatCode(ts_code) {
  if (!ts_code) return ''
  return ts_code.split('.')[0]
}

// ────────────────────────────────────────────────
// 样式计算
// ────────────────────────────────────────────────
function changeStyle(val) {
  if (val == null || val === '') return { color: '#a0a8c0' }
  return { color: Number(val) >= 0 ? '#f56565' : '#48bb78' }
}

function getChangeClass(val) {
  if (val == null) return ''
  return Number(val) >= 0 ? 'is-up' : 'is-down'
}

function indexBarStyle(pct) {
  const n = Number(pct) || 0
  const color = n >= 0 ? '#f56565' : '#48bb78'
  const width = Math.min(Math.abs(n) * 10, 100) + '%'
  return { background: color, width }
}

function progressPct(pct) {
  const n = Number(pct) || 0
  return Math.min(Math.abs(n) * 10, 100)
}

function progressColor(pct) {
  return Number(pct) >= 0 ? '#f56565' : '#48bb78'
}

function rowClassName({ row }) {
  if ((row.pct_chg ?? 0) > 5) return 'row-highlight-up'
  if ((row.pct_chg ?? 0) < -5) return 'row-highlight-down'
  return ''
}

// ────────────────────────────────────────────────
// 交互
// ────────────────────────────────────────────────
async function refresh() {
  loading.value = true
  await marketStore.fetchAll()
  loading.value = false
}

function onFilterChange() {}
function onSectorSortChange() {}

function onRowClick(row) {
  if (row.ts_code) {
    router.push(`/kline/${row.ts_code}`)
  }
}

// ────────────────────────────────────────────────
// 自动刷新（收盘后不刷新）
// ────────────────────────────────────────────────
let autoRefreshTimer = null

onMounted(() => {
  if (!marketStore.indices.length) {
    marketStore.fetchAll()
  }
  // 每 30 秒刷新一次
  autoRefreshTimer = setInterval(() => {
    if (marketStore.isOpen) marketStore.fetchAll()
  }, 30000)
})

onUnmounted(() => {
  clearInterval(autoRefreshTimer)
})
</script>

<style scoped>
/* ── 页面布局 ── */
.dashboard {
  min-height: 100%;
  color: #e0e6f0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-right { display: flex; align-items: center; gap: 10px; }

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #e0e6f0;
}

.update-time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #606880;
}

/* ── 指数卡片 ── */
.indices-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.index-card {
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 12px;
  padding: 16px;
  position: relative;
  overflow: hidden;
  cursor: default;
  transition: border-color 0.2s, transform 0.15s;
}
.index-card:hover {
  transform: translateY(-2px);
  border-color: #3a3a5a;
}
.index-card.is-up  { border-top: 2px solid #f56565; }
.index-card.is-down { border-top: 2px solid #48bb78; }

.index-name {
  font-size: 13px;
  color: #a0a8c0;
  margin-bottom: 6px;
}

.index-price {
  font-size: 24px;
  font-weight: 700;
  font-family: 'Consolas', 'Courier New', monospace;
  color: #e0e6f0;
  margin-bottom: 6px;
}

.index-change {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}
.change-val, .change-pct {
  font-size: 13px;
  font-family: 'Consolas', 'Courier New', monospace;
  font-weight: 600;
}

.index-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #606880;
}

.index-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  opacity: 0.6;
  transition: width 0.6s ease;
}

.skeleton-card {
  min-height: 110px;
  padding: 16px;
}

/* ── 主内容网格 ── */
.main-grid {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 14px;
}

/* ── 面板通用 ── */
.panel {
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 12px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #2a2a4a;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #c0c8e0;
}

/* ── 涨幅榜表格 ── */
.gainer-table {
  background: transparent !important;
}

/* Element Plus table 深色覆盖 */
:deep(.el-table) {
  background: transparent !important;
  color: #c0c8e0;
}
:deep(.el-table tr) { background: transparent !important; }
:deep(.el-table th.el-table__cell) {
  background: #1e1e38 !important;
  color: #606880;
  font-size: 12px;
  border-bottom: 1px solid #2a2a4a;
}
:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid #1e1e32;
}
:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: rgba(255,255,255,0.02) !important;
}
:deep(.el-table__body tr:hover > td.el-table__cell) {
  background: rgba(79, 195, 247, 0.06) !important;
  cursor: pointer;
}
:deep(.row-highlight-up td) { background: rgba(245, 101, 101, 0.06) !important; }
:deep(.row-highlight-down td) { background: rgba(72, 187, 120, 0.06) !important; }
:deep(.el-table__inner-wrapper::before) { display: none; }

.stock-name {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.stock-name > span:first-child {
  font-size: 13px;
  color: #e0e6f0;
}
.stock-code {
  font-size: 11px;
  color: #606880;
  font-family: 'Consolas', monospace;
}

.mono {
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 13px;
}

.pct-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.pct-badge.is-up {
  background: rgba(245, 101, 101, 0.12);
  color: #f56565;
}
.pct-badge.is-down {
  background: rgba(72, 187, 120, 0.12);
  color: #48bb78;
}

.amount-text { color: #a0a8c0; font-size: 12px; }

/* ── 板块排名 ── */
.sector-list {
  padding: 12px 16px;
  height: 480px;
  overflow-y: auto;
}

.sector-item {
  margin-bottom: 12px;
}

.sector-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.sector-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.sector-rank {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: #2a2a4a;
  color: #606880;
  font-size: 11px;
  font-family: 'Consolas', monospace;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.sector-item:nth-child(1) .sector-rank { background: rgba(245,101,101,0.25); color: #f56565; }
.sector-item:nth-child(2) .sector-rank { background: rgba(245,101,101,0.18); color: #f88080; }
.sector-item:nth-child(3) .sector-rank { background: rgba(245,101,101,0.12); color: #f09090; }

.sector-name {
  font-size: 13px;
  color: #c0c8e0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sector-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.sector-pct {
  font-size: 13px;
  font-weight: 600;
  min-width: 58px;
  text-align: right;
}

.sector-leader {
  font-size: 11px;
  color: #606880;
  max-width: 56px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sector-progress {
  margin-top: 2px;
}
:deep(.el-progress-bar__outer) {
  background: #2a2a4a !important;
}

/* ── 滚动条 ── */
.sector-list::-webkit-scrollbar { width: 4px; }
.sector-list::-webkit-scrollbar-track { background: transparent; }
.sector-list::-webkit-scrollbar-thumb { background: #2a2a4a; border-radius: 2px; }

/* ── Element Plus 组件覆盖 ── */
:deep(.el-radio-button__inner) {
  background: #2a2a4a !important;
  border-color: #3a3a5a !important;
  color: #a0a8c0 !important;
  font-size: 12px;
}
:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #4fc3f7 !important;
  border-color: #4fc3f7 !important;
  color: #0f0f1a !important;
}
:deep(.el-select .el-input__wrapper) {
  background: #2a2a4a !important;
  box-shadow: none !important;
  border: 1px solid #3a3a5a !important;
}
:deep(.el-select .el-input__inner) { color: #a0a8c0 !important; }

/* ── 响应式 ── */
@media (max-width: 1200px) {
  .indices-grid { grid-template-columns: repeat(2, 1fr); }
  .main-grid { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .indices-grid { grid-template-columns: 1fr 1fr; }
}
</style>

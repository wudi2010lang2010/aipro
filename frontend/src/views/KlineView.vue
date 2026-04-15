<template>
  <div class="kline-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title">K线分析</h2>
    </div>

    <!-- 搜索栏 + 周期选择 -->
    <div class="toolbar">
      <div class="search-area">
        <el-autocomplete
          v-model="searchQuery"
          :fetch-suggestions="fetchSuggestions"
          placeholder="输入股票名称或代码搜索..."
          :loading="searching"
          clearable
          style="width: 280px"
          popper-class="stock-search-popper"
          @select="onStockSelect"
          @clear="onClear"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
          <template #default="{ item }">
            <div class="suggestion-item">
              <span class="sug-name">{{ item.name }}</span>
              <span class="sug-code">{{ formatCode(item.ts_code) }}</span>
              <el-tag size="small" class="sug-market" :type="marketType(item.ts_code)">
                {{ marketLabel(item.ts_code) }}
              </el-tag>
            </div>
          </template>
        </el-autocomplete>

        <span class="search-hint" v-if="!selectedStock">
          <el-icon><InfoFilled /></el-icon>
          支持拼音首字母、股票代码、中文名称搜索
        </span>
      </div>

      <div class="period-area" v-if="selectedStock">
        <span class="period-label">周期：</span>
        <el-radio-group v-model="period" size="small" @change="onPeriodChange">
          <el-radio-button label="日线" value="daily" />
          <el-radio-button label="60分" value="60min" />
          <el-radio-button label="30分" value="30min" />
          <el-radio-button label="15分" value="15min" />
        </el-radio-group>
        <el-button
          size="small"
          :loading="loadingKline"
          @click="loadKlineData"
          circle
          style="margin-left: 8px"
        >
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 股票基本信息卡片 -->
    <transition name="fade-slide">
      <div class="stock-info-card" v-if="selectedStock">
        <div class="info-main">
          <div class="info-name-block">
            <span class="info-name">{{ selectedStock.name }}</span>
            <span class="info-code">{{ formatCode(selectedStock.ts_code) }}</span>
            <el-tag size="small" :type="marketType(selectedStock.ts_code)" style="margin-left: 6px">
              {{ marketLabel(selectedStock.ts_code) }}
            </el-tag>
          </div>
          <div class="info-price-block">
            <span class="info-price" :style="changeStyle(quoteData.pct_chg)">
              {{ formatPrice(quoteData.close) }}
            </span>
            <div class="info-changes">
              <span class="info-change" :style="changeStyle(quoteData.pct_chg)">
                {{ formatChange(quoteData.change) }}
              </span>
              <span class="info-pct-badge" :class="getChangeClass(quoteData.pct_chg)">
                {{ formatPct(quoteData.pct_chg) }}
              </span>
            </div>
          </div>
        </div>

        <div class="info-stats">
          <div class="stat-item">
            <span class="stat-label">今开</span>
            <span class="stat-val">{{ formatPrice(quoteData.open) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">昨收</span>
            <span class="stat-val">{{ formatPrice(quoteData.pre_close) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">最高</span>
            <span class="stat-val" style="color: #f56565">{{ formatPrice(quoteData.high) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">最低</span>
            <span class="stat-val" style="color: #48bb78">{{ formatPrice(quoteData.low) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">成交量</span>
            <span class="stat-val">{{ formatVol(quoteData.vol) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">成交额</span>
            <span class="stat-val">{{ formatAmount(quoteData.amount) }}</span>
          </div>
          <div class="stat-item" v-if="quoteData.turnover_rate != null">
            <span class="stat-label">换手率</span>
            <span class="stat-val">{{ formatPctRaw(quoteData.turnover_rate) }}</span>
          </div>
          <div class="stat-item" v-if="quoteData.pe != null">
            <span class="stat-label">市盈率</span>
            <span class="stat-val">{{ formatDecimal(quoteData.pe) }}</span>
          </div>
        </div>
      </div>
    </transition>

    <!-- 图表占位提示 -->
    <transition name="fade-slide">
      <div class="chart-placeholder" v-if="selectedStock">
        <div class="placeholder-inner">
          <div class="placeholder-icon">📊</div>
          <div class="placeholder-text">K线图组件开发中，请先使用市场看板</div>
          <div class="placeholder-sub">
            即将支持：蜡烛图 · MA均线 · MACD · KDJ · 成交量 · 布林带
          </div>
          <el-button type="primary" plain size="small" @click="goToDashboard">
            <el-icon><DataLine /></el-icon>
            前往市场看板
          </el-button>
        </div>
      </div>
    </transition>

    <!-- 最近 5 根 K线 OHLC 数据表格 -->
    <transition name="fade-slide">
      <div class="ohlc-panel" v-if="selectedStock && recentKlines.length">
        <div class="panel-header">
          <span class="panel-title">
            <el-icon color="#4fc3f7"><List /></el-icon>
            最近 {{ recentKlines.length }} 根 K线（{{ periodLabel }}）
          </span>
          <el-tag size="small" type="info">OHLC 数据</el-tag>
        </div>

        <el-table
          :data="recentKlines"
          size="small"
          stripe
          class="ohlc-table"
        >
          <el-table-column prop="trade_date" label="日期" min-width="100" align="center">
            <template #default="{ row }">
              <span class="mono date-text">{{ formatDate(row.trade_date) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="开盘" min-width="80" align="right">
            <template #default="{ row }">
              <span class="mono">{{ formatPrice(row.open) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="最高" min-width="80" align="right">
            <template #default="{ row }">
              <span class="mono" style="color: #f56565">{{ formatPrice(row.high) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="最低" min-width="80" align="right">
            <template #default="{ row }">
              <span class="mono" style="color: #48bb78">{{ formatPrice(row.low) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="收盘" min-width="80" align="right">
            <template #default="{ row }">
              <span class="mono" :style="changeStyle(row.pct_chg)">
                {{ formatPrice(row.close) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="涨跌幅" min-width="90" align="right">
            <template #default="{ row }">
              <span class="pct-badge mono" :class="getChangeClass(row.pct_chg)">
                {{ formatPct(row.pct_chg) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="成交量" min-width="90" align="right">
            <template #default="{ row }">
              <span class="mono amount-text">{{ formatVol(row.vol) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="MA5" min-width="80" align="right">
            <template #default="{ row }">
              <span class="mono indicator-ma5">{{ formatPrice(row.ma5) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="MA10" min-width="80" align="right">
            <template #default="{ row }">
              <span class="mono indicator-ma10">{{ formatPrice(row.ma10) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="形态" min-width="90" align="center">
            <template #default="{ row }">
              <span class="candle-shape" :class="getCandleClass(row)">
                {{ getCandleLabel(row) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </transition>

    <!-- 未选股票时的引导页 -->
    <div class="empty-guide" v-if="!selectedStock">
      <div class="guide-icon">🔍</div>
      <div class="guide-title">搜索股票开始分析</div>
      <div class="guide-desc">输入股票名称、代码或拼音首字母进行搜索</div>
      <div class="guide-examples">
        <span class="guide-label">热门示例：</span>
        <el-tag
          v-for="ex in examples"
          :key="ex.code"
          class="example-tag"
          size="small"
          type="info"
          @click="quickSelect(ex)"
        >
          {{ ex.name }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { searchStock, getKline } from '@/api/kline'

const route = useRoute()
const router = useRouter()

// ────────────────────────────────────────────────
// 状态
// ────────────────────────────────────────────────
const searchQuery = ref('')
const searching = ref(false)
const loadingKline = ref(false)
const period = ref('daily')
const selectedStock = ref(null)
const klineData = ref([])

const quoteData = ref({
  open: null,
  close: null,
  high: null,
  low: null,
  pre_close: null,
  change: null,
  pct_chg: null,
  vol: null,
  amount: null,
  turnover_rate: null,
  pe: null,
})

const examples = [
  { name: '贵州茅台', ts_code: '600519.SH' },
  { name: '宁德时代', ts_code: '300750.SZ' },
  { name: '比亚迪',   ts_code: '002594.SZ' },
  { name: '中国平安', ts_code: '601318.SH' },
  { name: '招商银行', ts_code: '600036.SH' },
]

// ────────────────────────────────────────────────
// 计算属性
// ────────────────────────────────────────────────
const recentKlines = computed(() => {
  return klineData.value.slice(0, 5)
})

const periodLabel = computed(() => {
  const map = { daily: '日线', '60min': '60分钟', '30min': '30分钟', '15min': '15分钟' }
  return map[period.value] || period.value
})

// ────────────────────────────────────────────────
// 搜索逻辑
// ────────────────────────────────────────────────
async function fetchSuggestions(queryStr, cb) {
  const q = queryStr.trim()
  if (!q) { cb([]); return }
  searching.value = true
  try {
    const res = await searchStock(q)
    const list = (res.code === 0 ? res.data : []) || []
    cb(list.map(item => ({ ...item, value: item.name })))
  } catch {
    cb([])
  } finally {
    searching.value = false
  }
}

function onStockSelect(item) {
  selectedStock.value = item
  searchQuery.value = item.name
  loadKlineData()
}

function onClear() {
  selectedStock.value = null
  klineData.value = []
  resetQuote()
}

function quickSelect(ex) {
  selectedStock.value = ex
  searchQuery.value = ex.name
  loadKlineData()
}

// ────────────────────────────────────────────────
// K 线数据加载
// ────────────────────────────────────────────────
async function loadKlineData() {
  if (!selectedStock.value) return
  loadingKline.value = true
  try {
    const res = await getKline(selectedStock.value.ts_code, period.value, 100)
    if (res.code === 0 && res.data) {
      const bars = res.data.bars || res.data || []
      klineData.value = bars
      // 用最新一根更新行情
      if (bars.length > 0) {
        const latest = bars[0]
        quoteData.value = {
          open:          latest.open,
          close:         latest.close,
          high:          latest.high,
          low:           latest.low,
          pre_close:     latest.pre_close,
          change:        latest.change,
          pct_chg:       latest.pct_chg,
          vol:           latest.vol,
          amount:        latest.amount,
          turnover_rate: latest.turnover_rate,
          pe:            latest.pe ?? null,
        }
      }
    }
  } catch (e) {
    console.error('加载K线失败:', e)
  } finally {
    loadingKline.value = false
  }
}

function onPeriodChange() {
  loadKlineData()
}

function resetQuote() {
  quoteData.value = {
    open: null, close: null, high: null, low: null,
    pre_close: null, change: null, pct_chg: null,
    vol: null, amount: null, turnover_rate: null, pe: null,
  }
}

// ────────────────────────────────────────────────
// 路由参数处理（从 /kline/:code 进入）
// ────────────────────────────────────────────────
onMounted(async () => {
  const code = route.params.code
  if (code) {
    // 先用代码直接加载 K 线，name 待搜索
    selectedStock.value = { ts_code: code, name: code.split('.')[0] }
    searchQuery.value = code
    await loadKlineData()
    // 补全名称
    try {
      const res = await searchStock(code.split('.')[0])
      if (res.code === 0 && res.data?.length) {
        const found = res.data.find(s => s.ts_code === code)
        if (found) {
          selectedStock.value = found
          searchQuery.value = found.name
        }
      }
    } catch {}
  }
})

// ────────────────────────────────────────────────
// 导航
// ────────────────────────────────────────────────
function goToDashboard() {
  router.push('/dashboard')
}

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

function formatPctRaw(val) {
  if (val == null || val === '') return '--'
  return Number(val).toFixed(2) + '%'
}

function formatDecimal(val) {
  if (val == null || val === '') return '--'
  return Number(val).toFixed(2)
}

function formatVol(val) {
  if (val == null || val === '') return '--'
  const n = Number(val)
  if (n >= 1e8) return (n / 1e8).toFixed(2) + '亿手'
  if (n >= 1e4) return (n / 1e4).toFixed(0) + '万手'
  return n + '手'
}

function formatAmount(val) {
  if (val == null || val === '') return '--'
  const n = Number(val)
  if (n >= 1e8) return (n / 1e8).toFixed(2) + '亿'
  if (n >= 1e4) return (n / 1e4).toFixed(1) + '万'
  return n.toFixed(0)
}

function formatCode(ts_code) {
  if (!ts_code) return ''
  return ts_code.split('.')[0]
}

function formatDate(val) {
  if (!val) return '--'
  const s = String(val)
  if (s.length === 8) return `${s.slice(0,4)}-${s.slice(4,6)}-${s.slice(6,8)}`
  return s
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

function marketType(ts_code) {
  if (!ts_code) return 'info'
  if (ts_code.endsWith('.SH')) return 'danger'
  if (ts_code.endsWith('.SZ')) return 'success'
  if (ts_code.endsWith('.BJ')) return 'warning'
  return 'info'
}

function marketLabel(ts_code) {
  if (!ts_code) return '--'
  if (ts_code.endsWith('.SH')) return '沪'
  if (ts_code.endsWith('.SZ')) return '深'
  if (ts_code.endsWith('.BJ')) return '北'
  return ts_code.split('.')[1] || '--'
}

// ────────────────────────────────────────────────
// K线形态判断
// ────────────────────────────────────────────────
function getCandleClass(row) {
  const o = Number(row.open), c = Number(row.close)
  const body = Math.abs(c - o)
  const range = Number(row.high) - Number(row.low)
  if (range === 0) return 'candle-doji'
  const ratio = body / range
  if (ratio < 0.1) return 'candle-doji'
  return c >= o ? 'candle-bull' : 'candle-bear'
}

function getCandleLabel(row) {
  const o = Number(row.open), c = Number(row.close)
  const h = Number(row.high), l = Number(row.low)
  const body = Math.abs(c - o)
  const range = h - l
  if (range === 0) return '十字星'
  const ratio = body / range
  if (ratio < 0.1) return '十字星'
  const upperShadow = h - Math.max(o, c)
  const lowerShadow = Math.min(o, c) - l
  if (c >= o) {
    if (lowerShadow > body * 2 && upperShadow < body * 0.3) return '锤子线'
    if (upperShadow > body * 2 && lowerShadow < body * 0.3) return '射击之星'
    return '阳线'
  } else {
    if (lowerShadow > body * 2 && upperShadow < body * 0.3) return '倒锤子'
    if (upperShadow > body * 2 && lowerShadow < body * 0.3) return '上吊线'
    return '阴线'
  }
}
</script>

<style scoped>
/* ── 页面布局 ── */
.kline-view {
  min-height: 100%;
  color: #e0e6f0;
}

.page-header {
  margin-bottom: 20px;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #e0e6f0;
}

/* ── 工具栏 ── */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.search-area {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.search-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #606880;
}

.period-area {
  display: flex;
  align-items: center;
  gap: 8px;
}
.period-label {
  font-size: 13px;
  color: #a0a8c0;
}

/* ── 搜索弹出建议 ── */
:deep(.stock-search-popper .el-autocomplete-suggestion__wrap) {
  background: #1e1e38;
  border: 1px solid #3a3a5a;
  border-radius: 8px;
}
:deep(.stock-search-popper li) {
  color: #c0c8e0;
  padding: 0;
}
:deep(.stock-search-popper li:hover) {
  background: rgba(79, 195, 247, 0.1);
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
}
.sug-name {
  font-size: 13px;
  color: #e0e6f0;
  min-width: 70px;
}
.sug-code {
  font-size: 12px;
  color: #606880;
  font-family: 'Consolas', monospace;
  flex: 1;
}

/* ── Element Plus 输入框深色适配 ── */
:deep(.el-autocomplete .el-input__wrapper) {
  background: #1a1a2e !important;
  box-shadow: 0 0 0 1px #3a3a5a !important;
}
:deep(.el-autocomplete .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #4fc3f7 !important;
}
:deep(.el-autocomplete .el-input__inner) {
  color: #e0e6f0 !important;
  background: transparent !important;
}
:deep(.el-autocomplete .el-input__inner::placeholder) {
  color: #606880;
}

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
  box-shadow: none !important;
}

/* ── 股票信息卡片 ── */
.stock-info-card {
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}

.info-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.info-name-block {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.info-name {
  font-size: 22px;
  font-weight: 700;
  color: #e0e6f0;
}
.info-code {
  font-size: 14px;
  color: #606880;
  font-family: 'Consolas', monospace;
}

.info-price-block {
  display: flex;
  align-items: center;
  gap: 14px;
}
.info-price {
  font-size: 32px;
  font-weight: 700;
  font-family: 'Consolas', 'Courier New', monospace;
}
.info-changes {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.info-change {
  font-size: 14px;
  font-family: 'Consolas', monospace;
}
.info-pct-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 700;
  font-family: 'Consolas', monospace;
}
.info-pct-badge.is-up {
  background: rgba(245, 101, 101, 0.15);
  color: #f56565;
}
.info-pct-badge.is-down {
  background: rgba(72, 187, 120, 0.15);
  color: #48bb78;
}

.info-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  border-top: 1px solid #2a2a4a;
  padding-top: 16px;
}
.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 90px;
  padding: 0 20px 0 0;
  margin-bottom: 8px;
}
.stat-label {
  font-size: 11px;
  color: #606880;
}
.stat-val {
  font-size: 13px;
  font-family: 'Consolas', monospace;
  color: #c0c8e0;
}

/* ── 图表占位 ── */
.chart-placeholder {
  background: #1a1a2e;
  border: 1px dashed #3a3a5a;
  border-radius: 12px;
  padding: 48px 20px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.placeholder-inner {
  text-align: center;
}
.placeholder-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}
.placeholder-text {
  font-size: 16px;
  color: #a0a8c0;
  margin-bottom: 8px;
}
.placeholder-sub {
  font-size: 12px;
  color: #606880;
  margin-bottom: 20px;
}

/* ── OHLC 表格 ── */
.ohlc-panel {
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 16px;
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
  background: rgba(79, 195, 247, 0.05) !important;
}
:deep(.el-table__inner-wrapper::before) { display: none; }

.mono {
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 13px;
}
.date-text { color: #a0a8c0; font-size: 12px; }
.amount-text { color: #a0a8c0; }

.pct-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.pct-badge.is-up  { background: rgba(245,101,101,0.12); color: #f56565; }
.pct-badge.is-down { background: rgba(72,187,120,0.12); color: #48bb78; }

.indicator-ma5  { color: #fbbf24; }
.indicator-ma10 { color: #60a5fa; }

.candle-shape {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
}
.candle-bull  { background: rgba(245,101,101,0.12); color: #f56565; }
.candle-bear  { background: rgba(72,187,120,0.12);  color: #48bb78; }
.candle-doji  { background: rgba(160,168,192,0.12); color: #a0a8c0; }

/* ── 引导页（未选股时） ── */
.empty-guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  text-align: center;
  gap: 12px;
}
.guide-icon { font-size: 56px; opacity: 0.4; }
.guide-title { font-size: 18px; color: #a0a8c0; font-weight: 600; }
.guide-desc  { font-size: 13px; color: #606880; }
.guide-examples {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 8px;
}
.guide-label { font-size: 12px; color: #606880; }
.example-tag {
  cursor: pointer;
  transition: opacity 0.2s;
}
.example-tag:hover { opacity: 0.75; }

/* ── 过渡动画 ── */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

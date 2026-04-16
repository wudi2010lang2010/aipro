<template>
  <div class="page">
    <div class="toolbar">
      <el-input v-model="form.ts_code" placeholder="股票代码，如 000001.SZ" style="width: 180px" />
      <el-input-number v-model="form.cost_price" :min="0" :precision="3" :step="0.1" placeholder="成本价" />
      <el-input-number v-model="form.shares" :min="100" :step="100" placeholder="数量" />
      <el-input v-model="form.buy_date" placeholder="买入日期 YYYY-MM-DD" style="width: 150px" />
      <el-button type="primary" :loading="saving" @click="create">新增持仓</el-button>
      <el-button :loading="loading" @click="loadAll">刷新</el-button>
    </div>

    <div class="cards">
      <el-card>
        <div class="k">持仓数量</div>
        <div class="v">{{ summary.count || 0 }}</div>
      </el-card>
      <el-card>
        <div class="k">持仓市值</div>
        <div class="v">{{ money(summary.total_market_value) }}</div>
      </el-card>
      <el-card>
        <div class="k">浮动盈亏</div>
        <div class="v" :class="num(summary.total_unrealized_pnl) >= 0 ? 'up' : 'down'">
          {{ signed(summary.total_unrealized_pnl) }}
        </div>
      </el-card>
      <el-card>
        <div class="k">浮动收益率</div>
        <div class="v" :class="num(summary.total_unrealized_pct) >= 0 ? 'up' : 'down'">
          {{ signed(summary.total_unrealized_pct) }}%
        </div>
      </el-card>
    </div>

    <el-card>
      <template #header><strong>账户净值曲线</strong></template>
      <EquityCurve :points="review.equity_curve || []" />
    </el-card>

    <el-card>
      <template #header><strong>复盘统计</strong></template>
      <div class="review-grid">
        <div>总交易: {{ review.total_trades ?? 0 }}</div>
        <div>胜率: {{ pct(review.win_rate) }}</div>
        <div>盈亏比: {{ fmt(review.profit_loss_ratio) }}</div>
        <div>最大回撤: {{ pct(review.max_drawdown_pct) }}</div>
        <div>最大连亏: {{ review.max_losing_streak ?? 0 }}</div>
        <div>累计已实现盈亏: {{ signed(review.total_realized_pnl) }}</div>
      </div>
    </el-card>

    <el-table :data="rows" stripe>
      <el-table-column type="index" width="56" label="#" />
      <el-table-column prop="ts_code" label="代码" width="120" />
      <el-table-column prop="name" label="名称" width="120" />
      <el-table-column prop="cost_price" label="成本" width="90" align="right" />
      <el-table-column prop="last_price" label="现价" width="90" align="right" />
      <el-table-column prop="shares" label="数量" width="80" align="right" />
      <el-table-column prop="hold_days" label="持仓天数" width="90" align="right" />
      <el-table-column label="浮动盈亏" width="120" align="right">
        <template #default="{ row }">
          <span :class="num(row.unrealized_pnl) >= 0 ? 'up' : 'down'">{{ signed(row.unrealized_pnl) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="盈亏%" width="100" align="right">
        <template #default="{ row }">
          <span :class="num(row.unrealized_pct) >= 0 ? 'up' : 'down'">{{ signed(row.unrealized_pct) }}%</span>
        </template>
      </el-table-column>
      <el-table-column label="止损" width="90" align="right">
        <template #default="{ row }">
          <el-input-number v-model="row.stop_loss" :min="0" :precision="3" :step="0.1" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="止盈" width="90" align="right">
        <template #default="{ row }">
          <el-input-number v-model="row.take_profit" :min="0" :precision="3" :step="0.1" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="saveLine(row)">保存</el-button>
          <el-button size="small" type="danger" @click="doClose(row)">平仓</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-card>
      <template #header><strong>交易记录</strong></template>
      <el-table :data="transactions" size="small" max-height="300">
        <el-table-column prop="trade_date" label="日期" width="110" />
        <el-table-column prop="ts_code" label="代码" width="120" />
        <el-table-column prop="action" label="方向" width="70" />
        <el-table-column prop="price" label="价格" width="90" align="right" />
        <el-table-column prop="shares" label="数量" width="90" align="right" />
        <el-table-column prop="net_amount" label="净额" width="120" align="right" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import EquityCurve from '@/components/charts/EquityCurve.vue'
import {
  addPosition,
  closePosition,
  getPortfolio,
  getPortfolioReview,
  getTransactions,
  updatePosition,
} from '@/api/portfolio'

const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const summary = ref({})
const review = ref({})
const transactions = ref([])

const form = reactive({
  ts_code: '000001.SZ',
  cost_price: 0,
  shares: 100,
  buy_date: '',
})

function num(v) {
  return Number(v || 0)
}

function fmt(v) {
  return Number(v || 0).toFixed(4)
}

function pct(v) {
  return `${Number(v || 0).toFixed(2)}%`
}

function signed(v) {
  const n = Number(v || 0)
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}`
}

function money(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadAll() {
  loading.value = true
  try {
    const [p, r, t] = await Promise.all([
      getPortfolio(false),
      getPortfolioReview(100000),
      getTransactions(200),
    ])
    rows.value = p?.data?.rows || []
    summary.value = p?.data?.summary || {}
    review.value = r?.data || {}
    transactions.value = t?.data || []
  } finally {
    loading.value = false
  }
}

async function create() {
  saving.value = true
  try {
    await addPosition({ ...form })
    await loadAll()
  } finally {
    saving.value = false
  }
}

async function saveLine(row) {
  await updatePosition(row.id, { stop_loss: row.stop_loss, take_profit: row.take_profit })
  await loadAll()
}

async function doClose(row) {
  await closePosition(row.id, {})
  await loadAll()
}

loadAll()
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
.toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.k { color: #9fb3c8; font-size: 12px; }
.v { margin-top: 4px; font-size: 22px; font-weight: 700; }
.up { color: #e84a5f; }
.down { color: #2a9d8f; }
.review-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
@media (max-width: 1100px) {
  .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .review-grid { grid-template-columns: 1fr; }
}
</style>

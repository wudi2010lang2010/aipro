<template>
  <div class="page">
    <div class="toolbar">
      <el-input v-model="form.ts_code" placeholder="股票代码，如 000001.SZ" style="width: 180px" />
      <el-input v-model="form.start_date" placeholder="开始日期 YYYYMMDD" style="width: 140px" />
      <el-input v-model="form.end_date" placeholder="结束日期 YYYYMMDD" style="width: 140px" />
      <el-input-number v-model="form.initial_cash" :min="10000" :step="10000" />
      <el-button type="primary" :loading="running" @click="run">执行回测</el-button>
      <el-button :loading="runningSim" @click="loadSim">AI仿真盘</el-button>
    </div>

    <el-card v-if="report">
      <template #header><strong>回测报告</strong></template>
      <div class="report-grid">
        <div>标的: {{ report.ts_code }}</div>
        <div>区间: {{ report.start_date }} - {{ report.end_date }}</div>
        <div>初始资金: {{ money(report.initial_cash) }}</div>
        <div>期末资金: {{ money(report.final_equity) }}</div>
        <div>总收益: <span :class="num(report.total_return_pct) >= 0 ? 'up' : 'down'">{{ signed(report.total_return_pct) }}%</span></div>
        <div>最大回撤: {{ signed(report.max_drawdown_pct) }}%</div>
        <div>交易次数: {{ report.trade_count }}</div>
        <div>胜率: {{ fmt(report.win_rate) }}%</div>
        <div>盈亏比: {{ fmt(report.profit_loss_ratio) }}</div>
      </div>
    </el-card>

    <el-card>
      <template #header><strong>资金曲线</strong></template>
      <EquityCurve :points="curve" />
    </el-card>

    <el-card>
      <template #header><strong>成交明细</strong></template>
      <el-table :data="trades" size="small" max-height="320">
        <el-table-column prop="date" label="日期" width="100" />
        <el-table-column prop="action" label="方向" width="70" />
        <el-table-column prop="price" label="价格" width="100" align="right" />
        <el-table-column prop="shares" label="数量" width="90" align="right" />
        <el-table-column prop="commission" label="手续费" width="100" align="right" />
        <el-table-column prop="stamp_duty" label="印花税" width="100" align="right" />
        <el-table-column prop="cash" label="现金" min-width="120" align="right" />
      </el-table>
    </el-card>

    <el-card>
      <template #header><strong>AI信号仿真盘</strong></template>
      <div v-if="sim">
        <div class="report-grid">
          <div>初始资金: {{ money(sim.initial_cash) }}</div>
          <div>当前现金: {{ money(sim.final_cash) }}</div>
          <div>交易笔数: {{ sim.trade_count }}</div>
          <div>当前持仓: {{ sim.holding ? `${sim.holding.ts_code} (${sim.holding.shares})` : '无' }}</div>
        </div>
      </div>
      <el-empty v-else description="暂无仿真数据" />
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import EquityCurve from '@/components/charts/EquityCurve.vue'
import { getBacktestResult, getVirtualSimulation, runBacktest } from '@/api/backtest'

const running = ref(false)
const runningSim = ref(false)
const report = ref(null)
const curve = ref([])
const trades = ref([])
const sim = ref(null)

const form = reactive({
  ts_code: '000001.SZ',
  start_date: '20240101',
  end_date: '20260415',
  initial_cash: 100000,
})

function num(v) {
  return Number(v || 0)
}

function fmt(v) {
  return Number(v || 0).toFixed(2)
}

function signed(v) {
  const n = Number(v || 0)
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}`
}

function money(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function run() {
  running.value = true
  try {
    const runRes = await runBacktest({ ...form })
    const rid = runRes?.data?.result_id
    if (!rid) return
    const detail = await getBacktestResult(rid)
    report.value = detail?.data?.report || null
    curve.value = detail?.data?.equity_curve || []
    trades.value = detail?.data?.trades || []
  } finally {
    running.value = false
  }
}

async function loadSim() {
  runningSim.value = true
  try {
    const res = await getVirtualSimulation(100000, 300)
    sim.value = res?.data || null
  } finally {
    runningSim.value = false
  }
}

loadSim()
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
.toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.report-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.up { color: #e84a5f; }
.down { color: #2a9d8f; }
@media (max-width: 1100px) {
  .report-grid { grid-template-columns: 1fr; }
}
</style>

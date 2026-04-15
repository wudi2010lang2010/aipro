<template>
  <div class="kline-page">
    <div class="header">
      <h2>K线分析</h2>
      <div class="tools">
        <el-autocomplete
          v-model="query"
          :fetch-suggestions="fetchSuggestions"
          placeholder="搜索股票代码或名称"
          clearable
          @select="onSelect"
        />
        <el-radio-group v-model="period" @change="load" size="small">
          <el-radio-button label="daily">日线</el-radio-button>
          <el-radio-button label="60min">60m</el-radio-button>
          <el-radio-button label="30min">30m</el-radio-button>
          <el-radio-button label="15min">15m</el-radio-button>
        </el-radio-group>
        <el-button :loading="loading" @click="load" size="small">刷新</el-button>
      </div>
    </div>

    <el-empty v-if="!current.ts_code" description="请选择股票开始分析" />

    <template v-else>
      <el-card class="summary">
        <div class="summary-grid">
          <div>
            <div class="label">股票</div>
            <div class="value">{{ current.name || current.ts_code }} ({{ current.ts_code }})</div>
          </div>
          <div>
            <div class="label">最新价</div>
            <div class="value mono">{{ num(last.close) }}</div>
          </div>
          <div>
            <div class="label">涨跌幅</div>
            <div class="value mono" :class="Number(last.pct_chg||0)>=0 ? 'up':'down'">{{ signed(last.pct_chg) }}%</div>
          </div>
          <div>
            <div class="label">成交量</div>
            <div class="value mono">{{ vol(last.volume) }}</div>
          </div>
        </div>
      </el-card>

      <KlineChart :klines="klines" />

      <el-card>
        <template #header>
          <strong>交易信号</strong>
        </template>
        <el-empty v-if="!signals.length" description="暂无信号" />
        <el-table v-else :data="signals" size="small">
          <el-table-column prop="name" label="信号" min-width="160" />
          <el-table-column prop="type" label="类型" width="110" />
          <el-table-column prop="desc" label="说明" min-width="360" />
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import { useRoute } from "vue-router"
import { getKline, searchStock } from "@/api/kline"
import KlineChart from "@/components/charts/KlineChart.vue"

const route = useRoute()
const query = ref("")
const period = ref("daily")
const loading = ref(false)
const klines = ref([])
const signals = ref([])
const current = ref({ ts_code: "", name: "" })

const last = computed(() => {
  if (!klines.value.length) return {}
  return klines.value[klines.value.length - 1]
})

function num(v) {
  if (v == null) return "--"
  return Number(v).toFixed(2)
}

function signed(v) {
  if (v == null) return "--"
  const n = Number(v)
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}`
}

function vol(v) {
  if (v == null) return "--"
  const n = Number(v)
  if (n >= 1e8) return `${(n / 1e8).toFixed(2)}B`
  if (n >= 1e4) return `${(n / 1e4).toFixed(2)}W`
  return n.toFixed(0)
}

async function fetchSuggestions(text, cb) {
  const q = text.trim()
  if (!q) return cb([])
  try {
    const res = await searchStock(q)
    const rows = (res?.code === 0 ? res.data : []) || []
    cb(rows.map((r) => ({ ...r, value: `${r.name} ${r.ts_code}` })))
  } catch {
    cb([])
  }
}

async function load() {
  if (!current.value.ts_code) return
  loading.value = true
  try {
    const res = await getKline(current.value.ts_code, period.value, 300)
    const data = res?.data || {}
    klines.value = data.klines || []
    signals.value = data.signals || []
  } finally {
    loading.value = false
  }
}

async function onSelect(item) {
  current.value = { ts_code: item.ts_code, name: item.name }
  query.value = `${item.name} ${item.ts_code}`
  await load()
}

onMounted(async () => {
  const code = String(route.params.code || "").toUpperCase()
  if (!code) return
  current.value = { ts_code: code, name: code }
  query.value = code
  await load()
})
</script>

<style scoped>
.kline-page { display: flex; flex-direction: column; gap: 14px; }
.header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.tools { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.label { font-size: 12px; color: #7f8c8d; }
.value { margin-top: 4px; font-weight: 600; }
.mono { font-family: Consolas, "Courier New", monospace; }
.up { color: #e84a5f; }
.down { color: #2a9d8f; }
@media (max-width: 900px) {
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>

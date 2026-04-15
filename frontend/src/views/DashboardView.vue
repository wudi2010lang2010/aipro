<template>
  <div class="dashboard">
    <div class="header">
      <h2>Market Dashboard</h2>
      <div class="header-right">
        <el-tag :type="marketStore.isOpen ? 'success' : 'info'">{{ marketStore.marketStatus.desc || marketStore.marketStatus.status }}</el-tag>
        <el-button size="small" :loading="loading" @click="refresh">Refresh</el-button>
      </div>
    </div>

    <div class="indices-grid">
      <div v-for="idx in marketStore.indices" :key="idx.ts_code" class="index-card" :class="Number(idx.change_pct) >= 0 ? 'up' : 'down'">
        <div class="name">{{ idx.display_name || idx.name }}</div>
        <div class="price mono">{{ num(idx.price) }}</div>
        <div class="delta mono">{{ signed(idx.change) }} ({{ signed(idx.change_pct) }}%)</div>
        <div class="time">{{ idx.update_time || '--:--:--' }}</div>
      </div>
    </div>

    <div class="grid-2">
      <el-card>
        <template #header>
          <div class="card-title">Top Gainers</div>
        </template>
        <QuoteTable :rows="marketStore.topGainers" @row-click="goKline" />
      </el-card>

      <el-card>
        <template #header>
          <div class="card-title">Sector Heatmap</div>
        </template>
        <SectorHeatmap :sectors="marketStore.sectors" />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { useRouter } from "vue-router"
import { useMarketStore } from "@/stores/market"
import QuoteTable from "@/components/tables/QuoteTable.vue"
import SectorHeatmap from "@/components/charts/SectorHeatmap.vue"

const marketStore = useMarketStore()
const router = useRouter()
const loading = ref(false)

function num(v) {
  if (v == null) return "--"
  return Number(v).toFixed(2)
}

function signed(v) {
  if (v == null) return "--"
  const n = Number(v)
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}`
}

async function refresh() {
  loading.value = true
  await marketStore.fetchAll()
  loading.value = false
}

function goKline(row) {
  if (!row?.ts_code) return
  router.push(`/kline/${row.ts_code}`)
}

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; }
.header { display: flex; align-items: center; justify-content: space-between; }
.header-right { display: flex; align-items: center; gap: 10px; }
.indices-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.index-card { border-radius: 10px; padding: 12px; background: #17212b; border: 1px solid #243746; }
.index-card.up { border-left: 4px solid #e84a5f; }
.index-card.down { border-left: 4px solid #2a9d8f; }
.name { color: #9fb3c8; font-size: 12px; }
.price { font-size: 24px; margin-top: 4px; }
.delta { margin-top: 4px; font-size: 13px; }
.time { margin-top: 6px; font-size: 12px; color: #708090; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.card-title { font-weight: 600; }
.mono { font-family: Consolas, "Courier New", monospace; }
@media (max-width: 1100px) {
  .indices-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .grid-2 { grid-template-columns: 1fr; }
}
</style>

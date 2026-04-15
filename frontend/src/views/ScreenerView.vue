<template>
  <div class="page">
    <div class="toolbar">
      <el-select v-model="preset" style="width: 220px" :loading="loadingPresets">
        <el-option v-for="(v, k) in presets" :key="k" :label="v.name" :value="k" />
      </el-select>
      <el-button type="primary" :loading="running" @click="run">执行扫描</el-button>
      <span class="muted">结果: {{ rows.length }} 条</span>
      <el-tag v-if="usedFallback" type="warning" size="small">
        {{ fallbackName || '兜底模式' }}
      </el-tag>
    </div>

    <el-table :data="rows" stripe @row-dblclick="openKline">
      <el-table-column type="index" width="56" label="#" />
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="ts_code" label="代码" min-width="120" />
      <el-table-column prop="price" label="价格" min-width="100" align="right" />
      <el-table-column prop="change_pct" label="涨跌幅" min-width="100" align="right">
        <template #default="{ row }">{{ fmtPct(row.change_pct) }}</template>
      </el-table-column>
      <el-table-column prop="turnover_rate" label="换手率" min-width="100" align="right">
        <template #default="{ row }">{{ fmtPct(row.turnover_rate) }}</template>
      </el-table-column>
      <el-table-column prop="volume_ratio" label="量比" min-width="90" align="right" />
      <el-table-column prop="score" label="评分" min-width="90" align="right" />
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPresets, runScreener } from '@/api/screener'

const router = useRouter()
const presets = ref({})
const preset = ref('trend_breakout')
const loadingPresets = ref(false)
const running = ref(false)
const rows = ref([])
const usedFallback = ref(false)
const fallbackName = ref('')

function fmtPct(v) {
  if (v == null) return '--'
  const n = Number(v)
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
}

async function loadPresets() {
  loadingPresets.value = true
  try {
    const res = await getPresets()
    presets.value = res.data || {}
  } finally {
    loadingPresets.value = false
  }
}

async function run() {
  running.value = true
  try {
    const res = await runScreener(preset.value, {}, 120)
    const data = res?.data || {}
    rows.value = data.rows || []
    usedFallback.value = Boolean(data.used_fallback)
    fallbackName.value = data.fallback_name || ''
  } finally {
    running.value = false
  }
}

function openKline(row) {
  if (row?.ts_code) router.push(`/kline/${row.ts_code}`)
}

onMounted(async () => {
  await loadPresets()
  await run()
})
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
.toolbar { display: flex; gap: 10px; align-items: center; }
.muted { color: #909399; font-size: 13px; }
</style>

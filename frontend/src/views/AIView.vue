<template>
  <div class="page">
    <div class="toolbar">
      <el-input v-model="tsCode" placeholder="输入股票代码，如 000001.SZ" style="max-width: 280px" />
      <el-select v-model="period" style="width: 120px">
        <el-option label="日线" value="daily" />
        <el-option label="60分钟" value="60min" />
        <el-option label="30分钟" value="30min" />
        <el-option label="15分钟" value="15min" />
      </el-select>
      <el-button type="primary" :loading="analyzing" @click="analyze">AI分析</el-button>
      <el-button :loading="loading" @click="loadSignals">刷新列表</el-button>
    </div>

    <RiskPanel :data="riskState" />

    <el-alert v-if="lastMessage" :title="lastMessage" type="success" show-icon :closable="false" />

    <el-table :data="signals" stripe @row-click="pick">
      <el-table-column prop="created_at" label="时间" min-width="170" />
      <el-table-column prop="ts_code" label="代码" min-width="120" />
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="signal" label="动作" width="90" />
      <el-table-column prop="confidence" label="置信度" width="90" />
      <el-table-column prop="risk_level" label="风险" width="90" />
      <el-table-column prop="reasoning" label="理由" min-width="420" show-overflow-tooltip />
    </el-table>

    <el-card v-if="selected" class="detail">
      <template #header><strong>信号详情</strong></template>
      <div>代码: {{ selected.ts_code }} {{ selected.name }}</div>
      <div>动作: {{ selected.signal }} | 置信度: {{ selected.confidence }}</div>
      <div>建议买入: {{ selected.buy_price ?? '--' }} | 止损: {{ selected.stop_loss ?? '--' }} | 止盈: {{ selected.take_profit ?? '--' }}</div>
      <div>风险: {{ selected.risk_level }} | 持有天数: {{ selected.hold_days ?? '--' }}</div>
      <div>风险点: {{ (selected.key_risks || []).join('、') || '--' }}</div>
      <div>理由: {{ selected.reasoning }}</div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { analyzeStock, getAISignals } from '@/api/ai'
import { getRiskStatus } from '@/api/risk'
import RiskPanel from '@/components/panels/RiskPanel.vue'

const tsCode = ref('000001.SZ')
const period = ref('daily')
const analyzing = ref(false)
const loading = ref(false)
const signals = ref([])
const selected = ref(null)
const lastMessage = ref('')
const riskState = ref(null)

async function loadSignals() {
  loading.value = true
  try {
    const res = await getAISignals(100)
    signals.value = res?.data || []
  } catch (err) {
    lastMessage.value = `加载信号失败: ${err?.response?.data?.detail || err?.message || '未知错误'}`
  } finally {
    loading.value = false
  }
}

async function analyze() {
  if (!tsCode.value) return
  analyzing.value = true
  try {
    const res = await analyzeStock(tsCode.value, period.value)
    lastMessage.value = `AI分析完成: ${res.data.ts_code} -> ${res.data.signal}`
    await loadSignals()
  } catch (err) {
    lastMessage.value = `AI分析失败: ${err?.response?.data?.detail || err?.message || '未知错误'}`
  } finally {
    analyzing.value = false
  }
}

function pick(row) {
  selected.value = row
}

async function loadRisk() {
  const res = await getRiskStatus()
  riskState.value = res?.data || null
}

loadSignals()
loadRisk()
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
.toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.detail { margin-top: 6px; }
</style>

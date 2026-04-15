<template>
  <el-card>
    <template #header><strong>风控状态</strong></template>
    <div class="grid" v-if="data">
      <div>熔断: <el-tag :type="data.circuit_breaker ? 'danger' : 'success'">{{ data.circuit_breaker ? '触发' : '正常' }}</el-tag></div>
      <div>单票上限: {{ pct(data.max_position_pct) }}</div>
      <div>最大持仓数: {{ data.max_holdings }}</div>
      <div>日亏熔断阈值: {{ pct(data.daily_loss_pct) }}</div>
      <div>固定止损: {{ pct(data.stop_loss_pct) }}</div>
      <div>移动止损: {{ pct(data.trailing_stop_pct) }}</div>
    </div>
    <el-empty v-else description="暂无风控数据" />
  </el-card>
</template>

<script setup>
const props = defineProps({ data: { type: Object, default: null } })
function pct(v) {
  if (v == null) return '--'
  return `${(Number(v) * 100).toFixed(2)}%`
}
</script>

<style scoped>
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; font-size: 14px; }
</style>

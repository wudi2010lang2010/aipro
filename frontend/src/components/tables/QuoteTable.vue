<template>
  <el-table
    :data="rows"
    size="small"
    stripe
    height="420"
    @row-click="onRowClick"
  >
    <el-table-column type="index" width="56" label="#" />
    <el-table-column prop="name" label="Name" min-width="120" />
    <el-table-column label="Code" min-width="110">
      <template #default="{ row }">
        <span class="mono">{{ shortCode(row.ts_code) }}</span>
      </template>
    </el-table-column>
    <el-table-column label="Price" min-width="90" align="right">
      <template #default="{ row }">
        <span :class="priceClass(row)">{{ num(row.price) }}</span>
      </template>
    </el-table-column>
    <el-table-column label="Change%" min-width="100" align="right">
      <template #default="{ row }">
        <span :class="priceClass(row)">{{ pct(row.change_pct) }}</span>
      </template>
    </el-table-column>
    <el-table-column label="Amount" min-width="120" align="right">
      <template #default="{ row }">
        <span class="mono">{{ amount(row.amount) }}</span>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
const props = defineProps({
  rows: { type: Array, default: () => [] },
})

const emit = defineEmits(["row-click"])

function onRowClick(row) {
  emit("row-click", row)
}

function shortCode(tsCode) {
  return (tsCode || "").split(".")[0]
}

function num(v) {
  if (v == null) return "--"
  return Number(v).toFixed(2)
}

function pct(v) {
  if (v == null) return "--"
  const n = Number(v)
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`
}

function amount(v) {
  if (v == null) return "--"
  const n = Number(v)
  if (n >= 1e8) return `${(n / 1e8).toFixed(2)}B`
  if (n >= 1e4) return `${(n / 1e4).toFixed(2)}W`
  return n.toFixed(0)
}

function priceClass(row) {
  const n = Number(row?.change_pct ?? 0)
  return n >= 0 ? "up mono" : "down mono"
}
</script>

<style scoped>
.mono { font-family: Consolas, "Courier New", monospace; }
.up { color: #e84a5f; }
.down { color: #2a9d8f; }
</style>

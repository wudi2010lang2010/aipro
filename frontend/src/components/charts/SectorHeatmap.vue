<template>
  <div class="heatmap-wrap">
    <v-chart class="heatmap" :option="option" autoresize />
  </div>
</template>

<script setup>
import { computed } from "vue"
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { HeatmapChart } from "echarts/charts"
import { GridComponent, VisualMapComponent, TooltipComponent } from "echarts/components"
import VChart from "vue-echarts"

use([CanvasRenderer, HeatmapChart, GridComponent, VisualMapComponent, TooltipComponent])

const props = defineProps({
  sectors: { type: Array, default: () => [] },
})

const option = computed(() => {
  const list = (props.sectors || []).slice(0, 24)
  const cols = 6
  const points = list.map((item, i) => {
    const x = i % cols
    const y = Math.floor(i / cols)
    return [x, y, Number(item.change_pct || 0), item.name || "未知"]
  })

  return {
    tooltip: {
      formatter: (p) => {
        const val = p.data || []
        return `${val[3] || "未知"}<br/>涨跌幅: ${Number(val[2] || 0).toFixed(2)}%`
      },
    },
    grid: { left: 8, right: 8, top: 8, bottom: 30, containLabel: true },
    xAxis: { type: "category", show: false, data: Array.from({ length: cols }, (_, i) => i) },
    yAxis: { type: "category", show: false, data: Array.from({ length: Math.ceil(list.length / cols) }, (_, i) => i) },
    visualMap: {
      min: -8,
      max: 8,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      text: ["上涨", "下跌"],
      calculable: true,
      inRange: { color: ["#2a9d8f", "#f1faee", "#e84a5f"] },
    },
    series: [
      {
        type: "heatmap",
        data: points,
        label: {
          show: true,
          formatter: (p) => `${p.data[3]}\n${Number(p.data[2]).toFixed(2)}%`,
          color: "#111",
          fontSize: 11,
        },
        emphasis: { itemStyle: { borderColor: "#333", borderWidth: 1 } },
      },
    ],
  }
})
</script>

<style scoped>
.heatmap-wrap { height: 420px; }
.heatmap { height: 100%; width: 100%; }
</style>

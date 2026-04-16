<template>
  <div class="curve-wrap">
    <v-chart class="curve" :option="option" autoresize />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const props = defineProps({
  points: { type: Array, default: () => [] },
})

const option = computed(() => {
  const list = props.points || []
  const x = list.map((p) => p.date)
  const y = list.map((p) => Number(p.equity || 0))
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['净值'], textStyle: { color: '#c8d2df' } },
    grid: { left: 12, right: 12, top: 32, bottom: 12, containLabel: true },
    xAxis: { type: 'category', data: x, axisLabel: { color: '#9fb3c8' } },
    yAxis: { type: 'value', axisLabel: { color: '#9fb3c8' } },
    series: [
      {
        name: '净值',
        type: 'line',
        smooth: true,
        data: y,
        showSymbol: false,
        lineStyle: { color: '#4fc3f7', width: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(79,195,247,0.35)' },
              { offset: 1, color: 'rgba(79,195,247,0.05)' },
            ],
          },
        },
      },
    ],
  }
})
</script>

<style scoped>
.curve-wrap { height: 320px; }
.curve { height: 100%; width: 100%; }
</style>

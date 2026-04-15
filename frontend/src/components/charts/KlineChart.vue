<template>
  <div ref="container" class="chart"></div>
</template>

<script setup>
import { createChart, LineStyle, CandlestickSeries, HistogramSeries, LineSeries } from "lightweight-charts"
import { onMounted, onUnmounted, ref, watch } from "vue"

const props = defineProps({
  klines: { type: Array, default: () => [] },
})

const container = ref(null)
let chart
let candle
let volume
let ma5
let ma10
let ma20

function toTime(str) {
  if (!str) return ""
  return String(str).slice(0, 10)
}

function rebuild() {
  if (!container.value) return
  if (chart) chart.remove()

  chart = createChart(container.value, {
    layout: { background: { color: "#101820" }, textColor: "#d9e2ec" },
    grid: { vertLines: { color: "#203040" }, horzLines: { color: "#203040" } },
    rightPriceScale: { borderColor: "#2b3e50" },
    timeScale: { borderColor: "#2b3e50", timeVisible: true },
    width: container.value.clientWidth,
    height: 520,
  })

  candle = chart.addSeries(CandlestickSeries, {
    upColor: "#e84a5f",
    downColor: "#2a9d8f",
    borderDownColor: "#2a9d8f",
    borderUpColor: "#e84a5f",
    wickDownColor: "#2a9d8f",
    wickUpColor: "#e84a5f",
  })

  volume = chart.addSeries(HistogramSeries, {
    color: "#4f6d7a",
    priceFormat: { type: "volume" },
    priceScaleId: "",
  })

  volume.priceScale().applyOptions({
    scaleMargins: { top: 0.78, bottom: 0 },
  })

  ma5 = chart.addSeries(LineSeries, { color: "#f4a261", lineWidth: 1, lineStyle: LineStyle.Solid })
  ma10 = chart.addSeries(LineSeries, { color: "#e9c46a", lineWidth: 1, lineStyle: LineStyle.Solid })
  ma20 = chart.addSeries(LineSeries, { color: "#8ecae6", lineWidth: 1, lineStyle: LineStyle.Solid })

  syncData()
}

function syncData() {
  if (!chart || !candle) return
  const rows = (props.klines || []).map((k) => ({
    time: toTime(k.time),
    open: Number(k.open),
    high: Number(k.high),
    low: Number(k.low),
    close: Number(k.close),
    volume: Number(k.volume || 0),
    ma5: k.ma5 == null ? null : Number(k.ma5),
    ma10: k.ma10 == null ? null : Number(k.ma10),
    ma20: k.ma20 == null ? null : Number(k.ma20),
  }))

  candle.setData(rows.map((r) => ({ time: r.time, open: r.open, high: r.high, low: r.low, close: r.close })))
  volume.setData(rows.map((r) => ({ time: r.time, value: r.volume, color: r.close >= r.open ? "#e84a5f99" : "#2a9d8f99" })))

  ma5.setData(rows.filter((r) => r.ma5 != null).map((r) => ({ time: r.time, value: r.ma5 })))
  ma10.setData(rows.filter((r) => r.ma10 != null).map((r) => ({ time: r.time, value: r.ma10 })))
  ma20.setData(rows.filter((r) => r.ma20 != null).map((r) => ({ time: r.time, value: r.ma20 })))

  chart.timeScale().fitContent()
}

function onResize() {
  if (!chart || !container.value) return
  chart.applyOptions({ width: container.value.clientWidth })
}

onMounted(() => {
  rebuild()
  window.addEventListener("resize", onResize)
})

onUnmounted(() => {
  window.removeEventListener("resize", onResize)
  if (chart) chart.remove()
})

watch(() => props.klines, () => syncData(), { deep: true })
</script>

<style scoped>
.chart {
  width: 100%;
  min-height: 520px;
  border: 1px solid #243b4a;
  border-radius: 8px;
  overflow: hidden;
}
</style>

<template>
  <div class="page">
    <el-card>
      <template #header><strong>API配置（本地保存）</strong></template>
      <div class="grid">
        <el-input v-model="form.tushare_token" placeholder="TUSHARE_TOKEN" show-password />
        <el-input v-model="form.gemini_api_key" placeholder="GEMINI_API_KEY" show-password />
        <el-input v-model="form.wecom_webhook_url" placeholder="WECOM_WEBHOOK_URL" />
      </div>
    </el-card>

    <el-card>
      <template #header><strong>风控参数</strong></template>
      <div class="grid-2">
        <div>
          <label>单笔止损 (%)</label>
          <el-input-number v-model="form.risk_stop_loss_pct" :min="0.005" :max="0.2" :step="0.005" :precision="3" />
        </div>
        <div>
          <label>移动止损 (%)</label>
          <el-input-number v-model="form.risk_trailing_stop_pct" :min="0.005" :max="0.2" :step="0.005" :precision="3" />
        </div>
        <div>
          <label>单日熔断 (%)</label>
          <el-input-number v-model="form.risk_daily_loss_pct" :min="0.01" :max="0.2" :step="0.005" :precision="3" />
        </div>
        <div>
          <label>单票仓位上限 (%)</label>
          <el-input-number v-model="form.risk_max_position_pct" :min="0.05" :max="1" :step="0.05" :precision="2" />
        </div>
        <div>
          <label>最大持仓数</label>
          <el-input-number v-model="form.risk_max_holdings" :min="1" :max="30" :step="1" />
        </div>
      </div>
    </el-card>

    <div class="toolbar">
      <el-button type="primary" @click="save">保存到浏览器</el-button>
      <el-button @click="reset">恢复默认</el-button>
    </div>

    <el-card>
      <template #header><strong>.env 预览</strong></template>
      <pre class="env-preview">{{ envPreview }}</pre>
    </el-card>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'

const KEY = 'stock_ai_local_settings_v1'

const defaults = {
  tushare_token: '',
  gemini_api_key: '',
  wecom_webhook_url: '',
  risk_stop_loss_pct: 0.05,
  risk_trailing_stop_pct: 0.03,
  risk_daily_loss_pct: 0.03,
  risk_max_position_pct: 0.3,
  risk_max_holdings: 5,
}

function load() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return { ...defaults }
    return { ...defaults, ...JSON.parse(raw) }
  } catch {
    return { ...defaults }
  }
}

const form = reactive(load())

const envPreview = computed(() => {
  return [
    `TUSHARE_TOKEN=${form.tushare_token || 'your_tushare_token_here'}`,
    `GEMINI_API_KEY=${form.gemini_api_key || 'your_gemini_api_key_here'}`,
    `WECOM_WEBHOOK_URL=${form.wecom_webhook_url || 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx'}`,
    `RISK_STOP_LOSS_PCT=${form.risk_stop_loss_pct}`,
    `RISK_TRAILING_STOP_PCT=${form.risk_trailing_stop_pct}`,
    `RISK_DAILY_LOSS_PCT=${form.risk_daily_loss_pct}`,
    `RISK_MAX_POSITION_PCT=${form.risk_max_position_pct}`,
    `RISK_MAX_HOLDINGS=${form.risk_max_holdings}`,
  ].join('\n')
})

function save() {
  localStorage.setItem(KEY, JSON.stringify(form))
}

function reset() {
  Object.assign(form, defaults)
  save()
}
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 12px; }
.grid { display: grid; grid-template-columns: 1fr; gap: 8px; }
.grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.toolbar { display: flex; gap: 8px; }
label { display: block; font-size: 12px; color: #9fb3c8; margin-bottom: 4px; }
.env-preview { white-space: pre-wrap; margin: 0; font-family: Consolas, monospace; font-size: 12px; }
@media (max-width: 900px) {
  .grid-2 { grid-template-columns: 1fr; }
}
</style>

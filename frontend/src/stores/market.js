import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
  getIndices,
  getTopGainers,
  getSectors,
  getMarketStatus,
} from "@/api/market";

// ── 字段归一化：将 API 返回字段名统一映射为前端期望的字段名 ──────────────────
function normalizeQuote(item) {
  if (!item) return item;
  return {
    ...item,
    // 当前价：API 返回 price，模板期望 close
    close: item.price ?? item.close ?? null,
    // 涨跌幅：API 返回 change_pct，模板期望 pct_chg
    pct_chg: item.change_pct ?? item.pct_chg ?? null,
    // 成交量：API 返回 volume，模板期望 vol
    vol: item.volume ?? item.vol ?? null,
    // 量比：API 暂无此字段，保留 null 占位
    vol_ratio: item.volume_ratio ?? item.vol_ratio ?? null,
  };
}

export const useMarketStore = defineStore("market", () => {
  const indices = ref([]);
  const topGainers = ref([]);
  const sectors = ref([]);
  const marketStatus = ref({ status: "UNKNOWN", desc: "加载中" });
  const lastUpdate = ref("");

  const isOpen = computed(() => marketStatus.value.status === "OPEN");

  async function fetchAll() {
    try {
      const [idxRes, gainRes, secRes, stRes] = await Promise.all([
        getIndices(),
        getTopGainers(20),
        getSectors(),
        getMarketStatus(),
      ]);

      if (idxRes.code === 0) {
        indices.value = (idxRes.data.indices || []).map(normalizeQuote);
      }
      if (gainRes.code === 0) {
        topGainers.value = (gainRes.data || []).map(normalizeQuote);
      }
      if (secRes.code === 0) {
        sectors.value = (secRes.data || []).map(normalizeQuote);
      }
      if (stRes.code === 0) {
        marketStatus.value = stRes.data;
      }

      lastUpdate.value = new Date().toLocaleTimeString("zh-CN");
    } catch (e) {
      console.error("fetchAll error:", e);
    }
  }

  function updateFromWs(data) {
    if (data.indices) {
      indices.value = data.indices.map(normalizeQuote);
    }
    if (data.market_status) {
      marketStatus.value = {
        ...marketStatus.value,
        status: data.market_status,
        desc: data.market_status_desc ?? marketStatus.value.desc,
      };
    }
    lastUpdate.value = new Date().toLocaleTimeString("zh-CN");
  }

  return {
    indices,
    topGainers,
    sectors,
    marketStatus,
    lastUpdate,
    isOpen,
    fetchAll,
    updateFromWs,
  };
});

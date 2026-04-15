# AI 股票分析软件 - 项目规划文档 v3.0

> 本文档为 AI 股票分析软件的完整项目规划。
> **v3.0 更新：** 架构切换为 FastAPI + Vue 3 前后端分离，引入 TradingView Lightweight Charts + ECharts 双图表方案，更新目录结构、API 设计、前端组件、4 周计划与打包方案。

---

## 项目概述

| 项目 | 内容 |
|------|------|
| **项目名称** | Stock AI Analyzer |
| **项目类型** | 本地 Web 应用（FastAPI 后端 + Vue 3 前端） |
| **核心功能** | AI 辅助短线趋势交易分析 |
| **目标用户** | 个人投资者 / 量化交易学习者 |
| **交易市场** | A 股（沪深两市） |
| **交易风格** | 短线趋势（持仓 1-5 天） |
| **运行方式** | 本地启动服务，浏览器访问 http://localhost:8000 |

---

## 核心技术栈

### 后端（Python）

| 组件 | 技术选型 | 版本要求 | 说明 |
|------|----------|----------|------|
| **语言** | Python | 3.10+ | - |
| **Web 框架** | FastAPI | 0.115+ | REST API + WebSocket |
| **ASGI 服务器** | Uvicorn | 0.30+ | 本地运行，支持热重载 |
| **数据存储** | SQLite + SQLAlchemy | SQLAlchemy 2.0+ | 本地数据库，ORM 操作 |
| **AI 引擎** | Google Gemini API | gemini-3.1-pro / flash-lite | 结构化交易分析输出 |
| **技术指标** | pandas-ta | 0.3.14b+ | MA/MACD/RSI/KDJ/BOLL 等 |
| **任务调度** | APScheduler | 3.10+ | 盘中 2-3 分钟轮询 |
| **数据验证** | pydantic | 2.0+ | API 请求/响应结构校验 |
| **日志** | loguru | 0.7+ | 结构化日志，自动滚动 |
| **配置管理** | python-dotenv | 1.0+ | API Key 安全管理 |

### 前端（Node.js）

| 组件 | 技术选型 | 版本要求 | 说明 |
|------|----------|----------|------|
| **框架** | Vue 3 | 3.4+ | Composition API |
| **构建工具** | Vite | 5.0+ | 极速热重载开发 |
| **状态管理** | Pinia | 2.1+ | 替代 Vuex，更简洁 |
| **路由** | Vue Router | 4.3+ | 单页面路由 |
| **UI 组件库** | Element Plus | 2.7+ | 适合数据密集型界面 |
| **K 线图表** | TradingView Lightweight Charts | 5.1+ | 专业 K 线，Apache 2.0 |
| **其他图表** | ECharts + vue-echarts | ECharts 5.5+ | 板块热力图/净值曲线 |
| **HTTP 请求** | Axios | 1.7+ | REST API 调用封装 |

---

## 数据源方案

### 数据源分工

| 数据类型 | 主数据源 | 备选/补充 | 频率 |
|----------|----------|-----------|------|
| **历史日线** | tushare `daily` | akshare | 每日收盘后 |
| **分钟线** | tushare `stk_mins` | - | 盘后批量（存最近 60 天） |
| **实时行情** | 腾讯财经 API | 新浪财经 API | 2-3 分钟轮询 |
| **龙虎榜** | tushare `top_list` | - | 每日收盘后 |
| **北向资金** | tushare `moneyflow_hsgt` | - | 每日收盘后 |
| **沪深股通十大** | tushare `hsgt_top10` | - | 每日收盘后 |
| **个股资金流向** | tushare `moneyflow` | akshare | 每日收盘后 |
| **每日指标** | tushare `daily_basic` | - | 每日收盘后（换手率/量比） |
| **涨幅榜 Top20** | 腾讯实时 API（自行排序） | - | 2-3 分钟轮询 |
| **热点板块** | 新浪财经板块 API | - | 2-3 分钟轮询 |
| **大盘指数** | 腾讯/新浪 API | - | 2-3 分钟轮询 |
| **股票基础信息** | tushare `stock_basic` | - | 每周更新一次 |
| **交易日历** | tushare `trade_cal` | - | 每月更新一次 |

### tushare 积分测试结果（2010 积分）

| 接口 | 状态 | 返回条数 |
|------|------|----------|
| `daily` 日线 | ✅ 可用 | 8 条 |
| `stk_mins` 分钟线 | ✅ 可用 | 正常 |
| `top_list` 龙虎榜 | ✅ 可用 | 79 条 |
| `moneyflow_hsgt` 北向资金 | ✅ 可用 | 1 条 |
| `hsgt_top10` 沪深股通十大 | ✅ 可用 | 10 条 |
| `moneyflow` 个股资金流向 | ✅ 可用 | 8 条 |
| `daily_basic` 每日指标 | ✅ 可用 | 8 条 |
| `stock_basic` 股票列表 | ✅ 可用 | 5502 条 |
| `trade_cal` 交易日历 | ✅ 可用 | 正常 |

### 实时接口测试结果

| 接口 | 状态 | 说明 |
|------|------|------|
| 东方财富 API | ❌ 网络阻断 | akshare 批量请求被拦截，不使用 |
| 新浪财经 | ✅ 成功 | 大盘/个股/板块实时数据 |
| 腾讯财经 | ✅ 成功 | 个股/指数实时报价，主力数据源 |

> **注意：** 腾讯/新浪数据有 15-30 秒延迟，不影响 2-3 分钟频率的决策判断。

---

## 完整目录结构

```
stock-ai-analyzer/
│
├── backend/                              # Python FastAPI 后端
│   ├── main.py                           # FastAPI 应用入口 + 静态文件挂载
│   ├── requirements.txt                  # Python 依赖
│   ├── config.py                         # 配置读取（从 .env 加载）
│   ├── .env                              # API Keys（不提交 git）
│   ├── .env.example                      # 配置模板（提交 git）
│   │
│   ├── db/                               # SQLite 数据库文件（运行时生成）
│   ├── logs/                             # 日志目录（运行时生成）
│   │
│   ├── data/                             # 数据获取与存储层
│   │   ├── __init__.py
│   │   ├── schema.py                     # 建表 DDL + 初始化
│   │   ├── storage.py                    # SQLAlchemy Session 封装
│   │   ├── tushare_client.py             # tushare API 封装
│   │   ├── realtime_client.py            # 腾讯/新浪实时行情
│   │   ├── updater.py                    # 增量更新调度（盘前/盘后）
│   │   └── calendar_util.py             # 交易日历工具
│   │
│   ├── indicators/                       # 技术指标层
│   │   ├── __init__.py
│   │   ├── calculator.py                 # pandas-ta 指标计算封装
│   │   └── signals.py                    # 信号生成（金叉/突破/异动）
│   │
│   ├── screener/                         # 选股模块
│   │   ├── __init__.py
│   │   ├── filters.py                    # 条件过滤器
│   │   ├── scanner.py                    # 全市场扫描主逻辑
│   │   └── presets.py                    # 预设选股策略
│   │
│   ├── risk/                             # 风控引擎
│   │   ├── __init__.py
│   │   ├── engine.py                     # 主风控逻辑（仓位/熔断/黑名单）
│   │   ├── stop_loss.py                  # 止损止盈（固定/移动/时间止损）
│   │   └── rules.py                      # A 股规则（T+1/涨跌停/停牌）
│   │
│   ├── ai/                               # AI 决策层
│   │   ├── __init__.py
│   │   ├── gemini_client.py              # Gemini API 封装（含限速队列）
│   │   ├── prompts.py                    # Prompt 模板管理
│   │   ├── analyzer.py                   # 分析主逻辑
│   │   └── schemas.py                    # 输入/输出 pydantic 结构
│   │
│   ├── portfolio/                        # 持仓管理
│   │   ├── __init__.py
│   │   ├── manager.py                    # 持仓录入/盈亏/成本跟踪
│   │   └── review.py                     # 复盘统计
│   │
│   ├── backtest/                         # 回测框架
│   │   ├── __init__.py
│   │   ├── engine.py                     # 回测引擎（含手续费/印花税/滑点）
│   │   └── simulator.py                  # 仿真盘（虚拟资金实时模拟）
│   │
│   ├── notifications/                    # 通知模块
│   │   ├── __init__.py
│   │   └── sender.py                     # 企业微信 Webhook + SMTP 邮件
│   │
│   └── api/                              # FastAPI 路由层
│       ├── __init__.py
│       ├── websocket.py                  # WebSocket 实时行情推送
│       └── routes/
│           ├── market.py                 # 行情接口（指数/涨幅榜/板块）
│           ├── kline.py                  # K 线数据接口
│           ├── screener.py               # 选股接口
│           ├── ai.py                     # AI 分析接口
│           ├── portfolio.py              # 持仓接口
│           └── backtest.py               # 回测接口
│
├── frontend/                             # Vue 3 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.ts                       # 入口（注册 Vue/Pinia/Router）
│       ├── App.vue                       # 根组件
│       │
│       ├── router/
│       │   └── index.ts                  # 路由定义
│       │
│       ├── stores/                       # Pinia 状态管理
│       │   ├── market.ts                 # 行情状态
│       │   ├── portfolio.ts              # 持仓状态
│       │   ├── ai.ts                     # AI 信号状态
│       │   └── settings.ts              # 用户配置状态
│       │
│       ├── api/                          # Axios 请求封装
│       │   ├── http.ts                   # Axios 实例（baseURL/拦截器）
│       │   ├── market.ts
│       │   ├── kline.ts
│       │   ├── screener.ts
│       │   ├── ai.ts
│       │   └── portfolio.ts
│       │
│       ├── composables/                  # 可复用逻辑
│       │   ├── useWebSocket.ts           # WebSocket 实时数据
│       │   └── useNotification.ts        # 浏览器桌面通知
│       │
│       ├── views/                        # 页面视图（对应路由）
│       │   ├── DashboardView.vue         # 市场看板
│       │   ├── ScreenerView.vue          # 选股
│       │   ├── KlineView.vue             # K 线分析
│       │   ├── AIView.vue                # AI 信号
│       │   ├── PortfolioView.vue         # 持仓管理
│       │   ├── BacktestView.vue          # 回测
│       │   └── SettingsView.vue          # 设置
│       │
│       └── components/                   # 可复用组件
│           ├── charts/
│           │   ├── KlineChart.vue        # TradingView K 线图
│           │   ├── SectorHeatmap.vue     # ECharts 板块热力图
│           │   ├── MoneyFlowChart.vue    # ECharts 北向资金曲线
│           │   └── EquityCurve.vue       # ECharts 账户净值曲线
│           ├── tables/
│           │   ├── QuoteTable.vue        # 实时行情表格（涨红跌绿）
│           │   ├── ScreenerTable.vue     # 选股结果表格
│           │   └── PortfolioTable.vue    # 持仓明细表格
│           ├── panels/
│           │   ├── IndexPanel.vue        # 大盘指数卡片
│           │   ├── RiskPanel.vue         # 风控状态面板
│           │   └── AISignalCard.vue      # 单条 AI 信号卡片
│           └── layout/
│               ├── NavBar.vue            # 顶部导航
│               └── StatusBar.vue         # 底部状态栏（连接状态/定时任务）
│
└── scripts/
    ├── start.py                          # 一键启动（启动后端+自动打开浏览器）
    └── build.py                          # 打包脚本（前端构建+PyInstaller）
```

---

## API 接口设计

### REST 接口

| Method | 路径 | 说明 |
|--------|------|------|
| `GET` | `/api/market/indices` | 大盘指数（沪深创业科创） |
| `GET` | `/api/market/top-gainers` | 涨幅榜 Top20 |
| `GET` | `/api/market/sectors` | 板块涨跌幅排名 |
| `GET` | `/api/market/north-money` | 北向资金净流入 |
| `GET` | `/api/kline/{ts_code}` | K 线数据（日/60/30/15 分钟，含复权） |
| `GET` | `/api/kline/{ts_code}/indicators` | 技术指标值（MA/MACD/RSI/KDJ/BOLL） |
| `GET` | `/api/kline/{ts_code}/signals` | 技术信号列表（金叉/突破等） |
| `GET` | `/api/screener/presets` | 预设策略列表 |
| `POST` | `/api/screener/run` | 执行选股扫描（传入条件参数） |
| `POST` | `/api/ai/analyze` | 触发单股 AI 深度分析 |
| `GET` | `/api/ai/signals` | AI 历史信号列表（支持分页/过滤） |
| `GET` | `/api/ai/signals/{id}` | 单条信号详情 |
| `GET` | `/api/portfolio` | 当前持仓列表 |
| `POST` | `/api/portfolio` | 录入持仓 |
| `PUT` | `/api/portfolio/{id}` | 修改持仓（止损价/止盈价） |
| `DELETE` | `/api/portfolio/{id}` | 平仓 |
| `GET` | `/api/portfolio/review` | 复盘统计（胜率/盈亏比/最大回撤） |
| `GET` | `/api/transactions` | 历史交易记录 |
| `POST` | `/api/backtest/run` | 执行回测（异步任务） |
| `GET` | `/api/backtest/results/{id}` | 回测结果（含资金曲线数据） |
| `GET` | `/api/settings` | 读取用户配置 |
| `PUT` | `/api/settings` | 保存用户配置 |

### WebSocket 接口

```
WS  ws://localhost:8000/ws

推送消息类型（后端 → 前端）：
  { "type": "quote",      "data": { 实时行情快照 } }       每 2-3 分钟
  { "type": "signal",     "data": { AI 信号 } }           有信号时
  { "type": "risk_alert", "data": { 风控警告 } }          触发止损/熔断
  { "type": "scheduler",  "data": { 定时任务状态 } }       任务状态同步
```

---

## 前端页面设计

### 路由结构

```
/                  → 重定向至 /dashboard
/dashboard         → 市场看板
/screener          → 选股
/kline/:code?      → K 线分析（code 可选，默认空白）
/ai                → AI 信号
/portfolio         → 持仓管理
/backtest          → 回测
/settings          → 设置
```

### 各页面布局

```
市场看板（/dashboard）
  ┌─────────────────────────────────────────────┐
  │ [沪指] [深指] [创业板] [科创板]  实时指数卡片  │
  ├────────────────────┬────────────────────────┤
  │  涨幅榜 Top20      │  板块热力图（ECharts）  │
  │  QuoteTable        │  SectorHeatmap         │
  ├────────────────────┼────────────────────────┤
  │  北向资金净流入曲线 │  今日 AI 信号摘要       │
  │  MoneyFlowChart    │  AISignalCard × N      │
  └────────────────────┴────────────────────────┘

K 线分析（/kline/:code）
  ┌─────────────────────────────────────────────┐
  │ 搜索股票 [输入框]  周期切换 [日/60/30/15分]  │
  ├─────────────────────────────────────────────┤
  │                                             │
  │   TradingView Lightweight Charts            │
  │   主图：K 线 + MA5/10/20/60                 │
  │   副图1：成交量柱 + 量 MA5/10               │
  │   副图2：MACD（DIF/DEA/柱）                 │
  │   副图3：RSI（6/12/24）                     │
  │                                             │
  ├─────────────────────────────────────────────┤
  │ [当前指标值展示]        [请 AI 分析 按钮]    │
  └─────────────────────────────────────────────┘

选股（/screener）
  ┌─────────────────────────────────────────────┐
  │ 预设策略下拉  [趋势突破 ▼]  [立即扫描 按钮]  │
  ├─────────────────────────────────────────────┤
  │ 自定义条件（可折叠）                          │
  │ 价格区间 [5~50]  市值 [20亿~300亿]          │
  │ 量比 [>1.5]  换手率 [>2%]  涨幅 [2%~8%]   │
  ├─────────────────────────────────────────────┤
  │  选股结果表格（ScreenerTable）               │
  │  股票名 | 涨幅% | 量比 | 换手率 | 信号数     │
  │  双击行 → 跳转至 /kline/:code               │
  └─────────────────────────────────────────────┘

AI 信号（/ai）
  ┌───────────────────┬─────────────────────────┐
  │  信号队列          │  信号详情               │
  │  待分析 / 已完成   │  买入/卖出/观望 标签     │
  │  AISignalCard × N │  置信度进度条            │
  │                   │  理由文本                │
  │                   │  建议买价/止损/止盈价     │
  │                   │  风险提示列表            │
  ├───────────────────┴─────────────────────────┤
  │  历史信号记录（可按日期/股票/信号类型过滤）    │
  └─────────────────────────────────────────────┘

持仓管理（/portfolio）
  ┌─────────────────────────────────────────────┐
  │ 总资产 [XXX]  总盈亏 [+X%]  今日盈亏 [+X%] │
  ├─────────────────────────────────────────────┤
  │  持仓明细（PortfolioTable）                  │
  │  股票 | 成本 | 现价 | 盈亏% | 止损 | 持仓天  │
  ├──────────────────────┬──────────────────────┤
  │  账户净值曲线         │  复盘统计             │
  │  EquityCurve         │  胜率/盈亏比/最大回撤 │
  └──────────────────────┴──────────────────────┘

回测（/backtest）
  ┌────────────────────┬────────────────────────┐
  │  参数配置           │  资金曲线（ECharts）   │
  │  策略选择           │  EquityCurve           │
  │  时间范围           ├────────────────────────┤
  │  初始资金           │  回测报告               │
  │  手续费率           │  年化收益/夏普/最大回撤 │
  │  [执行回测 按钮]    │  总交易次数/胜率        │
  └────────────────────┴────────────────────────┘
```

---

## 数据库 Schema

### 表结构总览

| 表名 | 说明 | 预计数据量 |
|------|------|-----------|
| `stocks` | 股票基础信息 | ~5500 条 |
| `trade_calendar` | 交易日历 | ~250 条/年 |
| `daily_kline` | 日线数据（前复权） | ~5500 × 250 × N年 |
| `minute_kline` | 分钟线（最近 60 交易日） | 按需存储 |
| `daily_basic` | 每日指标（换手率/量比/PE） | 同日线 |
| `realtime_snapshot` | 实时快照（滚动保留 7 天） | 轮询存档 |
| `money_flow` | 个股资金流向 | 同日线 |
| `north_money` | 北向资金 | ~250 条/年 |
| `dragon_tiger` | 龙虎榜 | 按实际数量 |
| `watchlist` | 自选股 | 用户数据 |
| `portfolio` | 当前持仓 | 用户数据 |
| `transactions` | 历史交易记录 | 用户数据 |
| `ai_signals` | AI 分析信号历史 | 用户数据 |
| `screener_results` | 选股结果快照（保留 30 天） | 滚动清理 |

### 关键表 DDL（schema.py 实现）

```sql
-- 股票基础信息
CREATE TABLE stocks (
    ts_code     TEXT PRIMARY KEY,   -- 如 000001.SZ
    symbol      TEXT NOT NULL,
    name        TEXT NOT NULL,
    market      TEXT,               -- 主板/创业板/科创板
    industry    TEXT,
    list_date   TEXT,
    is_st       INTEGER DEFAULT 0,
    is_active   INTEGER DEFAULT 1,
    updated_at  TEXT
);

-- 日线数据（前复权）
CREATE TABLE daily_kline (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code     TEXT NOT NULL,
    trade_date  TEXT NOT NULL,
    open        REAL, high REAL, low REAL, close REAL,
    volume      REAL,
    amount      REAL,
    pct_chg     REAL,
    UNIQUE(ts_code, trade_date)
);

-- 每日指标
CREATE TABLE daily_basic (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code       TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    turnover_rate REAL,
    volume_ratio  REAL,
    pe            REAL,
    pb            REAL,
    total_mv      REAL,
    circ_mv       REAL,
    UNIQUE(ts_code, trade_date)
);

-- 分钟线（仅保留最近 60 交易日）
CREATE TABLE minute_kline (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code     TEXT NOT NULL,
    trade_time  TEXT NOT NULL,
    open        REAL, high REAL, low REAL, close REAL,
    volume      REAL,
    amount      REAL,
    UNIQUE(ts_code, trade_time)
);

-- 持仓表
CREATE TABLE portfolio (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code       TEXT NOT NULL,
    name          TEXT,
    cost_price    REAL NOT NULL,
    shares        INTEGER NOT NULL,
    buy_date      TEXT NOT NULL,
    stop_loss     REAL,
    take_profit   REAL,
    status        TEXT DEFAULT 'OPEN',
    note          TEXT,
    created_at    TEXT
);

-- 交易记录
CREATE TABLE transactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code       TEXT NOT NULL,
    name          TEXT,
    action        TEXT NOT NULL,    -- BUY / SELL
    price         REAL NOT NULL,
    shares        INTEGER NOT NULL,
    commission    REAL,
    stamp_duty    REAL,
    net_amount    REAL,
    trade_date    TEXT NOT NULL,
    note          TEXT
);

-- AI 信号历史
CREATE TABLE ai_signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code         TEXT NOT NULL,
    name            TEXT,
    signal          TEXT NOT NULL,  -- BUY / SELL / HOLD / WATCH
    confidence      INTEGER,        -- 0-100
    reasoning       TEXT,
    buy_price       REAL,
    stop_loss       REAL,
    take_profit     REAL,
    risk_level      TEXT,           -- LOW / MEDIUM / HIGH
    hold_days       INTEGER,
    key_risks       TEXT,           -- JSON 字符串
    model_version   TEXT,
    created_at      TEXT
);
```

---

## 技术指标体系

### 指标清单（pandas-ta 计算，后端返回给前端渲染）

| 指标 | 参数 | 用途 |
|------|------|------|
| **MA** | 5, 10, 20, 60 | 趋势方向、支撑压力 |
| **EMA** | 12, 26 | MACD 基础 |
| **MACD** | 12, 26, 9 | 动量方向、金叉死叉 |
| **RSI** | 6, 12, 24 | 超买超卖 |
| **KDJ** | 9, 3, 3 | 短线超买超卖 |
| **BOLL** | 20, 2σ | 波动区间、突破判断 |
| **成交量 MA** | 5, 10 | 量能趋势 |
| **量比** | - | tushare daily_basic |
| **换手率** | - | tushare daily_basic |
| **VWAP** | 日内 | 日内均价参考线 |

### TradingView Lightweight Charts 渲染方案

```
主图 Pane：
  CandlestickSeries  → OHLC K 线
  LineSeries × 4     → MA5 / MA10 / MA20 / MA60
  PriceLine          → 止损线（持仓时显示，红色虚线）
  PriceLine          → 止盈线（持仓时显示，绿色虚线）
  Markers            → AI 买入信号(▲绿) / 卖出信号(▼红)

副图 Pane 1：
  HistogramSeries    → 成交量柱（涨红跌绿）
  LineSeries × 2     → 量 MA5 / 量 MA10

副图 Pane 2：
  HistogramSeries    → MACD 柱（正绿负红）
  LineSeries × 2     → DIF / DEA

副图 Pane 3：
  LineSeries × 3     → RSI6 / RSI12 / RSI24
  价格线             → 超买线(80) / 超卖线(20)
```

---

## 选股模块设计

### 过滤条件（filters.py）

```
基础过滤：
  - 排除 ST / *ST / 退市风险
  - 排除停牌 / 临停
  - 价格区间：如 5-50 元
  - 流通市值区间：如 20亿-300亿

量价过滤：
  - 量比 > 1.5（放量）
  - 换手率 > 2%（活跃）
  - 涨幅区间：如 2%-8%
  - 5日成交额 > 5000 万（流动性）

技术指标过滤：
  - MA 多头排列
  - MACD 金叉或 DIF > 0
  - RSI6 在 40-70 之间
  - 价格在 BOLL 中轨以上
```

### 预设策略（presets.py）

| 策略名 | 说明 | 适合行情 |
|--------|------|---------|
| **趋势突破** | MA 多头排列 + 放量突破近期高点 | 牛市/结构性行情 |
| **缩量回调** | 上升趋势中缩量回踩 MA10/MA20 | 牛市回调买点 |
| **放量异动** | 量比 > 3 + 涨幅 > 3% + 换手率 > 3% | 主力建仓信号 |
| **低位金叉** | MACD 低位金叉 + 价格在 MA20 附近 | 反弹初期 |

---

## A 股市场规则处理

### 必须实现的规则（rules.py）

| 规则 | 处理方式 |
|------|---------|
| **T+1 制度** | 当日买入股票，AI 买入信号自动标注"明日可买入" |
| **涨停板（+10%）** | 买入信号触及涨停价，标注"追涨停风险高" |
| **跌停板（-10%）** | 持仓触及跌停，标注"跌停无法卖出，次日关注" |
| **科创板/创业板 ±20%** | 根据 `market` 字段区分涨跌停幅度 |
| **ST 股 ±5%** | `is_st=1` 时使用 ±5% 计算涨跌停价 |
| **停牌检测** | 实时行情无变化超 30 分钟，标注停牌，跳过分析 |
| **退市风险** | 名称含"退"或交易所公告，加入黑名单 |
| **集合竞价** | 09:15-09:25 不触发正式买卖信号 |
| **午间休市** | 11:30-13:00 暂停轮询，WebSocket 推送暂停状态 |

### 交易时段工具（calendar_util.py）

```python
is_trade_day(date)          # 查询 trade_calendar 表
is_market_open(datetime)    # 09:30-11:30 或 13:00-15:00
is_pre_market(datetime)     # 09:15-09:25 集合竞价
is_after_market(datetime)   # 15:00 之后
get_last_trade_day(date)    # 获取上一个交易日
```

---

## AI 决策设计（Gemini）

### 模型选型与调用策略

| 模型 | 用途 | 触发方式 |
|------|------|---------|
| `gemini-3.1-flash-lite` | 选股扫描后的批量快速筛选 | 自动（每次扫描后 Top10） |
| `gemini-3.1-pro` | 单股深度分析 | 手动（用户点击"AI 分析"按钮） |

> **API Key 获取：** [Google AI Studio](https://aistudio.google.com/) 免费申请。
> **限速处理：** `gemini_client.py` 内置请求队列，控制不超过 15 次/分钟（免费额度）。

### Gemini 输入数据结构（schemas.py）

```json
{
  "stock_code": "000001.SZ",
  "stock_name": "平安银行",
  "analysis_time": "2024-01-15 10:32:00",
  "market_status": "OPEN",
  "quote": {
    "current_price": 12.50,
    "change_pct": 2.3,
    "open": 12.20,
    "high": 12.65,
    "low": 12.10,
    "volume_ratio": 1.8,
    "turnover_rate": 3.2,
    "total_mv_billion": 24.3
  },
  "indicators": {
    "ma5": 12.20, "ma10": 11.80, "ma20": 11.50, "ma60": 10.90,
    "macd_dif": 0.15, "macd_dea": 0.10, "macd_hist": 0.05,
    "rsi6": 65.2, "rsi12": 58.1, "rsi24": 52.4,
    "kdj_k": 72.1, "kdj_d": 65.3, "kdj_j": 85.7,
    "boll_upper": 13.20, "boll_mid": 12.10, "boll_lower": 11.00,
    "ma_trend": "多头排列",
    "macd_signal": "金叉"
  },
  "recent_klines": [
    {"date": "2024-01-14", "open": 11.90, "close": 12.20,
     "volume_ratio": 1.2, "pct_chg": 2.1}
  ],
  "money_flow": {
    "net_mf_amount": 3250.5,
    "buy_lg_amount": 8900.0,
    "sell_lg_amount": 5649.5
  },
  "market_context": {
    "sh_index_pct": 0.8,
    "sz_index_pct": 1.1,
    "north_money_net": 15.3,
    "market_sentiment": "偏强"
  }
}
```

### Gemini 输出数据结构（schemas.py）

```json
{
  "signal": "BUY",
  "confidence": 78,
  "reasoning": "MACD 低位金叉，MA 多头排列趋势清晰，量比 1.8 温和放量，北向资金今日净流入，建议短线跟进。",
  "suggested_buy_price": 12.45,
  "stop_loss_price": 11.82,
  "take_profit_price": 13.50,
  "risk_level": "MEDIUM",
  "hold_days": 3,
  "key_risks": [
    "RSI6 已至 65，短期有超买压力",
    "大盘若转弱需及时止损"
  ]
}
```

### Prompt 设计原则（prompts.py）

```
System Prompt（角色设定）：
  你是专业的 A 股短线趋势交易分析师，专注 1-5 天持仓的波段操作。
  遵守以下原则：
  1. A 股 T+1 制度：买入信号标注次日可操作
  2. 趋势为王：不做逆势操作，不猜底部
  3. 量价配合：无量上涨不追高
  4. 风控优先：宁可错过，不可亏损超止损线
  5. 输出必须是严格 JSON 格式，不添加任何额外文字

User Prompt：
  请分析以下股票数据，给出短线交易建议：
  {股票数据 JSON}
  signal 只能是 BUY / SELL / HOLD / WATCH，confidence 为 0-100 整数
```

---

## 风控引擎设计

### 默认风控参数（可在设置页面调整）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| **单笔最大亏损** | -5% | 触及立即推送止损提醒 |
| **移动止损回撤** | -3% | 从持仓最高点回撤 3% 触发 |
| **单日最大亏损熔断** | -3% | 当日总资产亏损达 3% 暂停新信号 |
| **单只股票仓位上限** | 30% | 单只不超过总资金 30% |
| **最大同时持仓数** | 5 只 | 超过 5 只不发新建仓信号 |
| **止盈目标（参考）** | +8% ~ +15% | AI 提供具体价位 |
| **时间止损** | 5 天 | 持仓超 5 天未达目标，提醒评估 |

### 仓位计算

```
固定比例法（默认）：每笔建仓 = 总资金 × 20%

风险金额法：
  每笔建仓 = (总资金 × 1% 允许亏损) ÷ 5% 止损幅度
           = 总资金 × 20%
```

---

## 通知方案

### 主要：企业微信 Webhook（推荐）

```
配置步骤：
1. 企业微信 → 创建内部群 → 添加"群机器人" → 复制 Webhook URL
2. 填入 .env WECOM_WEBHOOK_URL
3. 支持 Markdown 格式，手机端实时弹通知，免费

推送场景：
  - AI 发出 BUY 信号（置信度 > 70）
  - 持仓触及止损线
  - 持仓触及止盈目标
  - 选股扫描发现高分标的（综合分 > 80）
  - 大盘熔断警告
```

### 备选：浏览器桌面通知（useNotification.ts）

```
浏览器 Notification API：页面打开时有效，弹出系统桌面通知
用途：补充企业微信之外的本地即时提醒
```

### 备用：SMTP 邮件

```
用于：企业微信不可用时的备份
配置：Gmail / QQ 邮件 SMTP
```

---

## 打包与部署方案

### 本地开发运行

```bash
# 启动后端
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 启动前端（另一个终端）
cd frontend
npm run dev         # Vite 开发服务器 localhost:5173
                    # 配置 vite.config.ts proxy → localhost:8000
```

### 生产打包流程（scripts/build.py）

```
Step 1: 前端构建
  cd frontend && npm run build
  → 生成 frontend/dist/（静态文件）

Step 2: 复制 dist 到后端
  cp -r frontend/dist backend/static/

Step 3: FastAPI 挂载静态文件（main.py）
  app.mount("/", StaticFiles(directory="static", html=True))
  → 访问 http://localhost:8000 直接加载 Vue 应用

Step 4: PyInstaller 打包
  pyinstaller --name StockAIAnalyzer
              --add-data "static:static"
              --add-data "db:db"
              backend/main.py
  → 生成 dist/StockAIAnalyzer/ 文件夹

Step 5: 一键启动脚本（scripts/start.py）
  启动 uvicorn → 等待 2 秒 → 自动打开浏览器
  → 双击 start.py 即可使用
```

### 分发包结构

```
StockAIAnalyzer/
├── StockAIAnalyzer.exe   # 主程序
├── static/               # Vue 前端构建产物
├── db/                   # 数据库（首次运行自动初始化）
├── logs/                 # 日志（运行时生成）
├── .env                  # 用户填写 API Key（首次运行引导配置）
└── start.bat             # 双击启动快捷方式
```

---

## 4 周实施计划

### Week 1：项目骨架 + 数据层

**目标：** FastAPI 服务启动，数据能获取并正确存入 SQLite

| # | 任务 | 文件 | 验收标准 |
|---|------|------|----------|
| 1 | 项目目录初始化 | 根目录结构 | `backend/` `frontend/` `scripts/` 目录创建完成 |
| 2 | Python 依赖安装 | `requirements.txt` | `pip install -r requirements.txt` 无报错 |
| 3 | `.env` 配置管理 | `config.py` + `.env.example` | tushare token / Gemini Key 可从环境变量读取 |
| 4 | 数据库建表 | `data/schema.py` | 执行后 `db/` 下生成 SQLite，所有表结构正确 |
| 5 | SQLAlchemy 封装 | `data/storage.py` | Session 管理、增删查改方法可用 |
| 6 | 交易日历工具 | `data/calendar_util.py` | 能判断今天是否交易日、当前是否交易时段 |
| 7 | tushare 客户端 | `data/tushare_client.py` | 日线/分钟线/龙虎榜/北向资金全部可拉取 |
| 8 | 实时行情客户端 | `data/realtime_client.py` | 腾讯 API 返回个股/指数/板块实时数据 |
| 9 | 增量更新调度 | `data/updater.py` | APScheduler 盘后批量拉取，盘中 3 分钟轮询 |
| 10 | FastAPI 主入口 | `backend/main.py` | `uvicorn main:app` 启动成功，`/docs` 可访问 |
| 11 | 基础 API 接口 | `api/routes/market.py` | `GET /api/market/indices` 返回真实指数数据 |
| 12 | 日志配置 | `backend/main.py` | loguru 写入 `logs/app.log`，按天滚动 |

**里程碑：** `curl http://localhost:8000/api/market/indices` 返回真实大盘数据

---

### Week 2：Vue 前端 + K 线图 + 行情看板

**目标：** 浏览器能看到完整行情界面，K 线图正常渲染，实时数据刷新

| # | 任务 | 文件 | 验收标准 |
|---|------|------|----------|
| 1 | Vue 3 + Vite 初始化 | `frontend/` | `npm run dev` 启动成功 |
| 2 | Element Plus + 路由 + Pinia | `router/` `stores/` | 路由切换正常，状态管理可用 |
| 3 | Axios 请求封装 | `api/http.ts` | 统一 baseURL，请求/响应拦截器 |
| 4 | WebSocket Composable | `composables/useWebSocket.ts` | 连接后端 ws，断线自动重连 |
| 5 | 后端 WebSocket 推送 | `api/websocket.py` | 每 3 分钟广播行情快照给所有连接客户端 |
| 6 | 市场看板页面 | `views/DashboardView.vue` | 指数/涨幅榜/板块数据正确展示 |
| 7 | 实时行情表格 | `components/tables/QuoteTable.vue` | 涨红跌绿渲染，数据 3 分钟自动刷新 |
| 8 | 板块热力图 | `components/charts/SectorHeatmap.vue` | ECharts 热力图展示板块涨跌 |
| 9 | TradingView K 线组件 | `components/charts/KlineChart.vue` | K 线 + MA + 成交量 + MACD + RSI 分图 |
| 10 | K 线后端接口 | `api/routes/kline.py` | 返回含指标值的 K 线 JSON 数据 |
| 11 | K 线分析页面 | `views/KlineView.vue` | 搜索股票 → 加载 K 线图，周期切换正常 |
| 12 | 技术指标计算 | `indicators/calculator.py` `signals.py` | pandas-ta 计算全部指标，信号识别正确 |

**里程碑：** 浏览器打开可看到实时行情看板，点击股票能显示完整 K 线图

---

### Week 3：AI 决策 + 选股 + 风控 + 通知

**目标：** AI 能给出结构化建议，选股功能完整，风控规则生效，手机收到推送

| # | 任务 | 文件 | 验收标准 |
|---|------|------|----------|
| 1 | Gemini 客户端 | `ai/gemini_client.py` | 调用 Gemini API，含限速队列/重试/超时处理 |
| 2 | AI 数据结构 | `ai/schemas.py` | pydantic 模型定义输入输出，含完整校验 |
| 3 | Prompt 模板 | `ai/prompts.py` | flash-lite 快速模板 + pro 深度模板 |
| 4 | AI 分析主逻辑 | `ai/analyzer.py` | 组装数据 → 调 Gemini → 解析 JSON → 存库 |
| 5 | AI API 接口 | `api/routes/ai.py` | `POST /api/ai/analyze` 返回结构化信号 |
| 6 | AI 信号页面 | `views/AIView.vue` | 历史信号列表 + 详情卡片展示 |
| 7 | A 股规则模块 | `risk/rules.py` | 涨跌停/T+1/停牌判断全部正确 |
| 8 | 风控引擎 | `risk/engine.py` | 仓位上限/日亏损熔断/黑名单生效 |
| 9 | 止损止盈 | `risk/stop_loss.py` | 固定止损/移动止损/时间止损定时检查 |
| 10 | 选股过滤器 | `screener/filters.py` | 条件可灵活组合 |
| 11 | 全市场扫描 | `screener/scanner.py` | 扫描 5500 只股票耗时 < 30 秒 |
| 12 | 选股 API + 页面 | `api/routes/screener.py` + `ScreenerView.vue` | 条件配置 → 扫描 → 结果表格 → 双击跳 K 线 |
| 13 | 通知模块 | `notifications/sender.py` | 企业微信 Webhook 推送成功，邮件备份可用 |
| 14 | 风控面板组件 | `components/panels/RiskPanel.vue` | 实时显示仓位状态/今日盈亏/熔断提示 |

**里程碑：** AI 分析 10 秒内返回，手机企业微信收到推送，选股结果准确

---

### Week 4：持仓管理 + 回测 + 打包部署

**目标：** 持仓管理闭环完整，策略可回测，程序可打包在无 Python 环境运行

| # | 任务 | 文件 | 验收标准 |
|---|------|------|----------|
| 1 | 持仓管理逻辑 | `portfolio/manager.py` | 录入/平仓/盈亏计算（含手续费/印花税） |
| 2 | 复盘统计 | `portfolio/review.py` | 胜率/盈亏比/最大回撤/最大连亏次数正确 |
| 3 | 持仓 API 接口 | `api/routes/portfolio.py` | CRUD 接口全部可用 |
| 4 | 持仓页面 | `views/PortfolioView.vue` | 汇总卡 + 持仓表 + 净值曲线 + 复盘统计 |
| 5 | 账户净值曲线 | `components/charts/EquityCurve.vue` | ECharts 折线图，含回撤标注 |
| 6 | 回测引擎 | `backtest/engine.py` | 手续费 0.025%×2 + 印花税 0.1% 卖出，滑点模拟 |
| 7 | 仿真盘 | `backtest/simulator.py` | 虚拟 10 万跟踪 AI 信号，不影响真实持仓 |
| 8 | 回测 API + 页面 | `api/routes/backtest.py` + `BacktestView.vue` | 参数配置 → 执行 → 资金曲线 + 回测报告 |
| 9 | 设置页面 | `views/SettingsView.vue` | API Key / 风控参数 / 通知 URL 可视化配置 |
| 10 | 前端构建配置 | `vite.config.ts` `backend/main.py` | `npm run build` → FastAPI 正确挂载静态文件 |
| 11 | 一键启动脚本 | `scripts/start.py` | 启动后端 2 秒后自动打开浏览器 |
| 12 | 打包脚本 | `scripts/build.py` | PyInstaller 生成可分发文件夹，无 Python 可运行 |
| 13 | 首次启动引导 | `backend/main.py` | 检测 .env 缺失时返回配置引导页面 |

**里程碑：** 完整回测一次生成报告，程序打包后在干净 Windows 上双击可运行

---

## 依赖清单

### requirements.txt（Python 后端）

```
# Web 框架
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
websockets>=12.0

# 数据源
tushare>=1.2.89
akshare>=1.12.0
requests>=2.31.0

# 数据处理
pandas>=2.0.0
numpy>=1.24.0
pandas-ta>=0.3.14b

# AI 引擎
google-genai>=1.0.0

# 数据库
SQLAlchemy>=2.0.0

# 数据验证
pydantic>=2.0.0

# 任务调度
APScheduler>=3.10.0

# 配置管理
python-dotenv>=1.0.0

# 日志
loguru>=0.7.0

# 打包（开发环境）
pyinstaller>=6.0.0
```

### package.json（Vue 前端）

```json
{
  "name": "stock-ai-analyzer-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.0",
    "element-plus": "^2.7.0",
    "@element-plus/icons-vue": "^2.3.0",
    "lightweight-charts": "^5.1.0",
    "echarts": "^5.5.0",
    "vue-echarts": "^7.0.0",
    "axios": "^1.7.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "typescript": "^5.4.0",
    "vue-tsc": "^2.0.0",
    "@types/node": "^20.0.0"
  }
}
```

---

## .env.example（配置模板）

```
# tushare API Token（从 tushare.pro 获取）
TUSHARE_TOKEN=your_tushare_token_here

# Google Gemini API Key（从 https://aistudio.google.com/ 获取）
GEMINI_API_KEY=your_gemini_api_key_here

# 默认快速模型（选股扫描）
GEMINI_MODEL_FAST=gemini-3.1-flash-lite

# 深度分析模型（手动触发）
GEMINI_MODEL_PRO=gemini-3.1-pro

# 企业微信群机器人 Webhook URL
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# 邮件备份（可选）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
NOTIFY_EMAIL=your_email@gmail.com

# 服务配置
HOST=127.0.0.1
PORT=8000

# 数据刷新间隔（秒）
POLL_INTERVAL=180

# 数据库路径
DB_PATH=db/stock_analyzer.db
```

---

## 非功能性需求

| 项目 | 要求 |
|------|------|
| **行情刷新响应** | WebSocket 推送到前端更新 < 2 秒 |
| **AI 分析响应** | flash-lite < 5 秒，pro < 15 秒 |
| **选股扫描耗时** | 全市场扫描 < 30 秒 |
| **K 线图加载** | 日线数据加载渲染 < 1 秒 |
| **内存占用** | 后端正常运行 < 300MB |
| **离线可用性** | 有历史数据时无网络也可查看 K 线和持仓 |
| **API 失败处理** | 任一接口超时自动重试 3 次，失败记录日志不崩溃 |
| **数据存储上限** | 分钟线保留 60 天，实时快照保留 7 天，自动清理 |
| **API 调用频控** | Gemini 内置队列，不超过 15 次/分钟 |
| **前端兼容性** | Chrome / Edge 最新两个版本 |

---

## 合规与免责

> **重要提醒：**
> - 本软件仅供**个人学习/研究**使用
> - AI 分析结果为算法建议，**不构成任何投资建议**
> - A 股存在涨跌停、T+1、流动性风险
> - 实盘交易风险自担，盈亏自负
> - 开发者不对使用本软件造成的任何损失承担责任
> - 请遵守您所在地区的法律法规及交易所相关规定

---

## 项目状态

| 项目 | 状态 |
|------|------|
| 需求分析 | ✅ 完成 |
| 技术选型 | ✅ 完成（v3.0 切换为 FastAPI + Vue） |
| 数据源测试 | ✅ 完成 |
| 数据库 Schema 设计 | ✅ 完成 |
| API 接口设计 | ✅ 完成 |
| 前端页面设计 | ✅ 完成 |
| AI 输入/输出结构设计 | ✅ 完成 |
| 技术指标体系 | ✅ 完成 |
| 选股模块设计 | ✅ 完成 |
| 风控参数量化 | ✅ 完成 |
| A 股规则梳理 | ✅ 完成 |
| 打包部署方案 | ✅ 完成 |
| 4 周开发规划 | ✅ 完成 |
| 代码开发 | ⏳ 待开始 |

---

*文档创建时间：2026-04-14*
*最后更新：v3.0 架构切换为 FastAPI + Vue 3*
# 保險推薦代理（Insurance Recommendation Agent）

這是一個以 **Google ADK**、**MCP Toolbox for Databases**、**ToolboxToolset**、**tools.yaml**、**SQLite** 與 **Vertex AI** 建立的保險推薦代理原型專案。

本專案示範如何透過 **MCP Toolbox 的 YAML 配置方式**，建立可被 Agent 調用的保險專用工具，並完成一個具備互動追問、商品篩選、規則解釋與保守聲明的初步保險推薦流程。

---

## 專案目標

本專案的目標是建立一個可互動的保險推薦代理，能夠：

- 在使用者資訊不足時先追問
- 根據年齡、預算、保障目標篩選商品
- 透過 MCP Toolbox 提供的保險專用工具查詢資料
- 說明推薦原因與規則依據
- 補充等待期、除外條款與限制
- 提供可追溯的工具呼叫流程
- 以保守方式輸出初步商品建議

---

## 最終架構

本專案採用以下架構：

```text
使用者
-> Google ADK Agent
-> ToolboxToolset
-> MCP Toolbox
-> tools.yaml
-> SQLite insurance.db
```

---

## 技術組成

* **Google ADK**：負責 Agent 對話流程、追問、工具選擇與最終回答生成
* **ToolboxToolset**：作為 ADK 與 MCP Toolbox 間的橋接層
* **MCP Toolbox for Databases**：負責載入 `tools.yaml`，提供保險專用工具
* **tools.yaml**：集中定義 `source`、`tool`、`toolset`、`prompt`
* **SQLite**：存放保險商品、推薦規則、示範用戶與 FAQ
* **Vertex AI**：提供模型推理能力
* **Docker**：啟動 MCP Toolbox Server

---

## 專案目錄結構

```text
insurance-recommendation-agent/
├─ app/
│  ├─ __init__.py
│  ├─ agent.py
│  └─ prompts/
│     └─ insurance_agent_prompt.txt
├─ db/
│  ├─ schema.sql
│  ├─ seed.sql
│  ├─ insurance.db
│  └─ tools.yaml
├─ tests/
│  ├─ test_cases.md
│  └─ test_insurance_tools.py
├─ docs/
│  ├─ architecture.md
│  ├─ prompt_tool_contract.md
│  ├─ limitations.md
│  └─ demo_script.md
├─ .env
├─ requirements.txt
└─ README.md
```

---

## 核心設計概念

### 1. ADK Agent

ADK Agent 負責：

* 接收使用者需求
* 判斷是否缺少必要資訊
* 決定應使用哪一個保險工具
* 整合工具輸出並生成最終推薦結果

### 2. ToolboxToolset

ToolboxToolset 負責：

* 讓 ADK Agent 透過 MCP 協定連接 MCP Toolbox
* 將 Toolbox 中定義好的工具暴露給 Agent 使用

### 3. MCP Toolbox

MCP Toolbox 負責：

* 載入 `tools.yaml`
* 註冊資料來源、工具、工具群組與 prompts
* 執行受控的資料查詢工具

### 4. tools.yaml

`tools.yaml` 是本專案的工具配置中心，負責定義：

* `source`：資料來源
* `tool`：保險查詢工具
* `toolset`：工具分組
* `prompt`：可重用的提示模板

### 5. SQLite

SQLite 資料庫目前存放：

* `insurance_products`
* `recommendation_rules`
* `user_profiles_demo`
* `faq_knowledge`

---

## 目前已定義的保險專用工具

本專案目前透過 `tools.yaml` 定義以下工具：

* `search_medical_products`
* `search_accident_products`
* `search_family_protection_products`
* `search_income_protection_products`
* `get_product_detail`
* `get_recommendation_rules`

---

## 目前已定義的 Toolbox Prompts

本專案目前在 `tools.yaml` 中定義以下 prompts：

* `insurance_recommendation_response_template`
* `insurance_followup_question_template`

這些 prompts 用來補強：

* 保守式推薦輸出格式
* 資訊不足時的追問方式

---

## 執行方式

### 1. 啟用虛擬環境

```bash
source .venv/bin/activate
```

### 2. 啟動 MCP Toolbox

```bash
docker run --rm --name insurance-toolbox -p 5000:5000 \
  -v "$(pwd)/db:/workspace/db" \
  us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:1.1.0 \
  -a 0.0.0.0 \
  --config /workspace/db/tools.yaml
```

### 3. 啟動 ADK 開發介面

```bash
adk web
```

### 4. 開啟瀏覽器

前往：

```text
http://127.0.0.1:8000
```

---

## 測試輸入範例

### 範例一：醫療保障

```text
我 30 歲，年度保險預算 15000，想加強醫療保障，有什麼推薦？
```

### 範例二：資訊不足

```text
我想買保險，幫我推薦。
```

### 範例三：家庭保障

```text
我 42 歲，已婚有小孩，年度預算 30000，想補家庭保障。
```

### 範例四：收入中斷保障

```text
我 38 歲，已婚有小孩，年度預算 25000，想加強收入中斷風險保障。
```

---

## 目前能力

本專案目前已可做到：

* 在資訊不足時先追問
* 根據保障目標選擇對應 YAML 工具
* 依年齡、預算與需求篩選保險商品
* 說明推薦原因與規則依據
* 補充等待期與除外條款
* 於 ADK trace 中看到可追溯的工具呼叫流程
* 避免使用自由 SQL 作為主要推薦方式
* 透過 `tools.yaml + ToolboxToolset` 完成完整整合設計

---

## Prompt 與 Tool 的分工原則

### Agent Prompt 負責

* 判斷是否需要追問
* 判斷該選哪個保險專用工具
* 決定如何整理與解釋結果
* 確保最終輸出語氣保守且合規

### Toolbox Tools 負責

* 提供受控且可測試的資料查詢能力
* 回傳商品候選清單
* 回傳商品細節
* 回傳推薦規則依據

### 分工邊界

* **Agent 不應自由產生任意 SQL**
* **Toolbox 不負責決定最終推薦話術**
* **Agent 負責解釋，Toolbox 負責受控資料存取**

---

## 已知限制

目前專案仍有以下限制：

1. 商品資料為示範用途，非真實保險商品
2. 尚未實作正式核保流程
3. 保費邏輯仍為簡化版本
4. 推薦規則涵蓋範圍有限
5. 尚未加入 production 級安全限制
6. 尚未加入 embedding / semantic retrieval 功能
7. 目前互動介面仍以 ADK Dev UI 為主

---

## 後續可擴充方向

建議後續可依序擴充：

1. 補強 `tools.yaml` 的場景工具
2. 加入 FAQ 語意檢索
3. 加入條款與除外責任檢索
4. 補強 `allowed-origins` 與 `allowed-hosts`
5. 擴充測試矩陣與驗收案例
6. 切換到正式資料源
7. 增加前端互動介面

---

## 免責聲明

本專案僅用於原型設計、學習與系統架構示範。

所有保險推薦結果僅供初步商品篩選，實際投保仍需以商品條款、健康告知與核保結果為準。

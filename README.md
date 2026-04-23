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
* **MCP Toolbox for Databases**：負責載入 `tools.yaml`，提供保險專用工具與 prompts
* **tools.yaml**：集中定義 `source`、`tool`、`toolset`、`prompt`
* **SQLite**：存放保險商品、推薦規則、示範用戶與 FAQ
* **Vertex AI**：提供模型推理能力
* **Docker**：啟動 MCP Toolbox Server

---

## 專案目錄結構

```text
insurance-recommendation-agent/
├── Makefile
├── README.md
├── app
│   ├── __init__.py
│   ├── agent.py
│   ├── prompts
│   │   └── insurance_agent_prompt.txt
│   └── tools
│       └── insurance_tools.py
├── data
├── db
│   ├── insurance.db
│   ├── schema.sql
│   ├── seed.sql
│   └── tools.yaml
├── docker-compose.yml
├── docs
│   ├── architecture.md
│   ├── demo_script.md
│   ├── embedding.md
│   ├── limitations.md
│   ├── prompt_tool_contract.md
│   └── summary.md
├── pyproject.toml
├── tests
│   ├── test_cases.md
│   └── test_insurance_tools.py
└── uv.lock
```

---

## 核心設計概念

### 1. Google ADK Agent

ADK Agent 負責整體互動流程編排（orchestration），包含：

* 接收使用者需求
* 判斷是否缺少必要資訊
* 決定應使用哪一個保險專用工具
* 視情況補查商品細節或推薦規則
* 整合工具結果並生成最終回覆

ADK Agent 的責任是「何時問、何時查、如何整合」，而不是直接進行自由資料庫查詢。

---

### 2. ToolboxToolset

ToolboxToolset 負責：

* 讓 ADK Agent 透過 MCP 協定連接 MCP Toolbox
* 將 MCP Toolbox 中定義的工具與 prompts 暴露給 Agent 使用
* 作為 ADK 與 Toolbox 配置層之間的橋接介面

---

### 3. MCP Toolbox

MCP Toolbox 負責：

* 載入 `tools.yaml`
* 註冊 `source`、`tool`、`toolset`、`prompt`
* 提供可被 Agent 調用的保險專用工具
* 提供可重用的 prompt 模板資產

MCP Toolbox 的角色是「受控工具與模板供應層」，不直接負責最終推薦話術編排。

---

### 4. tools.yaml

`tools.yaml` 是本專案的配置中心，負責集中管理：

* `source`：資料來源
* `tool`：保險專用查詢工具
* `toolset`：工具分組
* `prompt`：可重用的對話模板

本專案以 `tools.yaml` 作為主要整合核心，而不是讓 Agent 直接自由產生 SQL。

---

### 5. SQLite

SQLite 資料庫目前存放：

* `insurance_products`
* `recommendation_rules`
* `user_profiles_demo`
* `faq_knowledge`

SQLite 作為目前的原型資料層，提供商品、規則與示範資料。

---

## 目前已定義的保險專用工具

本專案目前透過 `tools.yaml` 定義以下工具：

* `search_medical_products`
* `search_accident_products`
* `search_family_protection_products`
* `search_income_protection_products`
* `get_product_detail`
* `get_recommendation_rules`

這些工具的角色如下：

* `search_medical_products`：依年齡與預算查詢醫療保障商品
* `search_accident_products`：依年齡與預算查詢意外保障商品
* `search_family_protection_products`：依年齡與預算查詢家庭保障候選商品
* `search_income_protection_products`：依年齡與預算查詢收入中斷風險保障候選商品
* `get_product_detail`：查詢單一商品細節，如等待期、除外條款、適用年齡與保費範圍
* `get_recommendation_rules`：查詢與保障目標相關的推薦規則依據

---

## 目前已定義的 Toolbox Prompts

本專案目前在 `tools.yaml` 中定義以下 prompts：

* `insurance_followup_question_template`
* `insurance_recommendation_response_template`
* `insurance_disclaimer_template`

這些 prompts 的用途如下：

* `insurance_followup_question_template`：當使用者資訊不足時，用於生成自然、簡潔、友善的追問內容
* `insurance_recommendation_response_template`：用於整理推薦輸出的基本結構，例如推薦商品名稱、推薦原因、限制與條款提醒
* `insurance_disclaimer_template`：用於統一附加保守聲明，確保輸出符合原型設計的合規邊界

這些 prompts 屬於「可重用模板資產」，不負責查詢資料，而是協助 Agent 以一致方式組織回覆。

---

## 執行方式

### 安裝依賴

一般執行模式：

```bash
make install
```

若要執行 ADK evals，請安裝 eval optional dependency group：

```bash
make install-eval
```

若已建立 `.venv`，也可改用：

```bash
make sync-eval
```

### 1. 啟用虛擬環境

```bash
source .venv/bin/activate
```

### 2. 啟動 MCP Toolbox

```bash
make toolbox-up
```

### 3. 啟動 ADK 開發介面

```bash
make run
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
* 透過推薦規則補充解釋依據
* 補充等待期與除外條款
* 使用 Toolbox prompts 提升追問與推薦輸出的一致性
* 於 ADK trace 中看到可追溯的工具呼叫流程
* 避免使用自由 SQL 作為主要推薦方式
* 透過 `tools.yaml + ToolboxToolset` 完成完整整合設計

---

## Prompt 與 Tool 的分工原則

本專案採用以下分工原則：

### 1. Agent Prompt 負責行為編排

`app/prompts/insurance_agent_prompt.txt` 主要負責：

* 判斷是否需要追問
* 判斷應選擇哪一個保險專用工具
* 決定何時補查商品細節或規則依據
* 規範整體互動流程與禁止事項

也就是說，Agent Prompt 負責「行為 orchestration」，而不是直接提供資料。

---

### 2. Toolbox Prompts 負責可重用話術模板

`tools.yaml` 中定義的 prompts 主要負責：

* 缺少資訊時的追問模板
* 推薦結果的輸出模板
* 最後的保守聲明模板

這些 prompts 屬於「可重用語言模板」，用來提升不同場景下的輸出一致性。

---

### 3. Toolbox Tools 負責受控資料存取

`tools.yaml` 中定義的 tools 主要負責：

* 提供受控且可測試的資料查詢能力
* 回傳商品候選清單
* 回傳商品細節
* 回傳推薦規則依據

Tools 的責任是「查資料、回資料」，不是決定最終推薦話術。

---

### 4. 分工邊界

本專案遵守以下邊界：

* **Agent 不應自由產生任意 SQL**
* **Toolbox Tools 不負責最終推薦文案編排**
* **Toolbox Prompts 不負責資料查詢**
* **Agent 負責解釋與整合，Toolbox 負責受控存取與模板資產**

這樣的設計可讓 Agent 行為、工具能力與模板資產清楚分離，提升可維護性與可測試性。

---

## 推薦流程中的責任分配

在一次完整推薦流程中，各層責任如下：

1. **Agent**

   * 判斷使用者資訊是否足夠
   * 若不足，觸發追問邏輯
   * 若足夠，選擇對應的保險專用工具

2. **Toolbox Tools**

   * 根據年齡、預算、保障目標查詢候選商品
   * 回傳商品細節與推薦規則依據

3. **Toolbox Prompts**

   * 協助 Agent 以一致格式提出追問
   * 協助 Agent 以一致格式整理推薦內容與聲明

4. **Agent**

   * 根據工具結果與模板資產整合成最終回覆
   * 確保輸出保守、可追溯、不可虛構

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

1. 補強 `tools.yaml` 的場景工具與 toolsets 分工
2. 擴充 Toolbox prompts，建立更多標準化輸出模板
3. 加入 FAQ 語意檢索
4. 加入條款與除外責任檢索
5. 補強 `allowed-origins` 與 `allowed-hosts`
6. 擴充測試矩陣與驗收案例
7. 切換到正式資料源
8. 增加前端互動介面

---

## 免責聲明

本專案僅用於原型設計、學習與系統架構示範。

所有保險推薦結果僅供初步商品篩選，實際投保仍需以商品條款、健康告知與核保結果為準。

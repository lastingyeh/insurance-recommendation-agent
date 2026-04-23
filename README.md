# 保險推薦代理（Insurance Recommendation Agent）

這是一個以 Google ADK、MCP Toolbox for Databases、ToolboxToolset、SQLite 與 Vertex AI 建立的保險推薦代理原型專案。

目前專案的核心設計是：

- 由 ADK Agent 負責對話流程、追問、工具選擇與最終回覆整合
- 由 MCP Toolbox 載入 db/tools.yaml，提供受控的保險查詢工具與 prompt 模板
- 由 SQLite 提供示範商品、推薦規則與 FAQ 資料
- 透過 Makefile 統一管理安裝、資料庫初始化、啟動與 eval 指令

本專案聚焦在「可追溯、可測試、避免自由 SQL」的保險推薦流程，而不是完整投保系統。

---

## 專案目標

此原型目前的目標是驗證以下能力：

- 在使用者資訊不足時先追問
- 根據年齡、預算與主要保障目標挑選對應工具
- 透過 MCP Toolbox 執行受控資料查詢
- 整合推薦原因、規則依據、等待期與除外條款提醒
- 在回覆中維持保守聲明，不承諾核保、理賠或收益
- 讓工具呼叫流程能在 ADK trace / eval 中被檢驗

---

## 目前架構

```text
使用者
-> Google ADK Agent
-> ToolboxToolset
-> MCP Toolbox
-> db/tools.yaml
-> SQLite insurance.db
```

### 元件責任

- Google ADK Agent：負責互動 orchestration，判斷要追問、查哪個工具、何時補查細節與規則
- ToolboxToolset：作為 ADK 與 MCP Toolbox 間的 MCP 橋接層
- MCP Toolbox：載入 source、tool、toolset、prompt 定義，對外提供工具服務
- db/tools.yaml：集中定義資料來源、保險專用工具、工具群組與 prompt 模板
- SQLite：存放示範商品、推薦規則、demo user profile 與 FAQ

---

## 目前實作狀態

### Agent 執行路徑

目前 app/agent.py 採用以下做法：

- 以 gemini-2.5-flash 作為模型
- 從 app/prompts/insurance_agent_prompt.txt 載入主代理提示詞
- 透過 ToolboxToolset 連接 http://127.0.0.1:5000 的 MCP Toolbox
- 在正式執行路徑中使用 Toolbox 提供的工具，而不是直接把本地 Python helper 註冊成 agent tools

### 本地 Python helper 的角色

app/tools/insurance_tools.py 仍保留一組本地 SQLite helper，主要用途是：

- 提供查詢邏輯的參考實作
- 供本地測試與資料檢查使用
- 幫助比對 YAML 工具與 Python 查詢行為

換句話說，執行中的 Agent 目前主要依賴 MCP Toolbox；本地 Python helper 是輔助與測試資產，不是主要 runtime tool surface。

---

## 專案目錄

```text
insurance-recommendation-agent/
├── .env
├── .env.example
├── Makefile
├── README.md
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── prompts/
│   │   └── insurance_agent_prompt.txt
│   └── tools/
│       └── insurance_tools.py
├── data/
├── db/
│   ├── insurance.db
│   ├── schema.sql
│   ├── seed.sql
│   └── tools.yaml
├── docker-compose.yml
├── docs/
│   ├── architecture.md
│   ├── demo_script.md
│   ├── embedding.md
│   ├── governance.md
│   ├── limitations.md
│   ├── prompt_tool_contract.md
│   └── summary.md
├── pyproject.toml
├── tests/
│   ├── evals/
│   │   ├── case_09_system_capability.test.json
│   │   ├── case_10_no_guarantee.test.json
│   │   ├── case_11_rule_explanation.test.json
│   │   ├── case_12_product_detail_follow_up.test.json
│   │   ├── case_13_no_investment_return.test.json
│   │   ├── insurance_case12_only.test.json
│   │   ├── insurance_core.test.json
│   │   ├── insurance_extended.test.json
│   │   ├── insurance_safety.test.json
│   │   └── test_config.json
│   ├── test_cases.md
│   ├── test_insurance_tools.py
│   └── test_result_template.md
├── uv.lock
└── insurance_recommendation_agent.egg-info/
```

---

## 技術組成

- Google ADK：負責 agent 建立、工具調用與 eval 執行
- ToolboxToolset：讓 ADK Agent 透過 MCP 協定使用 Toolbox 中的工具
- MCP Toolbox for Databases：載入 YAML 配置，提供 SQLite 查詢工具與 prompt
- SQLite：目前的原型資料層
- Vertex AI：提供 Gemini 模型推理能力
- Docker Compose：啟動 MCP Toolbox 容器
- uv：建立虛擬環境與同步 Python 依賴

---

## 已定義的工具與模板

### Source

- insurance_sqlite

### Tools

- search_medical_products
- search_accident_products
- search_family_protection_products
- search_income_protection_products
- get_product_by_name
- get_product_detail
- get_recommendation_rules

### Toolsets

- insurance_recommendation_tools
- insurance_debug_tools

### Prompts

- insurance_followup_question_template
- insurance_recommendation_response_template
- insurance_disclaimer_template

### 目前工具用途

- search_medical_products：依年齡與年度預算查詢醫療保障商品
- search_accident_products：依年齡與年度預算查詢意外保障商品
- search_family_protection_products：依年齡與年度預算查詢家庭保障候選商品
- search_income_protection_products：依年齡與年度預算查詢收入中斷風險候選商品
- get_product_by_name：當使用者直接提到商品名稱時，先做精準商品查詢
- get_product_detail：補查等待期、除外條款、適用年齡與保費範圍等細節
- get_recommendation_rules：查詢與主要保障目標對應的推薦規則

---

## Agent Prompt 的行為邊界

主提示詞目前定義在 app/prompts/insurance_agent_prompt.txt，核心規則包括：

- 必須先確認是否具備年齡、預算、主要保障目標
- 若資訊不足，先追問，不可直接推薦
- 若資訊足夠，依保障目標選擇對應搜尋工具
- 使用者直接提到商品名稱時，可先使用 get_product_by_name
- 若需要補充商品限制或條款，再使用 get_product_detail
- 若需要解釋推薦依據，再使用 get_recommendation_rules
- 不得承諾保證核保、保證理賠或保證收益

這代表 Agent Prompt 的責任仍是 orchestration，而不是自由資料庫探索。

---

## 資料模型

目前 schema.sql 會建立以下資料表：

- insurance_products：商品主資料
- recommendation_rules：推薦規則與優先順序
- user_profiles_demo：示範用使用者資料
- faq_knowledge：FAQ 知識資料

其中目前推薦流程最直接依賴的是：

- insurance_products
- recommendation_rules

---

## 安裝與執行

### 前置需求

- Python 3.12
- uv
- Docker
- sqlite3
- 已可使用 Vertex AI 的 Google Cloud 環境

### 環境變數

請先建立 .env，至少包含 .env.example 中的設定：

```env
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_LOCATION=your-vertex-region
GOOGLE_GENAI_USE_VERTEXAI=1
```

若使用其他認證方式，請自行確保本機可正確存取 Vertex AI。

### 常用指令

首次安裝：

```bash
make install
```

需要 ADK eval 依賴時：

```bash
make install-eval
```

已經存在 .venv 時同步依賴：

```bash
make sync
```

同步含 eval extra 的依賴：

```bash
make sync-eval
```

檢查執行環境：

```bash
make env-check
```

初始化資料庫：

```bash
make db-init
```

重建資料庫：

```bash
make db-reset
```

啟動 Toolbox：

```bash
make toolbox-up
```

關閉 Toolbox：

```bash
make toolbox-down
```

啟動 ADK Web UI：

```bash
make run
```

以 CLI 模式執行 Agent：

```bash
make run-cli
```

一鍵完成安裝、建庫與啟動 Toolbox：

```bash
make up
```

停止服務：

```bash
make down
```

啟動後可在瀏覽器開啟：

```text
http://127.0.0.1:8000
```

### 建議啟動順序

```bash
make install
make db-init
make toolbox-up
make run
```

---

## 測試與評估

### Python 測試

```bash
make check
```

目前 tests/test_insurance_tools.py 主要用來驗證本地 SQLite helper 的查詢結果。

### ADK evals

核心回歸測試：

```bash
make eval-core
```

Safety 單案例測試：

```bash
make eval-safety
```

或分別執行：

```bash
make eval-safety-case-09
make eval-safety-case-10
make eval-safety-case-11
make eval-safety-case-12
make eval-safety-case-13
```

### Eval 檔案配置

目前主要 eval 檔案位於 tests/evals：

- insurance_core.test.json
- insurance_extended.test.json
- case_09_system_capability.test.json
- case_10_no_guarantee.test.json
- case_11_rule_explanation.test.json
- case_12_product_detail_follow_up.test.json
- case_13_no_investment_return.test.json
- insurance_safety.test.json
- insurance_case12_only.test.json
- test_config.json

目前 test_config.json 的評估標準為：

- tool_trajectory_avg_score：threshold 1.0，match_type 為 IN_ORDER
- final_response_match_v2：threshold 0.7

---

## 推薦流程摘要

1. 使用者輸入需求
2. Agent 判斷是否已有年齡、預算、主要保障目標
3. 若資訊不足，先追問
4. 若資訊足夠，選擇對應的 MCP Toolbox 工具
5. 必要時補查推薦規則與商品細節
6. 整合候選商品、條款提醒與保守聲明，生成最終回覆

---

## 目前能力

- 可在資訊不足時先追問核心欄位
- 可依保障目標切換對應保險工具
- 可查詢商品候選、商品細節與推薦規則
- 可處理使用者直接提及商品名稱的細節追問
- 可在回覆中補充等待期與除外條款提醒
- 可透過 ADK eval 驗證工具使用順序與最終回答品質

---

## 已知限制

目前仍有以下限制：

1. 商品資料為示範用途，非真實保險商品。
2. 尚未實作正式核保流程。
3. 保費邏輯仍屬簡化版本。
4. 推薦規則覆蓋範圍有限。
5. FAQ/embedding 檢索尚未接入正式推薦流程。
6. 本地 Python helper 與 YAML 工具存在雙軌實作，後續仍可再收斂。
7. 目前 UI 以 ADK Web UI 為主，尚未提供獨立前端。

---

## 後續建議方向

1. 將 agent prompt 中已使用的 get_product_by_name 完整反映到更多設計文件與測試案例。
2. 補強 FAQ、條款與除外責任的 retrieval 能力。
3. 讓本地 Python helper 與 MCP YAML 工具的能力邊界更一致。
4. 擴充 eval matrix，覆蓋更多追問、多輪澄清與商品比較情境。
5. 規劃正式前端與更完整的安全/治理設定。

---

## 相關文件

- docs/architecture.md：系統架構與資料流
- docs/prompt_tool_contract.md：Prompt 與 Tool 的分工邊界
- docs/governance.md：治理與限制說明
- docs/limitations.md：限制與後續方向
- docs/demo_script.md：示範對話腳本

---

## 免責聲明

本專案僅用於原型設計、學習與系統架構示範。

所有保險推薦結果僅供初步商品篩選，實際投保仍需以商品條款、健康告知與核保結果為準。

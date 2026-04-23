# 系統架構說明（Architecture）

本文件說明本專案的最終系統架構、元件責任、資料流，以及為什麼採用 `tools.yaml + ToolboxToolset + MCP Toolbox` 的整合方式來完成保險推薦代理。

---

## 一、最終架構總覽

本專案的最終高階架構如下：

```text
使用者
-> Google ADK Agent
-> ToolboxToolset
-> MCP Toolbox
-> tools.yaml
-> SQLite insurance.db
```

這個架構的核心思想是：

* **Agent 不直接自由查資料庫**
* **資料查詢能力由 MCP Toolbox 中的受控工具提供**
* **工具定義集中於 `tools.yaml`**
* **ADK Agent 負責對話、追問、工具選擇與結果解釋**

---

## 二、元件責任分工

### 1. 使用者（User）

使用者負責輸入需求，例如：

* 年齡
* 預算
* 保障目標
* 家庭狀況
* 是否已有保單

使用者輸入可能完整，也可能不完整，因此系統必須具備追問能力。

---

### 2. Google ADK Agent

ADK Agent 是整個系統的對話與決策核心，負責：

* 接收使用者需求
* 判斷資訊是否足夠
* 在資訊不足時先追問
* 根據保障目標選擇正確工具
* 整合工具結果
* 生成最終推薦回覆
* 補充推薦原因、限制、等待期、除外條款與保守聲明

ADK Agent **不應直接產生任意 SQL**，而是透過 MCP Toolbox 提供的受控工具完成資料查詢。

---

### 3. ToolboxToolset

`ToolboxToolset` 是 ADK 與 MCP Toolbox 之間的橋接層，負責：

* 讓 ADK Agent 透過 MCP 協定連接 Toolbox
* 將 Toolbox 中註冊好的 tools 提供給 Agent 使用
* 讓 Agent 在不直接接觸資料庫的情況下呼叫工具

換句話說，`ToolboxToolset` 是 **Agent 看到工具的入口**。

---

### 4. MCP Toolbox

MCP Toolbox 是本專案的工具供應層，負責：

* 載入 `tools.yaml`
* 初始化資料來源（source）
* 初始化保險專用工具（tool）
* 初始化工具群組（toolset）
* 初始化可重用 prompts
* 對外提供 MCP server 介面，供 ADK Agent 使用

MCP Toolbox 的價值在於：

* 工具可集中配置
* 查詢邏輯可受控
* 工具行為可追溯
* 後續更容易切換資料來源或擴充新工具

---

### 5. tools.yaml

`tools.yaml` 是本專案的工具配置中心，負責定義：

* `source`：資料來源
* `tool`：可被 Agent 調用的保險工具
* `toolset`：工具分組
* `prompt`：可重用的提示模板

目前本專案已在 `tools.yaml` 中定義：

#### source

* `insurance_sqlite`

#### tools

* `search_medical_products`
* `search_accident_products`
* `search_family_protection_products`
* `search_income_protection_products`
* `get_product_detail`
* `get_recommendation_rules`

#### toolsets

* `insurance_recommendation_tools`
* `insurance_debug_tools`

#### prompts

* `insurance_recommendation_response_template`
* `insurance_followup_question_template`

---

### 6. SQLite

SQLite 是目前的資料層，負責儲存保險推薦所需資料。

目前主要資料表包括：

* `insurance_products`
* `recommendation_rules`
* `user_profiles_demo`
* `faq_knowledge`

其中最主要會被推薦流程使用的是：

#### insurance_products

存放商品名稱、類型、年齡限制、保費範圍、保障摘要、等待期、除外條款等資料。

#### recommendation_rules

存放推薦規則與規則優先順序，供 Agent 補充推薦依據。

---

## 三、推薦流程（Recommendation Workflow）

本專案的推薦流程如下：

### Step 1：使用者輸入需求

例如：

* 「我 30 歲，年度保險預算 15000，想加強醫療保障，有什麼推薦？」
* 「我想買保險，幫我推薦。」
* 「我 42 歲，已婚有小孩，年度預算 30000，想補家庭保障。」

---

### Step 2：Agent 檢查資訊是否足夠

Agent 先判斷是否已具備以下必要資訊：

* 年齡
* 預算
* 主要保障目標

若缺少其中任一項，Agent 應先追問，而不是直接推薦商品。

---

### Step 3：Agent 選擇對應工具

當資訊足夠時，Agent 會依保障目標選擇對應工具，例如：

* `medical` -> `search_medical_products`
* `accident` -> `search_accident_products`
* `family_protection` -> `search_family_protection_products`
* `income_protection` -> `search_income_protection_products`
* `life` -> `search_family_protection_products`

這樣做的目的是讓工具邊界更清楚，避免讓 Agent 自己決定太多 SQL 細節。

---

### Step 4：查詢候選商品

Agent 透過 ToolboxToolset 呼叫 MCP Toolbox 中對應的工具。

例如家庭保障場景可能會呼叫：

* `search_family_protection_products`
* `get_recommendation_rules`

若需要補商品細節，再呼叫：

* `get_product_detail`

---

### Step 5：Agent 生成推薦回覆

Agent 根據工具輸出內容整理最終回答，通常包含：

* 推薦商品名稱
* 推薦原因
* 預算或條件限制
* 等待期
* 除外條款
* 規則依據
* 保守聲明

---

## 四、這種設計的優點

### 1. 避免自由 SQL

若讓模型自由產生 SQL，會帶來：

* 權限風險
* 查詢不穩定
* 行為不易測試
* 工具邊界模糊

本專案改用 `tools.yaml` 定義受控工具，可有效降低這些問題。

---

### 2. 提高可追溯性

透過 ADK trace，可看到 Agent 實際呼叫了哪些工具，例如：

* `search_medical_products`
* `search_family_protection_products`
* `get_recommendation_rules`

這比單純依賴模型文字輸出更容易驗證。

---

### 3. 提高維護性

當商品搜尋邏輯需要調整時，只需修改：

* `tools.yaml`
* 或底層資料表

而不需要讓 Agent prompt 不斷膨脹。

---

### 4. 提高可測試性

每個工具責任更明確後，測試案例也更容易設計。
例如：

* 醫療保障案例只驗證 `search_medical_products`
* 家庭保障案例驗證 `search_family_protection_products + get_recommendation_rules`
* 收入保障案例驗證 `search_income_protection_products`

---

## 五、Prompt 與 Tool 的邊界

本專案遵守以下原則：

### Agent Prompt 負責

* 判斷是否需要追問
* 決定要用哪個工具
* 解釋工具輸出結果
* 組織最終推薦語言
* 確保語氣保守合規

### Toolbox Tools 負責

* 執行受控資料查詢
* 提供商品候選
* 提供商品細節
* 提供規則依據

### 邊界原則

* **Agent 不負責自由資料存取**
* **Toolbox 不負責最終推薦話術**
* **Agent 負責解釋，Toolbox 負責執行**

---

## 六、目前已驗證的場景

本專案目前至少已驗證以下場景：

### 醫療保障

輸入：

* 30 歲
* 年度預算 15000
* 想加強醫療保障

預期工具：

* `search_medical_products`

---

### 資訊不足

輸入：

* 想買保險，幫我推薦

預期行為：

* 不直接推薦
* 先追問年齡、預算、保障目標

---

### 家庭保障

輸入：

* 42 歲
* 已婚有小孩
* 年度預算 30000
* 想補家庭保障

預期工具：

* `search_family_protection_products`
* `get_recommendation_rules`

---

## 七、目前架構的限制

目前架構仍有以下限制：

1. 商品資料為示範資料，非正式商品資料
2. 尚未接入正式核保流程
3. 尚未加入完整安全控制，例如 `allowed-origins`、`allowed-hosts`
4. 尚未加入 embedding / FAQ semantic retrieval
5. 目前互動仍以 ADK Dev UI 為主
6. 推薦規則仍為第一版原型設計

---

## 八、未來擴充方向

未來可進一步擴充：

### 1. FAQ 與條款語意檢索

利用 embedding 功能建立 FAQ semantic retrieval 與條款檢索能力。

### 2. 更細的場景工具

將目前工具再拆成更細的場景，例如：

* 低預算醫療保障
* 熟齡醫療補強
* 家庭責任強化
* 收入中斷補強

### 3. 正式資料源切換

未來可由 SQLite 切換到正式資料庫，保留相同 Agent 與 Toolbox 設計。

### 4. 前端介面

加入正式前端 UI，讓推薦流程可作為業務或客服支援工具。

---

## 九、結論

本專案的最終架構重點在於：

* 使用 **Google ADK** 管理對話與工具調度
* 使用 **ToolboxToolset** 作為 ADK 與 Toolbox 的橋接
* 使用 **MCP Toolbox + tools.yaml** 提供受控的保險專用工具
* 使用 **SQLite** 提供原型資料來源
* 透過清楚的 Prompt / Tool 邊界，建立可追溯、可測試、可擴充的保險推薦代理

# 最終專案總結

本專案完成了一個以 **Google ADK**、**MCP Toolbox for Databases**、**ToolboxToolset**、**tools.yaml**、**SQLite** 與 **Vertex AI** 為核心的 **保險推薦代理原型**。

本專案的重點，不只是做出一個能回答問題的聊天代理，而是建立一套 **可互動、可追溯、可維護、可擴充** 的 Agent 工具架構，讓保險推薦流程不依賴模型自由產生 SQL，而是透過 **MCP Toolbox 中以 `tools.yaml` 定義的受控工具** 完成商品查詢與規則解釋。

---

## 一、專案最終架構

本專案最終採用以下架構：

```text
使用者
-> Google ADK Agent
-> ToolboxToolset
-> MCP Toolbox
-> tools.yaml
-> SQLite insurance.db
```

各層角色如下：

* **Google ADK Agent**：負責對話流程、追問、工具選擇與最終推薦輸出
* **ToolboxToolset**：負責讓 ADK Agent 透過 MCP 協定連接 MCP Toolbox
* **MCP Toolbox**：負責載入 `tools.yaml` 並提供工具
* **tools.yaml**：集中定義 `source`、`tool`、`toolset`、`prompt`
* **SQLite**：提供保險商品、推薦規則、FAQ 與示範資料

---

## 二、專案完成的核心能力

本專案目前已完成以下能力：

### 1. 互動式需求蒐集

當使用者資訊不足時，Agent 會先追問，而不是直接推薦商品。

例如：

* 年齡
* 預算
* 主要保障目標

---

### 2. 保險專用工具查詢

透過 `tools.yaml` 定義受控工具，而非使用自由 SQL。

目前已完成的工具包括：

* `search_medical_products`
* `search_accident_products`
* `search_family_protection_products`
* `search_income_protection_products`
* `get_product_detail`
* `get_recommendation_rules`

---

### 3. 規則驅動推薦

除了商品查詢外，Agent 還能透過 `get_recommendation_rules` 補充：

* 為什麼推薦這個商品
* 為什麼某些情境優先考慮特定商品類型
* 如何將商品推薦與家庭責任、收入中斷等保障需求連結

---

### 4. 結構化推薦輸出

最終推薦回覆已能穩定包含：

* 推薦商品名稱
* 推薦原因
* 條件限制
* 等待期
* 除外條款
* 規則依據
* 保守聲明

---

### 5. 可追溯工具呼叫流程

透過 ADK trace，可驗證 Agent 實際呼叫了哪些工具，例如：

* `search_medical_products`
* `search_family_protection_products`
* `get_recommendation_rules`

這讓整個推薦流程具備更高的可驗證性。

---

## 三、專案設計上的關鍵成果

本專案最重要的成果，不是單純做出推薦結果，而是完成了以下三個設計轉換：

### 1. 從自由 SQL 轉向受控工具

一開始雖然可透過 prebuilt SQLite 工具執行 `execute_sql`，但最終已收斂為：

* 不使用自由 SQL 作為主推薦機制
* 改以 `tools.yaml` 定義保險專用工具
* 由 Agent 選工具，而不是自己寫 SQL

---

### 2. 從本地 Python tools 轉向 MCP Toolbox YAML 配置

專案中曾先以本地 Python function 驗證推薦流程，之後再完整收斂到：

* `source`
* `tool`
* `toolset`
* `prompt`

都由 `tools.yaml` 統一管理。

這使得系統更接近正式 MCP Toolbox 的配置思維。

---

### 3. 從單一查詢工具轉向場景化工具設計

工具已從單一搜尋工具拆分成不同保障場景，例如：

* 醫療保障
* 意外保障
* 家庭保障
* 收入中斷保障

這讓 Agent 的工具選擇更清楚，也讓每個場景更容易測試與維護。

---

## 四、已完成的專案文件

本專案目前已整理出完整交付文件，包括：

* `README.md`
* `docs/architecture.md`
* `docs/prompt_tool_contract.md`
* `docs/demo_script.md`
* `docs/limitations.md`
* `tests/test_cases.md`

這使得專案不只可執行，也可用於：

* 技術展示
* 團隊分享
* 架構匯報
* 教學使用
* 作品集展示

---

## 五、目前專案的定位

本專案目前最適合的定位是：

* 保險推薦代理 PoC
* MCP Toolbox × ADK 整合示範
* `tools.yaml` 為核心的 Agent 工具架構教學專案
* 後續產品化與語意檢索擴充的基礎版本

它已經是：

* 可運行
* 可測試
* 可展示
* 可驗證
* 可擴充

但仍不是正式上線產品。

---

## 六、目前已知限制

目前專案仍有以下限制：

* 商品資料為示範資料
* 尚未實作正式核保流程
* 保費邏輯為簡化版本
* 規則涵蓋範圍有限
* 尚未加入 production 安全設定
* 尚未加入 embedding / semantic retrieval
* 尚未接正式資料源
* 尚未有正式前端介面

這些限制已在 `docs/limitations.md` 中整理清楚。

---

## 七、下一階段建議方向

若要繼續往下一階段發展，建議優先順序如下：

### 第一階段

* 補強安全設定
* 完善測試矩陣
* 整理最終展示文件

### 第二階段

* 加入 FAQ semantic retrieval
* 加入條款與除外責任語意檢索
* 將 embedding 納入 MCP Toolbox 教學模組

### 第三階段

* 切換正式資料源
* 加入正式前端 UI
* 補齊權限控管與上線架構

---

## 八、專案總結一句話版本

本專案完成了一個以 **`tools.yaml + ToolboxToolset + MCP Toolbox`** 為核心、可透過 **Google ADK** 進行對話與工具調度的 **保險推薦代理原型**，具備追問、商品篩選、規則解釋、保守聲明與可追溯工具呼叫能力，可作為後續產品化與知識檢索擴充的基礎。

---

## 九、專案總結完整版

這個專案的真正價值，不只是「讓模型推薦保險」，而是建立了一個 **清楚分工的 Agent 工具架構**：

* Agent 負責判斷怎麼問、怎麼選、怎麼說
* Toolbox 負責受控地查資料
* `tools.yaml` 負責定義工具能力
* 資料庫只作為資料來源，而不是讓模型自由操作的對象

這樣的設計比起讓模型直接自由查資料，更適合：

* 企業內部 Agent PoC
* 受控資料查詢場景
* 可解釋推薦流程
* 後續產品化擴充

因此，本專案已成功達成最初的核心目標：

> **透過 MCP Toolbox 與 Google ADK，完成一個以 `tools.yaml` 為核心的保險推薦代理完整專案設計。**

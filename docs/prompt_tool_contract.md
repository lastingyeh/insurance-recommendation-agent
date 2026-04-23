# Prompt 與 Tool 分工契約（Prompt / Tool Contract）

本文件說明本專案中 **Google ADK Agent Prompt** 與 **MCP Toolbox Tools** 的責任邊界、分工原則，以及兩者如何協作完成保險推薦流程。

這份文件的目的，是避免 Agent 與 Tool 的責任混淆，讓整個系統更容易：

- 維護
- 測試
- 擴充
- 降低風險

---

## 一、核心原則

本專案採用以下分工原則：

- **Prompt 負責決策與解釋**
- **Tool 負責受控資料存取**
- **Prompt 不直接自由查資料**
- **Tool 不負責最終推薦話術**

也就是說：

> **Agent 負責思考與表達，Toolbox 負責受控執行。**

---

## 二、Prompt 的責任

在本專案中，ADK Agent Prompt 的責任包括：

### 1. 判斷資訊是否足夠
Agent 需要先判斷是否已取得以下必要資訊：

- 年齡
- 預算
- 主要保障目標

若資訊不足，Agent 應先追問，而不是直接推薦商品。

---

### 2. 決定要使用哪一個工具
Prompt 需要根據使用者需求，決定對應的保險專用工具，例如：

- `medical` -> `search_medical_products`
- `accident` -> `search_accident_products`
- `family_protection` -> `search_family_protection_products`
- `income_protection` -> `search_income_protection_products`
- `life` -> `search_family_protection_products`

Prompt 的責任是**選工具**，不是自己實作查詢邏輯。

---

### 3. 解釋工具輸出
Agent 會根據工具回傳的內容，產生最終推薦結果，例如：

- 為什麼推薦這個商品
- 這個商品適合哪類情境
- 有哪些限制
- 有哪些等待期或除外條款
- 哪條規則支撐這次推薦

---

### 4. 控制輸出語氣與風險
Prompt 需要確保最終回答：

- 不虛構資料
- 不承諾保證核保
- 不承諾保證理賠
- 不承諾保證收益
- 保留保守聲明

---

### 5. 整理最終回答格式
Prompt 應控制回覆具備基本結構，例如：

- 使用者需求摘要
- 推薦商品名稱
- 推薦原因
- 條件限制
- 等待期與除外條款
- 規則依據
- 保守聲明

---

## 三、Tool 的責任

本專案中的 MCP Toolbox Tools 負責：

### 1. 提供受控資料查詢能力
Tools 的工作是執行已定義的查詢邏輯，而不是讓 Agent 任意查資料庫。

例如：

- 查符合醫療保障條件的商品
- 查符合家庭保障條件的商品
- 查商品詳細資訊
- 查推薦規則

---

### 2. 回傳結構化資料
Tool 應回傳穩定、可預期的資料結構，例如：

- 商品 ID
- 商品名稱
- 商品類型
- 保費範圍
- 保障摘要
- 等待期
- 除外條款
- 推薦規則

Tool 不應負責最終自然語言包裝。

---

### 3. 維持查詢邏輯的可測試性
由於 Tool 是受控查詢，因此可以獨立驗證：

- 查詢條件是否正確
- 映射是否正確
- SQL 是否穩定
- 回傳格式是否穩定

這讓整個系統比自由 SQL 更容易測試。

---

### 4. 限制行為邊界
Tool 的責任不是「盡可能回答任何問題」，而是：

- 僅在定義範圍內返回資料
- 保持查詢能力清楚
- 避免變成無限制的資料庫入口

---

## 四、目前工具對照表

本專案目前在 `tools.yaml` 中定義的保險工具如下：

### 1. `search_medical_products`
用途：
- 依年齡與預算搜尋醫療保障商品

---

### 2. `search_accident_products`
用途：
- 依年齡與預算搜尋意外保障商品

---

### 3. `search_family_protection_products`
用途：
- 依年齡與預算搜尋家庭保障商品
- 目前主要對應壽險類商品

---

### 4. `search_income_protection_products`
用途：
- 依年齡與預算搜尋收入中斷保障商品
- 目前優先回傳重大疾病與壽險候選商品

---

### 5. `get_product_detail`
用途：
- 查詢單一商品的詳細資料
- 補充等待期、除外條款、年齡範圍與商品摘要

---

### 6. `get_recommendation_rules`
用途：
- 查詢推薦規則
- 補充「為何推薦」的規則依據

---

## 五、Prompt 與 Tool 的邊界定義

### Prompt 不應做的事
Prompt 不應：

- 任意產生 SQL
- 假設資料庫中存在某商品
- 自己捏造等待期、除外條款、規則內容
- 將推理結果誤當作資料事實

---

### Tool 不應做的事
Tool 不應：

- 直接輸出最終推薦話術
- 自己做保守聲明判斷
- 決定最終語氣
- 模擬核保或理賠判斷
- 越界回答超出定義範圍的問題

---

## 六、目前的映射契約

在目前專案中，保障目標與工具選擇的映射如下：

| 使用者保障目標 | Agent 應優先選擇的工具 |
|---|---|
| medical | `search_medical_products` |
| accident | `search_accident_products` |
| family_protection | `search_family_protection_products` |
| income_protection | `search_income_protection_products` |
| life | `search_family_protection_products` |

這個映射屬於 **Prompt 的決策責任**，而不是由 Tool 自行猜測。

---

## 七、典型互動流程

### 情境 A：資訊不足
使用者輸入：

> 我想買保險，幫我推薦。

此時 Prompt 應：

1. 判斷資訊不足
2. 不呼叫推薦工具
3. 先追問：
   - 年齡
   - 預算
   - 主要保障目標

此時 Tool 不應被呼叫。

---

### 情境 B：醫療保障
使用者輸入：

> 我 30 歲，年度保險預算 15000，想加強醫療保障。

此時 Prompt 應：

1. 判斷資訊足夠
2. 選擇 `search_medical_products`
3. 視需要選擇 `get_product_detail`
4. 整理推薦回覆

---

### 情境 C：家庭保障
使用者輸入：

> 我 42 歲，已婚有小孩，年度預算 30000，想補家庭保障。

此時 Prompt 應：

1. 判斷資訊足夠
2. 選擇 `search_family_protection_products`
3. 選擇 `get_recommendation_rules`
4. 視需要選擇 `get_product_detail`
5. 整理推薦回覆

---

## 八、為什麼不讓 Agent 自由產生 SQL

這是本專案最重要的設計原則之一。

若讓 Agent 自由產生 SQL，會有以下問題：

### 1. 安全風險
模型可能查詢不必要的欄位或資料。

### 2. 查詢不穩定
同樣需求可能產生不同 SQL，難以維護與測試。

### 3. 難以驗證
你會很難界定是 Prompt 問題、Tool 問題，還是 SQL 本身問題。

### 4. 工具責任模糊
當模型同時負責選工具、寫 SQL、整理結果時，系統變得不易維護。

因此，本專案採用：

- **YAML 定義受控工具**
- **Prompt 負責決策**
- **Toolbox 負責執行**

這樣的架構更清楚也更穩定。

---

## 九、目前的保守輸出契約

所有最終推薦回覆都應遵守以下輸出原則：

### 必須包含
- 推薦商品名稱
- 推薦原因
- 若有條件限制需提醒
- 若有等待期或除外條款需說明
- 保守聲明

### 不可包含
- 保證核保
- 保證理賠
- 保證收益
- 模型自行捏造的商品資訊

### 固定保守聲明
所有推薦回覆最後應包含：

> 本建議僅供初步商品篩選，實際投保仍需以商品條款、健康告知與核保結果為準。

---

## 十、未來擴充時的分工原則

未來若擴充新能力，仍應維持同樣邊界：

### 若是資料查詢或檢索能力
應優先考慮放進 Toolbox，例如：

- FAQ semantic retrieval
- 條款檢索
- 進階商品搜尋

### 若是對話決策與話術控制
應優先放在 Agent Prompt，例如：

- 追問順序
- 推薦話術
- 保守聲明策略
- 規則解釋方式

---

## 十一、結論

本專案的 Prompt / Tool Contract 可以濃縮成一句話：

> **Prompt 決定怎麼問、怎麼選、怎麼說；Tool 決定怎麼查、查什麼、回什麼。**

透過這樣的分工：

- Agent 能保持靈活
- Tool 能保持受控
- 系統更容易測試與維護
- 後續更容易擴充到 embedding、FAQ retrieval、正式資料源與 production 架構
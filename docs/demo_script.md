# Demo Script（專案展示腳本）

本文件提供一份可直接用於展示本專案的 demo 腳本，適合：

- 專案成果展示
- 內部分享
- 技術簡報
- PoC 匯報
- 面試或作品集說明

本腳本以目前專案的最終架構為基礎：

```text
使用者
-> Google ADK Agent
-> ToolboxToolset
-> MCP Toolbox
-> tools.yaml
-> SQLite insurance.db
```

---

## 一、開場介紹

今天要展示的是一個 **保險推薦代理原型專案**。

這個專案是使用以下技術組成：

* Google ADK
* MCP Toolbox for Databases
* ToolboxToolset
* tools.yaml
* SQLite
* Vertex AI

這個系統的目標不是取代正式保險規劃，而是完成一個 **可互動、可追溯、可解釋的初步商品篩選代理**。

它能做到：

* 在資訊不足時先追問
* 根據年齡、預算與保障需求篩選商品
* 使用 MCP Toolbox 提供的保險專用工具完成查詢
* 說明推薦原因與規則依據
* 補充等待期、除外條款與保守聲明

---

## 二、系統架構說明

本專案採用以下架構：

```text
使用者
-> Google ADK Agent
-> ToolboxToolset
-> MCP Toolbox
-> tools.yaml
-> SQLite insurance.db
```

### 各層分工如下：

#### Google ADK Agent

負責：

* 與使用者互動
* 判斷資訊是否足夠
* 決定要呼叫哪一個保險工具
* 整理工具結果並生成最終回答

#### ToolboxToolset

負責：

* 讓 ADK Agent 透過 MCP 協定連接 MCP Toolbox

#### MCP Toolbox

負責：

* 載入 `tools.yaml`
* 提供已定義好的保險專用工具
* 執行受控資料查詢

#### tools.yaml

負責：

* 定義資料來源
* 定義保險工具
* 定義工具群組
* 定義可重用 prompts

#### SQLite

負責：

* 存放商品資料
* 存放推薦規則
* 存放 FAQ 與示範用戶資料

---

## 三、展示重點

本次 demo 會特別展示三件事：

### 1. 不是自由 SQL

這個系統不是讓模型自由產生 SQL，而是透過 `tools.yaml` 定義受控工具。

### 2. Agent 會追問

若資訊不足，Agent 不會直接推薦商品，而會先追問必要資訊。

### 3. 工具呼叫可追溯

在 ADK trace 中，可以看到 Agent 實際呼叫了哪些保險工具，例如：

* `search_medical_products`
* `search_family_protection_products`
* `search_income_protection_products`
* `get_recommendation_rules`
* `get_product_detail`

---

## 四、展示前準備

在 demo 前，請先確認：

### 1. MCP Toolbox 已啟動

啟動指令：

```bash
docker run --rm --name insurance-toolbox -p 5000:5000 \
  -v "$(pwd)/db:/workspace/db" \
  us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:1.1.0 \
  -a 0.0.0.0 \
  --config /workspace/db/tools.yaml
```

### 2. ADK Dev UI 已啟動

啟動指令：

```bash
adk web
```

### 3. 已可開啟瀏覽器

網址：

```text
http://127.0.0.1:8000
```

### 4. 已確認目前工具已載入

目前應可看到以下工具：

* `search_medical_products`
* `search_accident_products`
* `search_family_protection_products`
* `search_income_protection_products`
* `get_product_detail`
* `get_recommendation_rules`

---

## 五、Demo 情境一：醫療保障（資訊完整）

### 使用者輸入

```text
我 30 歲，年度保險預算 15000，想加強醫療保障，有什麼推薦？
```

### 展示重點

這一題要展示：

* 使用者資訊已足夠
* Agent 不需要追問
* Agent 會直接選擇 `search_medical_products`
* Agent 根據查詢結果推薦商品
* 回答中會補充等待期、除外條款與保守聲明

### 期待結果

推薦商品應為：

* `安心住院醫療方案 A`

### 展示時可講的話

這題代表一個資訊完整的場景。
Agent 已具備年齡、預算與保障目標，因此不需要追問，而是直接呼叫對應的醫療保障工具完成商品篩選。

如果打開 trace，可以看到它使用的是受控的保險工具，而不是自由 SQL。

---

## 六、Demo 情境二：資訊不足

### 使用者輸入

```text
我想買保險，幫我推薦。
```

### 展示重點

這一題要展示：

* Agent 不會直接推薦
* Agent 會先追問必要資訊
* 這時候通常不應呼叫推薦工具

### 預期追問內容

應至少追問：

* 年齡
* 預算
* 主要保障目標

### 展示時可講的話

這題代表一個不完整需求場景。
保險推薦不應在資訊不足時直接輸出商品，因此 Agent 會先蒐集必要資訊，而不是貿然推薦。

這能展示系統具備基本的顧問式互動能力，而不只是單純查資料庫。

---

## 七、Demo 情境三：家庭保障

### 使用者輸入

```text
我 42 歲，已婚有小孩，年度預算 30000，想補家庭保障。
```

### 展示重點

這一題要展示：

* Agent 會選用 `search_family_protection_products`
* Agent 會進一步使用 `get_recommendation_rules`
* 回答中會補充家庭責任與規則依據
* 回答仍保留等待期、除外條款與保守聲明

### 預期結果

推薦商品應為：

* `家庭定期壽險方案 C`

### 展示時可講的話

這題代表一個比較貼近真實顧問場景的案例。
除了商品本身，Agent 也會結合規則依據，說明為什麼家庭責任族群通常優先考慮壽險，這讓推薦更具可解釋性。

---

## 八、Demo 情境四：收入中斷保障

### 使用者輸入

```text
我 38 歲，已婚有小孩，年度預算 25000，想加強收入中斷風險保障。
```

### 展示重點

這一題要展示：

* Agent 會選用 `search_income_protection_products`
* 視情況補用 `get_recommendation_rules`
* Agent 能說明為什麼這類需求可能會優先看重大疾病或壽險候選商品

### 展示時可講的話

這題用來展示 Agent 對較抽象需求的處理能力。
收入中斷保障不是單一商品名稱，而是一種保障目的，因此工具設計會把它映射到更合適的候選商品類型。

---

## 九、展示 trace 時要強調的重點

在 ADK Dev UI 中，可打開 trace 觀察工具呼叫。

展示 trace 時，建議強調以下幾點：

### 1. 可追溯

可以看到 Agent 實際使用了哪些工具。

### 2. 工具邊界清楚

不同保障目標會對應不同工具，而不是讓模型自由查資料。

### 3. 系統更容易測試

因為每個工具責任明確，所以每個場景都能對應到具體工具驗收。

---

## 十、展示結尾可用說法

這個專案展示的是一個完整的保險推薦代理 PoC，重點不在於做出一個最聰明的模型，而是在於建立一個：

* 可互動
* 可追溯
* 可維護
* 可測試
* 可擴充

的 Agent 工具架構。

它透過：

* Google ADK 管理對話與工具調度
* ToolboxToolset 連接 ADK 與 MCP Toolbox
* MCP Toolbox 載入 `tools.yaml`
* 受控工具負責保險場景查詢
* Agent 負責推薦解釋與保守輸出

這樣的設計比自由 SQL 更適合作為企業型 Agent PoC 的基礎。

---

## 十一、展示後可補充的未來方向

如果展示後要補充後續方向，可用以下幾點：

### 1. 補強工具

將現有工具拆成更細的場景，例如熟齡醫療、低預算保障、家庭責任強化等。

### 2. 加入 FAQ / 條款檢索

透過 embedding 增加語意檢索能力，讓 Agent 能回答更細的保險知識問題。

### 3. 切換正式資料源

將 SQLite 替換為正式資料庫，保留相同的工具與 Agent 架構。

### 4. 補齊 production 安全設定

加入 `allowed-origins`、`allowed-hosts`、授權機制與更完整的存取控制。

---

## 十二、簡短結論版

若需要更短的結尾，可以直接說：

> 這個專案完成了一個以 `tools.yaml + ToolboxToolset + MCP Toolbox` 為核心的保險推薦代理原型，具備追問、商品篩選、規則解釋與可追溯工具呼叫能力，並能作為後續產品化與知識檢索擴充的基礎。

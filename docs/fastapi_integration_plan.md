# FastAPI 整合實作計劃

本文件定義如何把目前的保險推薦 ADK agent 整合為一個可由 FastAPI 提供的後端服務，並逐步取代目前由 Next.js route 代理 ADK API server 的做法。

## 1. 目標

整合完成後，系統應達成以下結果：

- 由 FastAPI 提供穩定的 HTTP 與 SSE 介面給前端使用
- FastAPI 直接承接 ADK agent 執行與 session 管理，而不是讓前端依賴 ADK API server 的私有路徑
- 保留既有 session state 行為，包含 user profile、最後推薦商品與 UI metadata
- 保持 Toolbox MCP 整合方式不變，避免一次同時改動資料查詢層
- 讓未來部署時可只暴露單一後端服務

## 2. 目前現況

### 2.1 已存在的能力

- app/agent.py 是正式的 create_agent 與 root_agent 入口，可直接作為 FastAPI service 的 agent factory
- app/app_runtime.py 已集中管理 app name、toolbox URL、session DB URI、model name 等 runtime 設定
- app/tools/session_tools.py 已把對話所需的狀態欄位收斂在 ADK state 內
- pyproject.toml 已經安裝 fastapi 與 uvicorn，相依不需要重新補齊

### 2.2 目前的 HTTP 邊界

目前前端不是直接呼叫 agent，而是透過 Next.js route 代理 ADK API server：

- frontend/app/api/agent/run/route.ts 會先建立 session、同步 state，再呼叫 /run_sse
- frontend/app/api/agent/sessions/route.ts 會呼叫 ADK 的 sessions list/create API
- frontend/app/api/agent/sessions/[sessionId]/route.ts 會呼叫 ADK 的 session delete API

這代表現在的依賴鏈是：

前端 -> Next.js API route -> ADK API server -> ADK agent -> Toolbox MCP

### 2.3 已確認的 ADK 整合能力

從已安裝的 ADK 套件可確認目前可使用以下元件：

- google.adk.runners.Runner
- google.adk.sessions.sqlite_session_service.SqliteSessionService
- google.adk.sessions.database_session_service.DatabaseSessionService

因此 FastAPI 可以直接建立 Runner 與 SessionService，不必被迫繼續依賴 adk api_server 作為中介。

## 3. 建議目標架構

建議把後端收斂為以下結構：

前端 -> FastAPI -> ADK Runner -> Agent -> Toolbox MCP -> SQLite

### 3.1 責任切分

- Agent 層：維持 app/agent.py 的對話 orchestration 與工具組合
- Runtime 層：負責載入設定、建立 SessionService、建立 Runner
- API 層：負責 request validation、session CRUD、SSE 串流、錯誤格式化
- Frontend：只處理畫面與事件渲染，不再了解 ADK 專用路由

### 3.2 整合原則

- 不改變 MCP Toolbox 與 tools.yaml 的工具邊界
- 不改變 session_tools.py 的 state key 設計
- 優先維持前端既有 payload 結構，降低 UI 端改動
- 先完成與現有前端相容，再考慮把 Next.js API route 移除

## 4. API 設計

為了最低遷移成本，FastAPI 第一版建議直接提供與目前前端相容的介面。

### 4.1 Session API

1. GET /api/agent/sessions
   - 回傳 session 清單
   - 轉換 ADK session 格式為前端現用的 SessionRecord-like 結構

2. POST /api/agent/sessions
   - 建立新 session
   - 接受 sessionId 與初始 state
   - 支援寫入 _ui_title 與 _ui_subtitle

3. DELETE /api/agent/sessions/{session_id}
   - 刪除指定 session
   - 對不存在 session 採冪等處理

### 4.2 Run API

1. POST /api/agent/run
   - 接受 prompt、sessionId、sessionState
   - 回傳 text/event-stream
   - 事件 envelope 維持目前前端 consumeProxyStream 可理解的型別：
     - meta
     - timeline
     - state
     - message
     - done
     - error

### 4.3 健康檢查 API

1. GET /healthz
   - 回傳 service status

2. GET /readyz
   - 檢查 session DB 與 Toolbox 端點是否可用

## 5. 建議新增檔案

建議新增以下 Python 模組，避免把 HTTP、ADK runtime 與 schema 全部塞進單一檔案：

- app/api/main.py
  - FastAPI app entrypoint
  - 掛載 routes、startup/shutdown hooks

- app/api/schemas.py
  - Pydantic request/response models

- app/api/dependencies.py
  - 統一建立與快取 runtime 元件
  - 例如 config、session_service、runner

- app/api/session_service.py
  - 包裝 ADK session CRUD 與 state patch 行為

- app/api/streaming.py
  - 將 Runner.run_async 產生的 ADK event 轉成前端需要的 SSE envelope

- app/api/routes/sessions.py
  - session list/create/delete routes

- app/api/routes/run.py
  - agent 執行與 SSE routes

- tests/test_fastapi_api.py
  - API 層測試

## 6. 實作步驟

### Phase 0: 整理共用 runtime

目標：把 FastAPI 與 CLI/測試都會用到的元件抽成共用 factory。

工作項目：

- 把 create_agent 保持為唯一 agent 建立入口
- 新增 create_session_service，依 ADK_SESSION_DB_URI 建立 SqliteSessionService 或 DatabaseSessionService
- 新增 create_runner，使用 Runner(app_name=..., agent=..., session_service=...)
- 若需要，補一個 create_app_runtime_container 來集中管理 singleton 資源

完成標準：

- 不透過 adk api_server 也能在 Python 內建立 agent + runner + session service

### Phase 1: 建立 FastAPI 基礎骨架

目標：先提供可啟動的 API service 與最小健康檢查。

工作項目：

- 建立 app/api/main.py 與 FastAPI 實例
- 加入 CORS 設定，允許 frontend 開發環境存取
- 新增 /healthz 與 /readyz
- Makefile 新增 run-fastapi 指令，例如 uv run uvicorn app.api.main:app --reload --port 8080

完成標準：

- 本地可單獨啟動 FastAPI
- 前端可透過環境變數切到 FastAPI base URL

### Phase 2: Session CRUD 落地

目標：先把目前前端最穩定的 session 行為搬到 FastAPI。

工作項目：

- 實作 list sessions
- 實作 create session
- 實作 delete session
- 保留 _ui_title、_ui_subtitle 與其他 state 欄位
- 回傳格式維持與 frontend/app/api/agent/sessions/route.ts 相容

完成標準：

- 前端對話列表、建立新對話、刪除對話均可改打 FastAPI

### Phase 3: Agent 執行與 SSE 串流

目標：用 FastAPI 直接呼叫 Runner.run_async，產出與現有前端相容的 SSE 事件。

工作項目：

- 接收 prompt、sessionId、sessionState
- 若 session 不存在則建立，存在則 patch state
- 把使用者輸入轉成 ADK Content 物件
- 透過 Runner.run_async 逐筆讀取 event
- 將 ADK event 映射為前端現用 envelope
- 在結束時補一筆 done，附上最新 session state

串流映射原則：

- functionCall -> timeline(tool-call)
- functionResponse -> timeline(tool-result)
- partial text -> message(append) + timeline(stream)
- final text -> message(replace) 或 done.finalText
- state delta -> state

完成標準：

- 前端不再需要依賴 /run_sse 與 ADK API server 的私有 SSE 格式

### Phase 4: 前端切換與 proxy 移除

目標：把 Next.js route 從主路徑移除，保留短期 fallback。

工作項目：

- frontend 改為直接呼叫 FastAPI base URL，或保留 Next.js route 但只做簡單轉發
- 加入 FEATURE FLAG，例如 USE_FASTAPI_BACKEND=1
- 穩定後移除 frontend/app/api/agent/* 內的大部分 ADK proxy 邏輯

完成標準：

- 主要資料流成為 前端 -> FastAPI -> ADK Runner

## 7. Session 與狀態策略

目前 state key 已經由 session_tools.py 固定，例如：

- user:age
- user:budget
- user:main_goal
- user:last_recommended_product_name
- user:last_recommended_product_id

FastAPI 整合時必須遵守以下規則：

- 不重新命名既有 state key
- UI 專用欄位維持使用 _ui_title、_ui_subtitle
- API 層只做 state patch，不在 HTTP 層重寫推薦邏輯
- session 不存在時才初始化，不要每輪覆蓋整個 state

## 8. 測試計劃

### 8.1 單元測試

- session create/list/delete
- state patch merge 行為
- ADK event -> SSE envelope 映射
- 錯誤情境：session 不存在、Toolbox 無法連線、模型回傳空內容

### 8.2 整合測試

- FastAPI 啟動後，POST /api/agent/run 可收到 SSE 串流
- 同一個 session 連續發兩輪訊息可重用 state
- 最近一次推薦商品可在下一輪被讀回

### 8.3 回歸驗證

- 既有 pytest 測試持續通過
- ADK eval 至少重跑 core 與 session-aware eval cases
- 前端使用 FastAPI backend 時，新增對話、刪除對話、串流回覆都可正常操作

## 9. 風險與對策

### 9.1 ADK event 格式與前端預期不完全一致

對策：

- 不把 ADK 原始事件直接暴露給前端
- 在 app/api/streaming.py 做明確映射與正規化

### 9.2 SessionService URI 在不同環境行為不同

對策：

- 優先支援 sqlite 與 database 兩種型別
- 啟動時明確記錄解析後使用的 session service 類型

### 9.3 Toolbox 不可用會讓整個 run 失敗

對策：

- /readyz 納入 Toolbox 連線檢查
- run API 捕捉錯誤並以一致 envelope 回報

### 9.4 一次切換前後端邊界風險太高

對策：

- 採兩段式遷移
- 先上 FastAPI 與 Next.js 並存
- 確認穩定後再移除 Next.js proxy

## 10. 建議交付順序

建議分三個 PR：

1. PR-1：FastAPI 骨架、runtime factories、health endpoints、session CRUD
2. PR-2：run SSE endpoint、event mapping、API tests
3. PR-3：frontend 切換、移除或瘦身 Next.js proxy、文件更新

## 11. 最小可行版本

若需要最快交付一個可用版本，最低範圍如下：

- 只做 FastAPI session CRUD + run SSE
- 前端先保留現有 UI 與大部分狀態管理
- Next.js route 改成單純轉發 FastAPI，而不再直接碰 ADK API server

這個版本能先把 ADK 專有路由隔離在 Python 後端內，後續再逐步把 Next.js proxy 拿掉。

## 12. 驗收標準

整體完成時，應滿足以下條件：

- 啟動 FastAPI 後，不需要另外暴露 adk api_server 給前端
- 前端可透過單一後端完成 session 管理與串流回覆
- 相同 session 的 user profile 與最後推薦商品能跨輪保存
- 既有 ToolboxToolset 與保險查詢工具不需重寫
- 測試與 eval 沒有明顯退化

## 13. 檔案級 task breakdown

本節把建議工作拆到檔案級別，方便直接開 issue、PR 或 implementation checklist。

### 13.1 調整既有檔案

#### app/app_runtime.py

責任：保留既有 runtime config 入口，並補齊 FastAPI service 所需設定。

建議新增項目：

- AppRuntimeConfig.fastapi_host
- AppRuntimeConfig.fastapi_port
- AppRuntimeConfig.fastapi_reload
- AppRuntimeConfig.cors_allow_origins
- load_runtime_config() 對上述欄位的環境變數解析

建議環境變數：

- FASTAPI_HOST，預設 127.0.0.1
- FASTAPI_PORT，預設 8080
- FASTAPI_RELOAD，預設 true 或 false 依開發模式決定
- FASTAPI_CORS_ALLOW_ORIGINS，以逗號分隔

完成標準：

- FastAPI 啟動不需要在其他檔案重複解析環境變數

#### app/agent.py

責任：維持唯一 agent 建立入口。

建議調整：

- 保留 create_agent()
- 不把 FastAPI、Runner 或 SessionService 依賴寫進此檔案
- 若需要加註型別，只做最小調整

完成標準：

- 任何 runtime 都透過 create_agent() 取得同一份 agent 組態

#### Makefile

責任：補 FastAPI 啟動與測試入口。

建議新增 target：

- run-fastapi
- run-backend 或 run-api-local
- test-api

建議命令方向：

- uv run uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8080

完成標準：

- 開發者不需要手動記 uvicorn 啟動參數

#### README.md

責任：補 FastAPI 開發模式、前端接線方式與遷移後路徑說明。

建議補充內容：

- 如何啟動 Toolbox
- 如何啟動 FastAPI backend
- frontend 應設定哪個 base URL
- FastAPI 與 ADK api_server 的角色差異

### 13.2 新增後端檔案

#### app/api/main.py

責任：FastAPI app entrypoint。

建議包含：

- create_app()
- app = create_app()
- 掛載 CORS middleware
- include_router(run_router)
- include_router(session_router)
- healthz 與 readyz route

完成標準：

- uvicorn 可直接以 app.api.main:app 啟動

#### app/api/dependencies.py

責任：集中建立並快取 runtime 依賴。

建議包含：

- get_runtime_config()
- create_session_service(config)
- get_session_service()
- create_runner(config)
- get_runner()
- get_agent()

注意事項：

- 優先把 singleton 初始化收斂在此處
- 不要讓 route handler 直接 new Runner 或直接解析環境變數

#### app/api/schemas.py

責任：集中 request 與 response schema。

建議包含：

- SessionCreateRequest
- SessionListItem
- SessionListResponse
- AgentRunRequest
- StreamEnvelopeMeta
- StreamEnvelopeTimeline
- StreamEnvelopeState
- StreamEnvelopeMessage
- StreamEnvelopeDone
- StreamEnvelopeError

完成標準：

- route handler 不需要內嵌 dict schema 定義

#### app/api/session_service.py

責任：封裝 ADK session CRUD 與 state patch。

建議包含：

- list_sessions_for_ui(app_name, user_id)
- create_session_if_missing(app_name, user_id, session_id, initial_state)
- patch_session_state(app_name, user_id, session_id, state_delta)
- get_session_state(app_name, user_id, session_id)
- delete_session_if_exists(app_name, user_id, session_id)
- to_session_list_item(session)

完成標準：

- route 層不需要直接處理 ADK session object 的轉換細節

#### app/api/streaming.py

責任：把 ADK event 轉為前端可直接消費的 SSE envelope。

建議包含：

- build_user_message_content(prompt)
- iter_run_events(runner, user_id, session_id, prompt)
- map_adk_event_to_envelopes(event, sequence)
- stringify_state_patch(state_delta)
- encode_sse_event(envelope)
- build_done_envelope(final_text, state)
- build_error_envelope(message)

完成標準：

- route handler 只負責串接流程，不負責事件映射細節

#### app/api/routes/sessions.py

責任：暴露 session list/create/delete endpoints。

建議包含：

- router = APIRouter(prefix="/api/agent/sessions", tags=["sessions"])
- list_sessions()
- create_session()
- delete_session(session_id)

#### app/api/routes/run.py

責任：暴露 agent run SSE endpoint。

建議包含：

- router = APIRouter(prefix="/api/agent", tags=["agent"])
- run_agent(request: AgentRunRequest)
- 以 StreamingResponse 回傳 SSE

#### tests/test_fastapi_api.py

責任：驗證 API contract。

建議覆蓋：

- GET /api/agent/sessions
- POST /api/agent/sessions
- DELETE /api/agent/sessions/{session_id}
- POST /api/agent/run 的非串流錯誤處理
- POST /api/agent/run 的 SSE 基本 envelope 順序

## 14. 函式級實作清單

本節進一步定義每個檔案應優先產出的函式與工作內容。

### 14.1 Runtime 層

#### app/api/dependencies.py

1. get_runtime_config
  - 直接呼叫 load_runtime_config
  - 回傳 AppRuntimeConfig

2. create_session_service
  - 讀取 config.session_db_uri
  - 若 schema 是 sqlite，建立 SqliteSessionService 或對應 factory
  - 其他情況走 DatabaseSessionService

3. create_runner
  - 使用 create_agent 建立 agent
  - 使用 create_session_service 建立 session_service
  - 建立 Runner(app_name=config.app_name, agent=agent, session_service=session_service)

4. get_runner
  - 做快取，避免每個 request 重建 Runner

### 14.2 Session 層

#### app/api/session_service.py

1. create_session_if_missing
  - 先嘗試讀 session
  - 不存在才 create
  - 避免重複建立導致 409 類型情境

2. patch_session_state
  - 讀目前 state
  - 只 merge state_delta
  - 保留既有 user:* 與 _ui_* 欄位

3. list_sessions_for_ui
  - 將 ADK session 轉為前端畫面所需欄位
  - 處理 title、subtitle、updatedAt、state

4. delete_session_if_exists
  - 不存在時回成功語意

### 14.3 SSE 映射層

#### app/api/streaming.py

1. build_user_message_content
  - 將 prompt 轉成 ADK Content

2. iter_run_events
  - 包裝 runner.run_async
  - 只處理與本次 session 相關的執行流

3. map_adk_event_to_envelopes
  - 對齊 frontend/app/api/agent/run/route.ts 目前的 envelope contract
  - functionCall -> timeline tool-call
  - functionResponse -> timeline tool-result
  - partial text -> message append
  - final text -> message replace 或 done

4. encode_sse_event
  - 輸出 data: {json} 加雙換行

5. collect_final_state
  - 從 session_service 讀最新 state
  - 作為 done envelope 的 state

### 14.4 Route 層

#### app/api/routes/run.py

1. run_agent
  - 驗證 prompt 與 sessionId
  - ensure session
  - patch state
  - 建立 StreamingResponse
  - 在 generator 內串接 iter_run_events 與 done envelope

2. sse_generator
  - 先送 meta
  - 逐筆送 mapped envelopes
  - 成功時送 done
  - 失敗時送 error

#### app/api/routes/sessions.py

1. list_sessions
  - 使用 list_sessions_for_ui

2. create_session
  - 接收 sessionId 與 state
  - 呼叫 create_session_if_missing

3. delete_session
  - 呼叫 delete_session_if_exists

#### app/api/main.py

1. create_app
  - 建立 FastAPI 物件
  - 掛 middleware
  - include routes

2. healthz
  - 回傳 process 存活狀態

3. readyz
  - 驗證 session service 與 Toolbox URL 基本可用性

## 15. 建議 PR checklist

### 15.1 PR-1 checklist

- 新增 app/api/main.py
- 新增 app/api/dependencies.py
- 新增 app/api/session_service.py
- 新增 app/api/routes/sessions.py
- 補 app/app_runtime.py 的 FastAPI 設定
- 補 Makefile 的 run-fastapi
- 補最小 API 測試

### 15.2 PR-2 checklist

- 新增 app/api/schemas.py
- 新增 app/api/streaming.py
- 新增 app/api/routes/run.py
- 完成 ADK event -> SSE envelope 映射
- 補 SSE 測試與錯誤路徑測試

### 15.3 PR-3 checklist

- frontend 改接 FastAPI base URL 或輕量 proxy
- 移除對 ADK /run_sse 與 /apps/.../sessions 的直接依賴
- 更新 README 與開發指令
- 重跑 pytest 與核心 eval

## 16. 實作優先順序建議

若由單人連續開發，建議照以下順序實作：

1. 先完成 app/api/dependencies.py 與 app/api/session_service.py
2. 再完成 app/api/main.py 與 app/api/routes/sessions.py
3. 用 tests/test_fastapi_api.py 先鎖定 session contract
4. 接著完成 app/api/streaming.py 與 app/api/routes/run.py
5. 最後再動 frontend 與 README

這個順序能先把最不確定的 ADK runtime 邊界固定，再處理 SSE 映射與前端接線。
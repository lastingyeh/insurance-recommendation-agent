.PHONY: help install install-eval sync sync-eval db-init db-reset toolbox-up toolbox-down toolbox-logs \
	run run-web run-cli clean clean-all check env-check eval-core eval-safety \
	eval-safety-case-09 eval-safety-case-10 eval-safety-case-11 eval-safety-case-12 eval-safety-case-13

# ─── 預設目標 ──────────────────────────────────────────────
help: ## 列出所有可用指令
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ─── 變數 ──────────────────────────────────────────────────
PYTHON   := .venv/bin/python
UV       := uv
SQLITE   := sqlite3
DB_FILE  := db/insurance.db
ADK      := .venv/bin/adk
APP_DIR  := .
ADK_PORT := 8000
EVAL_DIR := tests/evals
EVAL_CONFIG := $(EVAL_DIR)/test_config.json

# ─── 環境建立 ──────────────────────────────────────────────
install: ## 建立虛擬環境並安裝所有依賴
	$(UV) venv --python 3.12
	$(UV) sync

install-eval: ## 建立虛擬環境並安裝含 eval extra 的依賴
	$(UV) venv --python 3.12
	$(UV) sync --extra eval

sync: ## 同步依賴（已有 .venv 時使用）
	$(UV) sync

sync-eval: ## 同步含 eval extra 的依賴（執行 evals 時使用）
	$(UV) sync --extra eval

env-check: ## 檢查必要工具與環境變數
	@echo "=== 環境檢查 ==="
	@command -v $(UV) >/dev/null 2>&1  && echo "✔ uv"              || echo "✘ uv 未安裝"
	@command -v docker >/dev/null 2>&1 && echo "✔ docker"          || echo "✘ docker 未安裝"
	@command -v $(SQLITE) >/dev/null 2>&1 && echo "✔ sqlite3"      || echo "✘ sqlite3 未安裝"
	@[ -f .env ]                       && echo "✔ .env 存在"       || echo "✘ .env 不存在"
	@[ -d .venv ]                      && echo "✔ .venv 存在"      || echo "✘ .venv 不存在（請先 make install）"

# ─── 資料庫 ────────────────────────────────────────────────
db-init: ## 建立 SQLite 資料庫（schema + seed）
	@mkdir -p data
	$(SQLITE) $(DB_FILE) < db/schema.sql
	$(SQLITE) $(DB_FILE) < db/seed.sql
	@echo "資料庫已初始化：$(DB_FILE)"

db-reset: ## 刪除並重建資料庫
	rm -f $(DB_FILE)
	$(MAKE) db-init

# ─── Toolbox 服務（Docker）───────────────────────────────
toolbox-up: ## 啟動 Toolbox 容器（背景執行）
	docker compose up -d

toolbox-down: ## 停止並移除 Toolbox 容器
	docker compose down

toolbox-logs: ## 查看 Toolbox 容器日誌
	docker compose logs -f

# ─── 執行 Agent ────────────────────────────────────────────
run: run-web ## 預設以 Web UI 啟動 Agent

run-web: _kill-port ## 以 ADK Web UI 啟動 Agent
	$(ADK) web $(APP_DIR)

run-cli: ## 以 CLI 模式啟動 Agent
	$(ADK) run $(APP_DIR)

_kill-port: ## (內部) 釋放 ADK_PORT 佔用的程序
	@PID=$$(lsof -ti :$(ADK_PORT) 2>/dev/null); \
	if [ -n "$$PID" ]; then \
		echo "⚠ Port $(ADK_PORT) 被 PID $$PID 佔用，正在終止…"; \
		kill $$PID 2>/dev/null || true; \
		sleep 1; \
		kill -9 $$PID 2>/dev/null || true; \
		echo "✔ Port $(ADK_PORT) 已釋放"; \
	fi

# ─── 測試 ──────────────────────────────────────────────────
check: ## 執行測試
	$(PYTHON) -m pytest tests/ -v

# ─── ADK Evals ───────────────────────────────────────────
eval-core: ## 執行核心回歸 eval
	$(ADK) eval app $(EVAL_DIR)/insurance_core.test.json --config_file_path $(EVAL_CONFIG)
	$(ADK) eval app $(EVAL_DIR)/insurance_extended.test.json --config_file_path $(EVAL_CONFIG)

eval-safety: ## 執行所有 safety 單案 eval
	$(MAKE) eval-safety-case-09
	$(MAKE) eval-safety-case-10
	$(MAKE) eval-safety-case-11
	$(MAKE) eval-safety-case-12
	$(MAKE) eval-safety-case-13

eval-safety-case-09: ## 執行 safety case 09 eval
	$(ADK) eval app $(EVAL_DIR)/case_09_system_capability.test.json --config_file_path $(EVAL_CONFIG)

eval-safety-case-10: ## 執行 safety case 10 eval
	$(ADK) eval app $(EVAL_DIR)/case_10_no_guarantee.test.json --config_file_path $(EVAL_CONFIG)

eval-safety-case-11: ## 執行 safety case 11 eval
	$(ADK) eval app $(EVAL_DIR)/case_11_rule_explanation.test.json --config_file_path $(EVAL_CONFIG)

eval-safety-case-12: ## 執行 safety case 12 eval
	$(ADK) eval app $(EVAL_DIR)/case_12_product_detail_follow_up.test.json --config_file_path $(EVAL_CONFIG)

eval-safety-case-13: ## 執行 safety case 13 eval
	$(ADK) eval app $(EVAL_DIR)/case_13_no_investment_return.test.json --config_file_path $(EVAL_CONFIG)

# ─── 清除 ──────────────────────────────────────────────────
clean: ## 清除快取與暫存檔
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	rm -rf .pytest_cache

clean-db: ## 僅清除資料庫檔案
	rm -f $(DB_FILE)

clean-sessions: ## 清除 ADK session 資料
	rm -f .adk/session.db $(APP_DIR)/.adk/session.db

clean-all: clean clean-db clean-sessions ## 完整清除（快取 + 資料庫 + session）
	rm -rf .venv
	@echo "已完整清除。重新建立請執行 make install"

# ─── 一鍵啟動 ─────────────────────────────────────────────
up: install db-init toolbox-up ## 一鍵完成環境建立 + DB 初始化 + 啟動 Toolbox
	@echo ""
	@echo "環境就緒！執行 make run 啟動 Agent"

down: toolbox-down ## 停止所有服務

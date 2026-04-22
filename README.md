Core Components
ADK Agent

Handles conversation flow, follow-up questions, tool selection, and final recommendation generation.

Local Insurance Tools

Main tools for recommendation tasks:

summarize_user_profile
search_products_by_profile
get_product_detail
get_recommendation_rules
MCP Toolbox

Used as an auxiliary database exploration layer during development.

SQLite Database

Stores:

insurance products
recommendation rules
demo user profiles
FAQ knowledge
How to Run
1. Activate virtual environment
source .venv/bin/activate
2. Start MCP Toolbox with Docker
docker run --rm -p 5000:5000 \
  -v "$(pwd)/db:/workspace/db" \
  -e SQLITE_DATABASE=/workspace/db/insurance.db \
  us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:1.1.0 \
  --prebuilt sqlite
3. Start ADK web UI
adk web
4. Open browser

Go to:
http://127.0.0.1:8000

Example Test Inputs
Case A

我 30 歲，年度保險預算 15000，想加強醫療保障，有什麼推薦？

Case B

我想買保險，幫我推薦。

Case C

我 42 歲，已婚有小孩，年度預算 30000，想補家庭保障。

Current Capabilities
ask for missing information
map user goals to insurance product types
recommend products based on age, budget, and goal
explain recommendation reasons
mention waiting periods and exclusions
include conservative disclaimer
Known Limitations
product data is demo-only and not real insurance products
underwriting is not implemented
pricing is simplified
recommendation rules are basic and limited
no production-grade authentication / authorization layer yet
Disclaimer

This project is for prototype and educational purposes only.

Insurance recommendations are for initial screening only. Actual policy purchase is subject to product terms, health disclosure, and underwriting results.
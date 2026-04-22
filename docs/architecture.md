# Architecture

## High-Level Flow

User
-> ADK Agent
-> Local Insurance Tools
-> SQLite Database

Optional development support:
ADK Agent
-> MCP Toolbox
-> SQLite Database

## Responsibilities

### ADK Agent
- handle dialogue
- ask follow-up questions
- choose tools
- generate final answers

### Local Insurance Tools
- normalize user inputs
- search product candidates
- fetch product details
- fetch recommendation rules

### MCP Toolbox
- provide database exploration capability during development
- support debugging and schema inspection

### SQLite Database
- insurance_products
- recommendation_rules
- user_profiles_demo
- faq_knowledge

## Recommendation Workflow

1. collect required user information
2. summarize normalized profile
3. search candidate products
4. fetch rules if needed
5. fetch product details if needed
6. generate recommendation with explanation and disclaimer
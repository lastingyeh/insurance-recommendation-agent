# Demo Script

## Opening
Today I will demonstrate an insurance recommendation agent built with Google ADK, MCP Toolbox, SQLite, and Vertex AI.

This agent can collect user needs, ask follow-up questions, search insurance products, explain recommendation reasons, and provide conservative recommendation outputs.

## Demo 1: Complete Information
Input:
我 30 歲，年度保險預算 15000，想加強醫療保障，有什麼推薦？

Expected demo points:
- agent summarizes the user profile
- agent recommends 安心住院醫療方案 A
- agent explains waiting period and exclusions
- agent includes disclaimer

## Demo 2: Missing Information
Input:
我想買保險，幫我推薦。

Expected demo points:
- agent does not recommend immediately
- agent asks for age, budget, and main goal

## Demo 3: Family Protection
Input:
我 42 歲，已婚有小孩，年度預算 30000，想補家庭保障。

Expected demo points:
- agent maps family protection to life insurance
- agent recommends 家庭定期壽險方案 C
- agent explains rule basis

## Closing
This project demonstrates a complete prototype workflow:
- structured requirement collection
- insurance-specific tools
- database-backed recommendation
- explainable outputs
- conservative disclaimer handling
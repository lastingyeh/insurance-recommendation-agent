INSERT INTO insurance_products (
    product_id, product_name, product_type, target_age_min, target_age_max,
    annual_premium_min, annual_premium_max, coverage_focus, coverage_summary,
    waiting_period_days, exclusions, is_active
) VALUES
(1, '安心住院醫療方案 A', 'medical', 20, 55, 12000, 24000, '住院醫療', '提供住院日額與手術給付，適合想補強基礎醫療保障者', 30, '既往症、等待期內疾病不賠', 1),
(2, '全方位重大疾病方案 B', 'critical_illness', 25, 60, 18000, 36000, '重大疾病', '提供重大疾病一次性給付，適合家庭經濟支柱', 90, '特定除外疾病、未誠實告知', 1),
(3, '家庭定期壽險方案 C', 'life', 25, 65, 15000, 50000, '家庭保障', '定期壽險，適合有家庭責任與貸款壓力者', 0, '自殺等待期、未揭露健康狀況', 1),
(4, '安心意外防護方案 D', 'accident', 18, 60, 6000, 15000, '意外保障', '提供意外身故與意外醫療，適合通勤族與外勤工作者', 0, '高風險活動不保或限額', 1),
(5, '高齡醫療補強方案 E', 'medical', 46, 70, 22000, 48000, '熟齡醫療', '適合中高齡族群補強醫療保障', 30, '既往症、特定慢性病除外', 1),
(6, '新鮮人基礎保障方案 F', 'accident', 22, 35, 5000, 10000, '低預算基礎保障', '適合預算有限的年輕族群，提供基礎意外保障', 0, '危險職業部分限保', 1);

INSERT INTO recommendation_rules (
    rule_id, rule_name, product_type, condition_json, recommendation_logic, priority, is_active
) VALUES
(1, '年輕低預算先補基礎意外', 'accident', '{\"age_max\":35,\"budget_max\":12000}', '若年齡較輕且預算有限，優先推薦低門檻基礎意外商品', 10, 1),
(2, '家庭支柱優先考慮壽險', 'life', '{\"has_children\":true}', '若有子女或家庭責任，優先考慮壽險補足家庭收入中斷風險', 5, 1),
(3, '重視醫療支出可先看醫療險', 'medical', '{\"main_goal\":\"medical\"}', '若主要目標是補強住院與手術費用，先推薦醫療型商品', 8, 1),
(4, '收入支柱可補重大疾病', 'critical_illness', '{\"main_goal\":\"income_protection\"}', '若擔心重大疾病造成收入中斷，可納入重大疾病商品', 7, 1),
(5, '熟齡族群檢查年齡限制', 'medical', '{\"age_min\":46}', '熟齡族群應優先檢查商品投保年齡與醫療保障內容', 20, 1);


INSERT INTO user_profiles_demo (
    user_id, name, age, marital_status, has_children, occupation_risk_level,
    annual_income, insurance_budget, main_goal, risk_preference, existing_coverage
) VALUES
(1, 'Amy', 30, 'single', 0, 'low', 700000, 12000, 'medical', 'balanced', 'company_group_insurance'),
(2, 'Brian', 42, 'married', 1, 'medium', 1200000, 30000, 'family_protection', 'conservative', 'medical_basic'),
(3, 'Cindy', 50, 'married', 1, 'low', 1500000, 40000, 'medical', 'balanced', 'life_basic'),
(4, 'David', 27, 'single', 0, 'medium', 650000, 8000, 'accident', 'aggressive', 'none'),
(5, 'Eva', 38, 'married', 1, 'low', 1100000, 25000, 'income_protection', 'balanced', 'medical_basic');


INSERT INTO faq_knowledge (
    faq_id, question, answer, related_product_type, audience_tag
) VALUES
(1, '醫療險主要保障什麼？', '醫療險通常用於補強住院、手術或特定醫療費用支出。', 'medical', 'general'),
(2, '壽險適合哪些人？', '壽險通常較適合有家庭責任、房貸或收入支柱角色的人。', 'life', 'family'),
(3, '意外險和醫療險有什麼不同？', '意外險重點在意外事故造成的傷害，醫療險則多補強疾病或住院醫療費用。', 'accident', 'general'),
(4, '重大疾病險適合誰？', '擔心重大疾病造成收入中斷或一次性高額支出的人，通常會考慮重大疾病保障。', 'critical_illness', 'income_protection'),
(5, 'AI 推薦是否等於正式投保建議？', '不是，AI 僅能提供初步資訊整理與商品篩選，正式投保仍需以條款與核保結果為準。', NULL, 'compliance');
DROP TABLE IF EXISTS insurance_products;
DROP TABLE IF EXISTS recommendation_rules;
DROP TABLE IF EXISTS user_profiles_demo;
DROP TABLE IF EXISTS faq_knowledge;

CREATE TABLE insurance_products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    product_type TEXT NOT NULL,
    target_age_min INTEGER NOT NULL,
    target_age_max INTEGER NOT NULL,
    annual_premium_min INTEGER NOT NULL,
    annual_premium_max INTEGER NOT NULL,
    coverage_focus TEXT NOT NULL,
    coverage_summary TEXT NOT NULL,
    waiting_period_days INTEGER DEFAULT 0,
    exclusions TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE recommendation_rules (
    rule_id INTEGER PRIMARY KEY,
    rule_name TEXT NOT NULL,
    product_type TEXT NOT NULL,
    condition_json TEXT NOT NULL,
    recommendation_logic TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE user_profiles_demo (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    marital_status TEXT NOT NULL,
    has_children INTEGER NOT NULL DEFAULT 0,
    occupation_risk_level TEXT NOT NULL,
    annual_income INTEGER NOT NULL,
    insurance_budget INTEGER NOT NULL,
    main_goal TEXT NOT NULL,
    risk_preference TEXT NOT NULL,
    existing_coverage TEXT
);

CREATE TABLE faq_knowledge (
    faq_id INTEGER PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    related_product_type TEXT,
    audience_tag TEXT
);
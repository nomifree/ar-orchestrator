SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY,
    client_name TEXT NOT NULL,
    specialty TEXT NOT NULL,
    sla_target_days INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payers (
    payer_id TEXT PRIMARY KEY,
    payer_name TEXT NOT NULL,
    payer_type TEXT NOT NULL,
    avg_response_days INTEGER NOT NULL,
    appeal_window_days INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    portal_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    employee_name TEXT NOT NULL,
    team TEXT NOT NULL,
    role TEXT NOT NULL,
    shift TEXT,
    supervisor_id TEXT,
    active_flag BOOLEAN DEFAULT TRUE,
    hire_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    payer_id TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    service_date DATE NOT NULL,
    submit_date DATE NOT NULL,
    billed_amount DOUBLE NOT NULL,
    allowed_amount DOUBLE,
    paid_amount DOUBLE DEFAULT 0,
    patient_balance DOUBLE DEFAULT 0,
    claim_status TEXT NOT NULL,
    days_in_ar INTEGER,
    aging_bucket TEXT,
    cpt_codes TEXT,
    icd10_codes TEXT,
    claim_type TEXT,
    blocker_owner TEXT,
    assigned_to TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS denials (
    denial_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    denial_date DATE NOT NULL,
    denial_category TEXT NOT NULL,
    denial_reason TEXT NOT NULL,
    denial_reason_code TEXT,
    denied_amount DOUBLE NOT NULL,
    appeal_deadline DATE,
    appeal_status TEXT,
    open_flag BOOLEAN DEFAULT TRUE,
    is_repeat_denial BOOLEAN DEFAULT FALSE,
    preventable_flag BOOLEAN DEFAULT FALSE,
    proof_on_file BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS followups (
    followup_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    followup_date DATE NOT NULL,
    action_code TEXT NOT NULL,
    action_description TEXT,
    status_code TEXT NOT NULL,
    amount_recovered DOUBLE DEFAULT 0,
    next_action_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS work_queue (
    claim_id TEXT PRIMARY KEY,
    workability_status TEXT NOT NULL,
    priority_score INTEGER NOT NULL,
    priority_level TEXT NOT NULL,
    score_breakdown TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    recommended_action_code TEXT NOT NULL,
    assigned_to TEXT,
    queue_generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scoring_config (
    config_id INTEGER PRIMARY KEY,
    config_name TEXT NOT NULL,
    weight_days_ar INTEGER NOT NULL,
    weight_balance INTEGER NOT NULL,
    weight_denial_deadline INTEGER NOT NULL,
    weight_stale_followup INTEGER NOT NULL,
    weight_payer_risk INTEGER NOT NULL,
    weight_repeat_denial INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

RESET_SQL = """
DROP TABLE IF EXISTS work_queue;
DROP TABLE IF EXISTS followups;
DROP TABLE IF EXISTS denials;
DROP TABLE IF EXISTS claims;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS payers;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS scoring_config;
"""

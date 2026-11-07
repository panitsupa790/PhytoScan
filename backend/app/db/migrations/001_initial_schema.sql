CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    password_hash TEXT,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    refresh_token_hash TEXT NOT NULL UNIQUE,
    device_name TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    platform TEXT,
    device_name TEXT,
    app_version TEXT,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS plants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name_th TEXT NOT NULL,
    name_en TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diseases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plant_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    name_th TEXT NOT NULL DEFAULT '',
    name_en TEXT NOT NULL,
    is_healthy INTEGER NOT NULL DEFAULT 0 CHECK (is_healthy IN (0, 1)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE RESTRICT,
    UNIQUE (plant_id, code)
);

CREATE TABLE IF NOT EXISTS disease_guidance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_id INTEGER NOT NULL,
    guidance_type TEXT NOT NULL CHECK (
        guidance_type IN ('symptom', 'care', 'prevention')
    ),
    content_th TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    source_reference TEXT,
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (
        review_status IN ('pending', 'verified')
    ),
    verified_at TEXT,
    FOREIGN KEY (disease_id) REFERENCES diseases(id) ON DELETE CASCADE,
    UNIQUE (disease_id, guidance_type, sort_order)
);

CREATE TABLE IF NOT EXISTS model_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_type TEXT NOT NULL CHECK (
        model_type IN ('plant_classifier', 'disease_classifier')
    ),
    plant_id INTEGER,
    model_version TEXT NOT NULL UNIQUE,
    architecture TEXT NOT NULL,
    file_path TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    input_width INTEGER NOT NULL,
    input_height INTEGER NOT NULL,
    input_channels INTEGER NOT NULL,
    dtype TEXT NOT NULL,
    pixel_min REAL NOT NULL,
    pixel_max REAL NOT NULL,
    decoder TEXT NOT NULL,
    resize_method TEXT NOT NULL,
    preprocessing TEXT NOT NULL,
    external_normalization INTEGER NOT NULL DEFAULT 0 CHECK (
        external_normalization IN (0, 1)
    ),
    operating_scope TEXT,
    is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS model_classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    class_index INTEGER NOT NULL,
    class_code TEXT NOT NULL,
    plant_id INTEGER,
    disease_id INTEGER,
    FOREIGN KEY (model_id) REFERENCES model_artifacts(id) ON DELETE CASCADE,
    FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE RESTRICT,
    FOREIGN KEY (disease_id) REFERENCES diseases(id) ON DELETE RESTRICT,
    UNIQUE (model_id, class_index),
    UNIQUE (model_id, class_code)
);

CREATE TABLE IF NOT EXISTS model_thresholds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    min_confidence REAL NOT NULL CHECK (min_confidence BETWEEN 0.0 AND 1.0),
    min_margin REAL NOT NULL CHECK (min_margin BETWEEN 0.0 AND 1.0),
    selection_criteria TEXT NOT NULL,
    evaluation_config_sha256 TEXT,
    validation_manifest_sha256 TEXT,
    selection_data TEXT,
    test_adjustment_performed INTEGER NOT NULL DEFAULT 0 CHECK (
        test_adjustment_performed IN (0, 1)
    ),
    frozen_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
    FOREIGN KEY (model_id) REFERENCES model_artifacts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS model_deployments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    environment TEXT NOT NULL CHECK (
        environment IN ('development', 'testing', 'production')
    ),
    status TEXT NOT NULL CHECK (status IN ('active', 'retired', 'failed')),
    deployed_at TEXT NOT NULL,
    retired_at TEXT,
    notes TEXT,
    FOREIGN KEY (model_id) REFERENCES model_artifacts(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS scan_sessions (
    id TEXT PRIMARY KEY,
    parent_scan_id TEXT,
    user_id TEXT,
    device_id TEXT,
    status TEXT NOT NULL CHECK (
        status IN (
            'processing',
            'manual_confirmation_required',
            'completed',
            'failed',
            'cancelled'
        )
    ),
    image_count INTEGER NOT NULL CHECK (image_count BETWEEN 1 AND 3),
    final_plant_id INTEGER,
    plant_name_th_snapshot TEXT,
    plant_name_en_snapshot TEXT,
    plant_confidence REAL CHECK (
        plant_confidence IS NULL OR plant_confidence BETWEEN 0.0 AND 1.0
    ),
    plant_source TEXT CHECK (
        plant_source IS NULL OR plant_source IN (
            'automatic',
            'manual_selection',
            'manual_confirmation'
        )
    ),
    result_agreement INTEGER CHECK (
        result_agreement IS NULL OR result_agreement IN (0, 1)
    ),
    plant_classifier_model_id INTEGER,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (parent_scan_id) REFERENCES scan_sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL,
    FOREIGN KEY (final_plant_id) REFERENCES plants(id) ON DELETE RESTRICT,
    FOREIGN KEY (plant_classifier_model_id) REFERENCES model_artifacts(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS scan_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    image_index INTEGER NOT NULL CHECK (image_index BETWEEN 0 AND 2),
    original_filename TEXT NOT NULL,
    local_path TEXT,
    storage_key TEXT,
    mime_type TEXT NOT NULL,
    file_size INTEGER NOT NULL CHECK (file_size >= 0),
    width INTEGER NOT NULL CHECK (width > 0),
    height INTEGER NOT NULL CHECK (height > 0),
    sha256 TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (scan_id) REFERENCES scan_sessions(id) ON DELETE CASCADE,
    UNIQUE (scan_id, image_index)
);

CREATE TABLE IF NOT EXISTS plant_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_image_id INTEGER NOT NULL UNIQUE,
    model_id INTEGER,
    predicted_plant_id INTEGER,
    predicted_code_snapshot TEXT,
    confidence REAL CHECK (confidence IS NULL OR confidence BETWEEN 0.0 AND 1.0),
    top1_top2_margin REAL CHECK (
        top1_top2_margin IS NULL OR top1_top2_margin BETWEEN 0.0 AND 1.0
    ),
    accepted INTEGER NOT NULL CHECK (accepted IN (0, 1)),
    decision TEXT NOT NULL CHECK (
        decision IN (
            'accepted',
            'low_confidence',
            'low_margin',
            'inconsistent_plant',
            'manual_selection'
        )
    ),
    rejection_reasons TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    FOREIGN KEY (scan_image_id) REFERENCES scan_images(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES model_artifacts(id) ON DELETE RESTRICT,
    FOREIGN KEY (predicted_plant_id) REFERENCES plants(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS plant_prediction_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plant_prediction_id INTEGER NOT NULL,
    class_index INTEGER NOT NULL,
    plant_id INTEGER NOT NULL,
    probability REAL NOT NULL CHECK (probability BETWEEN 0.0 AND 1.0),
    rank INTEGER NOT NULL CHECK (rank > 0),
    FOREIGN KEY (plant_prediction_id) REFERENCES plant_predictions(id) ON DELETE CASCADE,
    FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE RESTRICT,
    UNIQUE (plant_prediction_id, class_index),
    UNIQUE (plant_prediction_id, rank)
);

CREATE TABLE IF NOT EXISTS manual_confirmations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    suggested_plant_id INTEGER,
    confirmed_plant_id INTEGER,
    action TEXT NOT NULL CHECK (
        action IN (
            'requested',
            'confirm_suggestion',
            'select_other',
            'split_images',
            'cancel'
        )
    ),
    reason TEXT,
    confirmed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (scan_id) REFERENCES scan_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (suggested_plant_id) REFERENCES plants(id) ON DELETE RESTRICT,
    FOREIGN KEY (confirmed_plant_id) REFERENCES plants(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS disease_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_image_id INTEGER NOT NULL UNIQUE,
    plant_id INTEGER NOT NULL,
    disease_id INTEGER,
    disease_model_id INTEGER,
    disease_code_snapshot TEXT NOT NULL,
    disease_name_th_snapshot TEXT NOT NULL DEFAULT '',
    disease_name_en_snapshot TEXT NOT NULL,
    confidence REAL CHECK (confidence IS NULL OR confidence BETWEEN 0.0 AND 1.0),
    is_healthy INTEGER NOT NULL DEFAULT 0 CHECK (is_healthy IN (0, 1)),
    status TEXT NOT NULL CHECK (
        status IN ('completed', 'uncertain', 'model_unavailable', 'not_processed')
    ),
    created_at TEXT NOT NULL,
    FOREIGN KEY (scan_image_id) REFERENCES scan_images(id) ON DELETE CASCADE,
    FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE RESTRICT,
    FOREIGN KEY (disease_id) REFERENCES diseases(id) ON DELETE RESTRICT,
    FOREIGN KEY (disease_model_id) REFERENCES model_artifacts(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS result_detail_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_result_id INTEGER NOT NULL,
    detail_type TEXT NOT NULL CHECK (
        detail_type IN ('symptom', 'care', 'prevention')
    ),
    content TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (disease_result_id) REFERENCES disease_results(id) ON DELETE CASCADE,
    UNIQUE (disease_result_id, detail_type, sort_order)
);

CREATE TABLE IF NOT EXISTS scan_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_data TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (scan_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scan_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT,
    image_id INTEGER,
    http_status INTEGER,
    error_code TEXT NOT NULL,
    message TEXT NOT NULL,
    retryable INTEGER NOT NULL DEFAULT 0 CHECK (retryable IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (scan_id) REFERENCES scan_sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (image_id) REFERENCES scan_images(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    scan_id TEXT NOT NULL,
    image_id INTEGER,
    feedback_type TEXT NOT NULL CHECK (
        feedback_type IN ('correct', 'wrong_plant', 'wrong_disease', 'uncertain')
    ),
    corrected_plant_id INTEGER,
    corrected_disease_id INTEGER,
    comment TEXT,
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (
        review_status IN ('pending', 'reviewed', 'rejected')
    ),
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (scan_id) REFERENCES scan_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES scan_images(id) ON DELETE SET NULL,
    FOREIGN KEY (corrected_plant_id) REFERENCES plants(id) ON DELETE RESTRICT,
    FOREIGN KEY (corrected_disease_id) REFERENCES diseases(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_diseases_plant ON diseases(plant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_guidance_disease ON disease_guidance(disease_id, guidance_type, sort_order);
CREATE INDEX IF NOT EXISTS idx_models_type_active ON model_artifacts(model_type, is_active);
CREATE INDEX IF NOT EXISTS idx_model_deployments_status ON model_deployments(environment, status);
CREATE INDEX IF NOT EXISTS idx_scans_user_created ON scan_sessions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_plant_created ON scan_sessions(final_plant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_status_created ON scan_sessions(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_images_scan ON scan_images(scan_id, image_index);
CREATE INDEX IF NOT EXISTS idx_disease_results_disease ON disease_results(disease_id);
CREATE INDEX IF NOT EXISTS idx_events_scan_created ON scan_events(scan_id, created_at);
CREATE INDEX IF NOT EXISTS idx_errors_created ON scan_errors(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON user_feedback(feedback_type, created_at DESC);

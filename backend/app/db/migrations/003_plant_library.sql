CREATE TABLE IF NOT EXISTS plant_library_entries (
    plant_id INTEGER PRIMARY KEY,
    scientific_name TEXT NOT NULL,
    summary_th TEXT NOT NULL,
    cover_image TEXT NOT NULL,
    review_status TEXT NOT NULL,
    content_json TEXT NOT NULL,
    source_file TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_plant_library_scientific_name
    ON plant_library_entries(scientific_name);

CREATE INDEX IF NOT EXISTS idx_plant_library_review_status
    ON plant_library_entries(review_status);

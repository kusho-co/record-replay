CREATE TABLE IF NOT EXISTS traffic_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    path VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    headers JSON,
    path_params JSON,
    query_params JSON,
    request_body JSON,
    status INT,
    duration_ms FLOAT,
    response_headers JSON,
    INDEX idx_timestamp (timestamp),
    INDEX idx_path (path)
);

CREATE TABLE IF NOT EXISTS request_anomalies (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_id BIGINT,
    similarity_score FLOAT,
    anomaly_type VARCHAR(50),
    description TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reference_events JSON,
    FOREIGN KEY (event_id) REFERENCES traffic_events(id)
);

CREATE TABLE IF NOT EXISTS request_patterns (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    path VARCHAR(255),
    method VARCHAR(10),
    pattern_vector JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_path_method (path, method)
);
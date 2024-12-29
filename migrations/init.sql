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

CREATE TABLE  IF NOT EXISTS endpoint_test_suites (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    url VARCHAR(255) NOT NULL,
    http_method VARCHAR(10) NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_endpoint UNIQUE (url, http_method)
);

CREATE TABLE  IF NOT EXISTS test_cases (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    suite_id BIGINT NOT NULL,
    description VARCHAR(255),
    category VARCHAR(50),
    priority VARCHAR(20),
    request_method VARCHAR(10),
    request_url VARCHAR(255),
    request_headers JSON,
    request_path_params JSON,
    request_query_params JSON,
    request_body JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (suite_id) REFERENCES endpoint_test_suites(id)
);
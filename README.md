
# Kusho Record Replay Service

A Flask-based service for collecting, analyzing, and generating test cases for API traffic patterns.

## Prerequisites

- Docker and Docker Compose
- Python 3.x (for local development)
- MySQL 8.0
- OpenAI API key (for test generation features)

## Quick Start

1. Clone the repository:
   ```bash
   git clone git@github.com:kusho-co/record-replay.git
   cd record-replay
   ```

2. Configure the services in `docker-compose.yml`:
   ```yaml
   services:
     collector:
       environment:
         - MYSQL_HOST=mysql
         - MYSQL_PORT=3306
         - MYSQL_USER=kusho
         - MYSQL_PASSWORD=kusho_password
         - MYSQL_DATABASE=kusho_traffic
         - OPENAI_ORGID=your_org_id
         - OPENAI_API_KEY=your_api_key

     mysql:
       environment:
         - MYSQL_ROOT_PASSWORD=root_password
         - MYSQL_DATABASE=kusho_traffic
         - MYSQL_USER=kusho
         - MYSQL_PASSWORD=kusho_password
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

The service will be available at `http://localhost:7071`.

---

## API Endpoints

### Event Collection

#### Collect Events
```
POST /api/v1/events
```
- **Description**: Collect and store traffic events.
- **Request Body**:
  ```json
  {
    "events": [
      {
        "id": "event1",
        "timestamp": "2024-12-29T12:00:00Z",
        "data": "event_data"
      }
    ]
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Stored <number> events"
  }
  ```

---

### Traffic Analysis

#### Get Anomalies
```
GET /api/v1/analysis/anomalies
```
- **Description**: Retrieve traffic anomalies.
- **Query Parameters**:
  - `hours` (optional, default: 24): Number of past hours to analyze.
  - `min_score` (optional, default: 0.0): Minimum anomaly score.
- **Response**:
  ```json
  {
    "anomalies": [],
    "count": 0
  }
  ```

#### Analyze Traffic
```
POST /api/v1/analysis/analyze
```
- **Description**: Analyze recent traffic data.
- **Request Body**:
  ```json
  {
    "hours": 24
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Analyzed traffic for past 24 hours"
  }
  ```

#### Start Analysis Job
```
POST /api/v1/analysis/start-job
```
- **Description**: Start a background job for analyzing traffic and generating tests.
- **Request Body**:
  ```json
  {
    "hours": 24
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "job_id": "<job_id>",
    "message": "Started analysis job for past 24 hours"
  }
  ```

#### Get Job Status
```
GET /api/v1/analysis/job-status
```
- **Description**: Get the status of an analysis job.
- **Query Parameters**:
  - `job_id` (required): The ID of the job.
- **Response**:
  ```json
  {
    "job_id": "<job_id>",
    "job_status": "completed",
    "result": {},
    "error": null
  }
  ```

---

### OpenAPI Export

#### Export OpenAPI
```
GET /api/v1/export/openapi
```
- **Description**: Export the test suite in OpenAPI-compatible JSON.
- **Query Parameters**:
  - `base_url` (required): Base URL for the API.
- **Response**:
  ```json
  {
    "openapi": "3.0.0",
    "paths": {}
  }
  ```

#### Export OpenAPI for an Endpoint
```
GET /api/v1/export/openapi/endpoint
```
- **Description**: Export OpenAPI-compatible data for a specific endpoint.
- **Query Parameters**:
  - `base_url` (required): Base URL for the API.
  - `url` (required): Endpoint URL.
  - `http_method` (required): HTTP method (e.g., `GET`, `POST`).
- **Response**:
  ```json
  {
    "summary": "Endpoint description",
    "parameters": [],
    "responses": {}
  }
  ```

---

### Miscellaneous

#### List Available Endpoints
```
GET /api/v1/endpoints
```
- **Description**: List all available API endpoints.
- **Response**:
  ```json
  {
    "status": "success",
    "endpoints": ["/api/v1/events", "/api/v1/analysis/anomalies"]
  }
  ```

---

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run migrations:
   ```bash
   flask db upgrade
   ```

4. Start the development server:
   ```bash
   python -m flask run --port 7071
   ```

## Docker Configuration

The service uses two main containers:
- `collector`: The Flask application service
- `mysql`: MySQL 8.0 database server

Volumes:
- `mysql_data`: Persistent storage for MySQL data
- `migrations`: Database migration scripts
- `custom.cnf`: Custom MySQL configuration

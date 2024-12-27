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

The service will be available at `http://localhost:7071`

## Available Endpoints

- `POST /api/v1/events` - Collect events
- `GET /api/v1/analytics` - Get traffic analytics
- `GET /api/v1/analysis/anomalies` - Get traffic anomalies
- `POST /api/v1/generate-tests/bulk` - Generate test cases
- `POST /api/v1/analysis/start-job` - Start analysis job
- `GET /api/v1/analysis/job-status/<job_id>` - Check job status

The service will be available at `http://localhost:7071`

## API Endpoints

### Event Collection
```
POST /api/v1/events
```
Collect and store traffic events.


### Test Generation
```
POST /api/v1/generate-tests/bulk
```
Generate test cases in bulk based on traffic patterns.

### Analysis Jobs
```
POST /api/v1/analysis/start-job
GET /api/v1/analysis/job-status/<job_id>
```
Start and monitor analysis jobs.

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

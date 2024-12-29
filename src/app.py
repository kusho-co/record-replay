from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from .config import Config
from .storage.mysql import MySQLStorage
from .services.traffic import TrafficService
from .analysis.analyzer import RequestAnalyzer
from .generation.test_utils import TestGenerator
from .background_worker import BackgroundWorker
from .models import Job
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio
import uuid

executor = ThreadPoolExecutor(max_workers=5)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    config = Config()
    job_registry = {}
    
    storage = MySQLStorage(config.MYSQL_URI)
    traffic_service = TrafficService(storage)

    @app.route('/api/v1/events', methods=['POST'])
    def collect_events():
        try:
            events = request.json.get('events', [])
            traffic_service.store_events(events)
            return jsonify({
                'status': 'success',
                'message': f'Stored {len(events)} events'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500


    
    @app.route('/api/v1/analysis/anomalies', methods=['GET'])
    async def get_anomalies():
        hours = request.args.get('hours', default=24, type=int)
        min_score = request.args.get('min_score', default=0.0, type=float)
        
        anomalies = await storage.get_anomalies(hours=hours, min_score=min_score)
        return jsonify({
            'anomalies': anomalies,
            'count': len(anomalies)
        })
    



    @app.route('/api/v1/analysis/analyze', methods=['POST'])
    async def analyze_traffic():
        try:
            hours = request.json.get('hours', 24)
            analyzer = RequestAnalyzer(storage)
            await analyzer.analyze_recent_traffic(hours)
            return jsonify({
                'status': 'success',
                'message': f'Analyzed traffic for past {hours} hours'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/api/v1/analysis/start-job', methods=['POST'])
    async def start_analysis_job():
        """Start a new analysis and test generation job"""
        try:
            # Generate a unique job ID
            job_id = str(uuid.uuid4())
            job_registry[job_id] = {'status': 'in progress', 'result': None}

            # Get parameters from the request
            hours = request.json.get('hours', 24)

            # Define the background task
            def run_analysis_job(job_id, hours):
                try:
                    analyzer = RequestAnalyzer(storage)
                    analyzer.analyze_recent_traffic(hours)
                    worker = BackgroundWorker(storage, TestGenerator())
                    results = asyncio.run(worker.run_analysis(hours=hours))
                    logger.info(f"Analysis job {job_id} completed: {results}")
                    job_registry[job_id] = {'status': 'completed', 'result': results}
                except Exception as e:
                    logger.error(f"Error in job {job_id}: {str(e)}")
                    job_registry[job_id] = {'status': 'failed', 'error': str(e)}
            
            # Submit the task to the executor
            executor.submit(run_analysis_job, job_id, hours)

            # Respond immediately to the client with the job ID
            return jsonify({
                'status': 'success',
                'job_id': job_id,
                'message': f'Started analysis job for past {hours} hours'
            }), 202
        except Exception as e:
            logger.error(f"Error starting job: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
        
    @app.route('/api/v1/analysis/job-status', methods=['GET'])
    def get_job_status():
        """Get the status of a specific job"""
        job_id = request.args.get('job_id')
        if not job_id:
            return jsonify({'status': 'error', 'message': 'Missing job_id parameter'}), 400

        job_info = job_registry.get(job_id)
        if not job_info:
            return jsonify({'status': 'error', 'message': 'Job not found'}), 404

        return jsonify({
            'job_id': job_id,
            'job_status': job_info['status'],
            'result': job_info.get('result'),
            'error': job_info.get('error')
        })
    
    @app.route('/api/v1/export/openapi', methods=['GET'])
    def export_openapi():
        """Export test suite data in OpenAPI-compatible JSON."""
        try:
            base_url = request.args.get('base_url')
            if not base_url:
                return jsonify({'status': 'error', 'message': 'Missing base_url parameter'}), 400

            # Use the storage function to generate OpenAPI data
            openapi_data = storage.generate_openapi_data(base_url)
            return jsonify(openapi_data)

        except Exception as e:
            logger.error(f"Error exporting OpenAPI data: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
    @app.route('/api/v1/export/openapi/endpoint', methods=['GET'])
    def export_openapi_for_endpoint():
        """Export OpenAPI data for a specific endpoint."""
        try:
            base_url = request.args.get('base_url')
            url = request.args.get('url')
            http_method = request.args.get('http_method')
            
            if not base_url or not url or not http_method:
                return jsonify({
                    'status': 'error',
                    'message': 'Missing required parameters: base_url, url, http_method'
                }), 400

            openapi_data = storage.generate_openapi_data_for_endpoint(url, http_method, base_url)
            return jsonify(openapi_data)

        except Exception as e:
            logger.error(f"Error exporting OpenAPI for endpoint: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/api/v1/endpoints', methods=['GET'])
    def list_available_endpoints():
        """List all available endpoints."""
        try:
            endpoints = storage.get_available_endpoints()
            return jsonify({'status': 'success', 'endpoints': endpoints})
        except Exception as e:
            logger.error(f"Error listing endpoints: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500


    
    return app



if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=7071)
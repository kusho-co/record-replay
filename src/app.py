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


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    config = Config()
    
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

    @app.route('/api/v1/analytics', methods=['GET'])
    def get_analytics():
        hours = int(request.args.get('hours', 24))
        path_pattern = request.args.get('path_pattern')
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        analytics = traffic_service.get_analytics(start_time, end_time, path_pattern)
        return jsonify({
            'timeframe': f'Last {hours} hours',
            'analytics': analytics
        })
    
    @app.route('/api/v1/analysis/anomalies', methods=['GET'])
    async def get_anomalies():
        hours = request.args.get('hours', default=24, type=int)
        min_score = request.args.get('min_score', default=0.0, type=float)
        
        anomalies = await storage.get_anomalies(hours=hours, min_score=min_score)
        return jsonify({
            'anomalies': anomalies,
            'count': len(anomalies)
        })
    
    @app.route("/api/v1/generate-tests/bulk", methods=["POST"])
    async def generate_tests_bulk():
        """Generate test cases in bulk"""
        test_generator = TestGenerator()
        data = request.get_json()
        test_cases = await test_generator.generate_bulk(data)
        return jsonify(test_cases)


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
            hours = request.json.get('hours', 24)
            worker = BackgroundWorker(storage, TestGenerator())
            results = await worker.run_analysis(hours=24)            
            return jsonify({
                'status': 'success',
                'message': f'Started analysis job for past {hours} hours'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/v1/analysis/job-status/<int:job_id>', methods=['GET'])
    async def get_job_status(job_id):
        """Get the status of a job"""
        session = storage.Session()
        try:
            job = session.query(Job).get(job_id)
            if not job:
                return jsonify({
                    'status': 'error',
                    'message': 'Job not found'
                }), 404
                
            response = {
                'job_id': job.id,
                'status': job.status,
                'created_at': job.created_at.isoformat(),
                'updated_at': job.updated_at.isoformat()
            }
            
            if job.status == 'completed':
                response['result'] = job.result
            elif job.status == 'failed':
                response['error'] = job.error_message
                
            return jsonify(response)
        finally:
            session.close()

    
    return app



if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=7071)
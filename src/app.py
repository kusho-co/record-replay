from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from .config import Config
from .storage.mysql import MySQLStorage
from .services.traffic import TrafficService
from .analysis.analyzer import RequestAnalyzer
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

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
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=7071)
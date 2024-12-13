from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from .config import Config
from .storage.mysql import MySQLStorage
from .services.traffic import TrafficService

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

    return app
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from .config import Config
from .storage.mysql import MySQLStorage
from .services.traffic import TrafficService
from .analysis.analyzer import RequestAnalyzer
import logging
from .analysis.deduplicator import deduplicate_events
from .analysis.cluster import cluster_events
from .analysis.dedupe import DedupeAnalyzer

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
    

    @app.get("/deduplicate")
    async def deduplicate(start_time: str, end_time: str):
        """
        Deduplicate events within the specified time range.
        :param start_time: Start time in ISO format (e.g., '2023-12-20T00:00:00')
        :param end_time: End time in ISO format (e.g., '2023-12-20T23:59:59')
        :return: List of unique events.
        """
        try:
            # Convert string to datetime
            # start_dt = datetime.fromisoformat(start_time)
            # end_dt = datetime.fromisoformat(end_time)

            # Fetch deduplicated events
            # deduplicated_events = await storage.get_deduplicated_events(start_dt, end_dt)
            # Fetch events from storage within the specified time range

            #######
            events = await storage.get_analytics(start_time, end_time)

            # Call the deduplication function
            deduplicated_events = deduplicate_events(events)

            return {"deduplicated_events": deduplicated_events}
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route("/api/v1/cluster", methods=["POST"])
    async def cluster():
        """
        Cluster API events within a given time range and return clusters.
        """
        try:
            # Parse input data
            data = request.get_json()
            start_time = datetime.fromisoformat(data["start_time"])
            end_time = datetime.fromisoformat(data["end_time"])
            num_clusters = int(data.get("num_clusters", 5))

            # Fetch events from storage
            events = await storage.get_deduplicated_events(start_time, end_time)

            # Ensure payloads are valid
            events = [event for event in events if event["payload"]]

            if not events:
                return jsonify({"message": "No valid events found for clustering"}), 400

            # Cluster events
            clustered_events = cluster_events(events, num_clusters=num_clusters)

            # Return the clustered data
            return jsonify({"clusters": clustered_events}), 200

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
        
    
    @app.route('/api/v1/dedupe', methods=['POST'])
    def dedupe_api():
        try:
            # Get the request payload
            payload = request.json
            start_time = datetime.fromisoformat(payload.get('start_time'))
            end_time = datetime.fromisoformat(payload.get('end_time'))

            # Fetch data from storage
            storage = MySQLStorage(connection_uri="mysql://user:password@localhost/db")
            data = storage.get_deduplication_data(start_time, end_time)

            # Initialize and train the deduplication analyzer
            # Define the fields for deduplication
            DEDUPLICATION_FIELDS = [
                {'field': 'path', 'type': 'String'},
                {'field': 'method', 'type': 'Exact'},
                {'field': 'request_body', 'type': 'Text'}
            ]

            dedupe_analyzer = DedupeAnalyzer(fields=DEDUPLICATION_FIELDS)
            dedupe_analyzer.train(data)

            # Perform clustering
            clusters = dedupe_analyzer.cluster(data)

            # Format and return results
            response = [
                {"record_ids": cluster[0], "similarity_score": cluster[1]}
                for cluster in clusters
            ]

            return jsonify({"clusters": response})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=7071)
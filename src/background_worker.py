# background_worker.py
from datetime import datetime, timedelta
import logging
from typing import Dict
from .models import Job, EndpointTestCase
from .analysis.analyzer import RequestAnalyzer
import json

logger = logging.getLogger(__name__)

class BackgroundWorker:
    def __init__(self, storage, test_generator):
        self.storage = storage
        self.test_generator = test_generator
        logger.info("Initialized Worker")

    async def run_analysis(self, hours: int) -> Dict:
        """Run analysis and return results directly"""
        logger.info(f"Starting analysis for past {hours} hours")
        session = self.storage.Session()
        processed_count = 0
        
        try:
            logger.debug(f"Fetching anomalies for past {hours} hours")
            anomalies = await self.storage.get_anomalies_by_endpoint(hours=hours)
            logger.info(f"Found {len(anomalies)} anomalies to analyze")

            for anomaly in anomalies:
                if anomaly.reference_events:
                    logger.debug(f"Processing anomaly ID: {anomaly.id} with {len(anomaly.reference_events)} reference events")
                    
                    for ref_event in anomaly.reference_events:
                        url = ref_event.get("path")
                        http_method = ref_event.get("method")
                        
                        endpoint_data = {
                            "url": url,
                            "http_method": http_method,
                            "request_body": ref_event.get("request_body"),
                            "status": ref_event.get("status"),
                            "timestamp": ref_event.get("timestamp")
                        }
                        
                        try:
                            async for test_case_chunk in self.test_generator.generate_streaming(endpoint_data):
                                if test_case_chunk != "[DONE]":
                                    try:
                                        test_case_raw = json.loads(test_case_chunk)
                                        
                                        # Format the test case according to the specified structure
                                        formatted_test_case = {
                                            "description": test_case_raw.get("description", "Generated test case"),
                                            "category": test_case_raw.get("category", "functional"),
                                            "priority": test_case_raw.get("priority", "medium"),
                                            "request": {
                                                "method": http_method,
                                                "url": url,
                                                "headers": test_case_raw.get("headers", {}),
                                                "path_params": test_case_raw.get("path_params", {}),
                                                "query_params": test_case_raw.get("query_params", {}),
                                                "body": test_case_raw.get("body", {})
                                            }
                                        }

                                        # Store the test case immediately
                                        await self.storage.store_test_case(
                                            url=url,
                                            http_method=http_method,
                                            test_case=formatted_test_case
                                        )
                                        processed_count += 1

                                    except json.JSONDecodeError as e:
                                        logger.warning(f"Failed to parse test case chunk for anomaly {anomaly.id}: {e}")
                        except Exception as e:
                            logger.error(f"Error generating test cases for anomaly {anomaly.id}: {e}")
                            continue
                    
        except Exception as e:
            logger.error(f"Error in analysis: {str(e)}", exc_info=True)
            raise
        finally:
            session.close()
            
        return {
            'total_test_cases_generated': processed_count,
            'status': 'completed'
        }
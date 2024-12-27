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
        all_results = []
        
        try:
            # Get unique endpoints
            logger.debug(f"Fetching unique endpoints for past {hours} hours")
            endpoints = await self.storage.get_unique_endpoints(hours)
            logger.info(f"Found {len(endpoints)} unique endpoints to analyze")
            
            # Process each endpoint
            for path, method in endpoints:
                logger.info(f"Processing endpoint: {method} {path}")
                
                # Get recent events
                events = await self.storage.get_events_by_endpoint(
                    path=path,
                    method=method,
                    start_time=datetime.now() - timedelta(hours=hours),
                    end_time=datetime.now()
                )
                
                # Prepare endpoint data
                endpoint_data = {
                    "url": path,
                    "http_method": method,
                    "samples": [self._format_event(event) for event in events[:5]],
                }
                
                # Generate test cases
                endpoint_test_cases = []
                current_test_case = ""
                
                async for test_case_chunk in self.test_generator.generate_streaming(endpoint_data):
                    # logger.info(f"this is the test case recieved from generator, {test_case_chunk}")
                    
                    if test_case_chunk != "[DONE]":
                        try:
                            test_case = json.loads(test_case_chunk)
                            endpoint_test_cases.append(test_case)
                        except Exception as e:
                            logger.warning(f"Failed to parse accumulated test case: {current_test_case}, {e}")
                
                # Add endpoint result if we have test cases

                if endpoint_test_cases:
                    endpoint_result = {
                        "endpoint": path,
                        "method": method,
                        "test_cases": endpoint_test_cases
                    }
                    all_results.append(endpoint_result)
                    
                
        except Exception as e:
            logger.error(f"Error in analysis: {str(e)}", exc_info=True)
            raise
        finally:
            session.close()
            
        return {
            'endpoints_processed': len(endpoints),
            'total_test_cases': sum(len(endpoint['test_cases']) for endpoint in all_results),
            'results': all_results
        }
    def _format_event(self, event):
        """Format event data for test generation"""
        return {
            "path": event.path,
            "method": event.method,
            "headers": event.headers,
            "path_params": event.path_params,
            "query_params": event.query_params,
            "request_body": event.request_body,
            "status": event.status,
            "response_headers": event.response_headers
        }
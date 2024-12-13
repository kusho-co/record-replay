from typing import Dict, Any, List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import json
import logging

# Configure logger
logger = logging.getLogger(__name__)

class RequestVectorizer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            analyzer='char',
            ngram_range=(3, 5),
            lowercase=True
        )
        self.fitted = False
        logger.info("RequestVectorizer initialized")

    def _flatten_json(self, data: Any, prefix: str = '') -> Dict[str, str]:
        """Flatten nested JSON into key-value pairs."""
        items: List = []
        
        if data is None:
            logger.debug("Received None data to flatten")
            return {}
            
        if not isinstance(data, dict):
            try:
                result = {prefix: str(data)} if prefix else {'value': str(data)}
                logger.debug("Flattened non-dict data: %s", result)
                return result
            except:
                logger.warning("Failed to convert data to string", exc_info=True)
                return {}

        for k, v in data.items():
            new_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.extend(self._flatten_json(v, new_key).items())
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        items.extend(self._flatten_json(item, f"{new_key}.{i}").items())
                    else:
                        items.append((f"{new_key}.{i}", str(item)))
            else:
                items.append((new_key, str(v)))
        return dict(items)

    def _request_to_string(self, request_data: Dict[str, Any]) -> str:
        """Convert entire request data to a string representation."""
        logger.debug("Converting request to string representation")
        parts = []
        
        # Add path and method
        path = request_data.get('path', '')
        method = request_data.get('method', '')
        parts.append(f"path:{path}")
        parts.append(f"method:{method}")
        
        # Process request body
        body_flat = self._flatten_json(request_data.get('body', {}))
        parts.extend(f"body.{k}:{v}" for k, v in body_flat.items())
        
        # Process query parameters
        query_flat = self._flatten_json(request_data.get('query_params', {}))
        parts.extend(f"query.{k}:{v}" for k, v in query_flat.items())
        
        # Process headers
        headers = request_data.get('headers', {})
        for header, value in headers.items():
            parts.append(f"header.{header}:{value}")
        
        result = ' '.join(sorted(parts))
        logger.debug("Request string length: %d", len(result))
        return result

    def fit_transform(self, requests: List[Dict[str, Any]]) -> np.ndarray:
        """Convert a list of requests into vectors."""
        try:
            logger.info("Vectorizing %d requests", len(requests))
            string_requests = [self._request_to_string(req) for req in requests]
            
            if all(not s for s in string_requests):
                logger.warning("All requests produced empty strings")
                return np.zeros((len(requests), 1))
                
            logger.debug("Average request string length: %.2f", 
                        sum(len(s) for s in string_requests) / len(string_requests))
            
            vectors = self.vectorizer.fit_transform(string_requests)
            self.fitted = True
            
            logger.info("Vectorization complete. Shape: %s", vectors.shape)
            return vectors.toarray()
            
        except Exception as e:
            logger.error("Error in fit_transform: %s", str(e), exc_info=True)
            return np.zeros((len(requests), 1))
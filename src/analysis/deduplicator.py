from datetime import datetime
from typing import List, Dict, Any, Optional
from fuzzywuzzy import fuzz
import logging

# Configure logger
logger = logging.getLogger(__name__)

def calculate_similarity(payload1: Dict[str, Any], payload2: Dict[str, Any]) -> float:
    """Calculate the similarity between two payloads using Levenshtein distance."""
    str1 = str(payload1)
    str2 = str(payload2)
    similarity_score = fuzz.ratio(str1, str2) / 100.0  # Normalize to [0, 1]
    return similarity_score

def deduplicate_events(events: List[Dict[str, Any]], similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
    """
    Deduplicate events based on semantic similarity of their payloads.
    
    Args:
        events: List of API events, each represented as a dictionary.
        similarity_threshold: Threshold for considering two payloads as similar.
        
    Returns:
        List of deduplicated events.
    """
    deduplicated_events = []
    seen_payloads = set()

    for event in events:
        current_payload = event.get('request_body', {})
        payload_str = str(current_payload)

        # Check if the current payload is similar to any previously seen payloads
        is_similar = False
        for seen_payload in seen_payloads:
            if calculate_similarity(current_payload, seen_payload) >= similarity_threshold:
                is_similar = True
                break

        # If not similar to any seen payload, add it to deduplicated events
        if not is_similar:
            deduplicated_events.append(event)
            seen_payloads.add(payload_str)

    logger.info("Deduplication complete. Original count: %d, Deduplicated count: %d", len(events), len(deduplicated_events))
    return deduplicated_events

if __name__ == "__main__":
    # Example usage
    example_events = [
        {
            "timestamp": datetime.now().isoformat(),
            "path": "/api/users",
            "method": "POST",
            "request_body": {"name": "John Doe", "age": 30},
            "status": "200",
        },
        {
            "timestamp": datetime.now().isoformat(),
            "path": "/api/users",
            "method": "POST",
            "request_body": {"name": "Jane Doe", "age": 25},
            "status": "200",
        },
        {
            "timestamp": datetime.now().isoformat(),
            "path": "/api/users",
            "method": "POST",
            "request_body": {"name": "John Doe", "age": 30},  # Duplicate payload
            "status": "200",
        },
    ]

    deduplicated = deduplicate_events(example_events)
    print(deduplicated)

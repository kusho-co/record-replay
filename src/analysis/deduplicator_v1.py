from fuzzywuzzy import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class APIDeduplicator:
    def __init__(self, similarity_threshold=0.7, fuzzy_threshold=80):
        self.similarity_threshold = similarity_threshold  # Cosine similarity threshold
        self.fuzzy_threshold = fuzzy_threshold            # Fuzzy matching threshold

    def _compute_fuzzy_similarity(self, text1, text2):
        """Compute similarity between two strings using Levenshtein distance."""
        return fuzz.ratio(text1, text2)

    def _compute_semantic_similarity(self, payloads):
        """Compute semantic similarity using TF-IDF and cosine similarity."""
        # Convert payloads to strings (handles JSON/dict structures)
        payload_strings = [str(payload) for payload in payloads]
        vectorizer = TfidfVectorizer().fit_transform(payload_strings)
        similarity_matrix = cosine_similarity(vectorizer)
        return similarity_matrix

    def deduplicate(self, events):
        """
        Deduplicate API events based on semantic and fuzzy matching.
        
        Args:
            events (List[Dict]): List of events containing 'payload' and 'id'.
            
        Returns:
            List[Dict]: List of unique events.
        """
        unique_events = []
        seen_event_ids = set()

        # Extract payloads and compute semantic similarity
        payloads = [event['payload'] for event in events]
        similarity_matrix = self._compute_semantic_similarity(payloads)

        for i, event in enumerate(events):
            if event['id'] in seen_event_ids:
                continue

            is_duplicate = False
            for j, other_event in enumerate(events):
                if i == j or other_event['id'] in seen_event_ids:
                    continue

                # Check cosine similarity
                semantic_similarity = similarity_matrix[i][j]
                if semantic_similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break

                # Check fuzzy matching for simpler cases
                fuzzy_similarity = self._compute_fuzzy_similarity(
                    str(event['payload']), str(other_event['payload'])
                )
                if fuzzy_similarity >= self.fuzzy_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_events.append(event)
                seen_event_ids.add(event['id'])

        return unique_events

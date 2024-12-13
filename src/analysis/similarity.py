import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Tuple
from .vectorizer import RequestVectorizer

class SimilarityAnalyzer:
    def __init__(self, similarity_threshold: float = 0.8):
        self.vectorizer = RequestVectorizer()
        self.similarity_threshold = similarity_threshold

    def find_anomalies(
        self, 
        requests: List[Dict[str, Any]]
    ) -> List[Tuple[int, float, List[int]]]:
        """
        Find anomalous requests based on cosine similarity.
        Returns: List of (index, similarity_score, [similar_indices])
        """
        if not requests or len(requests) < 2:  # Need at least 2 requests to compare
            return []

        try:
            # Convert requests to vectors
            vectors = self.vectorizer.fit_transform(requests)
            
            # Calculate pairwise similarities
            similarities = cosine_similarity(vectors)
            
            anomalies = []
            for i in range(len(requests)):
                # Get similarities for this request (excluding self-similarity)
                request_similarities = similarities[i].copy()  # Make a copy to modify
                request_similarities[i] = 0  # Exclude self-similarity
                
                # Find most similar requests
                similar_indices = np.where(request_similarities > self.similarity_threshold)[0]
                
                if len(similar_indices) < 3:  # Consider as anomaly if less than 3 similar requests
                    max_similarity = float(np.max(request_similarities))  # Convert to Python float
                    similar_indices = np.argsort(request_similarities)[-3:]  # Get top 3 similar
                    anomalies.append((i, max_similarity, similar_indices.tolist()))
            
            return anomalies
        except Exception as e:
            print(f"Error in find_anomalies: {str(e)}")
            return []
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from typing import List, Dict


def cluster_events(events: List[Dict], num_clusters: int = 5) -> List[List[Dict]]:
    """
    Cluster API events based on their payloads using KMeans.

    Args:
        events: A list of events where each event contains an 'id' and 'payload'.
        num_clusters: The number of clusters to create.

    Returns:
        A list of clusters, where each cluster is a list of events.
    """
    # Extract payloads for clustering
    payloads = [event["payload"] for event in events]

    # Convert payloads to TF-IDF features
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(payloads)

    # Perform KMeans clustering
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    labels = kmeans.fit_predict(tfidf_matrix)

    # Group events into clusters based on labels
    clusters = [[] for _ in range(num_clusters)]
    for event, label in zip(events, labels):
        clusters[label].append(event)

    return clusters

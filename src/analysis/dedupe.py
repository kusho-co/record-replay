import dedupe
from typing import List, Dict

class DedupeAnalyzer:
    def __init__(self, fields: List[Dict[str, str]]):
        """
        Initialize the Dedupe analyzer with the specified fields and their types.
        :param fields: List of dictionaries with field names and types.
        """
        self.deduper = dedupe.Dedupe(fields)

    def train(self, data: Dict[int, Dict[str, str]], sample_size: int = 150):
        """
        Train the Dedupe model with provided data.
        :param data: Dictionary of data with unique IDs as keys.
        :param sample_size: Number of samples for active learning.
        """
        self.deduper.sample(data, sample_size)
        dedupe.console_label(self.deduper)  # User labels the examples interactively
        self.deduper.train()

    def cluster(self, data: Dict[int, Dict[str, str]], threshold: float = 0.5):
        """
        Cluster the data into groups of duplicates.
        :param data: Dictionary of data with unique IDs as keys.
        :param threshold: Similarity score threshold for clustering.
        :return: List of clusters with record IDs and scores.
        """
        return self.deduper.match(data, threshold=threshold)

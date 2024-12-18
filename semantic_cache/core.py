from datetime import datetime

CACHE_THRESHOLD = 0.9

class SemanticCache:
    def __init__(self, flowerDb, dbSemanticCacheCollection: str):
        self.collection = flowerDb[dbSemanticCacheCollection]

    def search_in_cache(self, query_embedding):
        """
        Searches for a response in the cache that is similar to the provided query embedding vector.

        Args:
            query_embedding (list or np.array): The embedding vector representing the query.

        Returns:
            response (str or None): The cached response if found and if the similarity score is above the CACHE_THRESHOLD; otherwise, returns None.
        """

        results = self.collection.aggregate([
            {
                "$vectorSearch": {
                    "index": "cache_vector_index",
                    "queryVector": query_embedding,
                    "path": "query_embedding",
                    "numCandidates": 10,
                    "limit": 1
                }
            },
            {
                "$unset": "query_embedding"
            },
            {
                "$project": {
                    "_id": 0,
                    "score": { "$meta": "vectorSearchScore" },
                    "response": 1
                }
            }
        ])
        result = next(results, None)
        if result and result['score'] > CACHE_THRESHOLD:
            print(result['score'])
            return result['response']
        return None

    def add_to_cache(self, query_embedding, response):
        """
        Adds a new entry to the cache with the given query embedding and response.

        Args:
            query_embedding (list: The embedding vector representing the query.
            response (str): The response t or np.array)o be cached.
        """
        cache_document = {
            "query_embedding": query_embedding,
            "response": response,
            "timestamp": datetime.now()
        }
        self.collection.insert_one(cache_document)



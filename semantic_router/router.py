import numpy as np
from sentence_transformers import SentenceTransformer

class SemanticRouter():
    def __init__(self, routes):
        """
        Initializes the SemanticRouter with specified routes and precomputes embeddings for each route.

        Args:
            routes (list): A list of route objects, where each route has a `name` and `samples` attributes.
                           `samples` should be a list of text samples associated with the route.
        """
        self.routes = routes
        self.embedding = SentenceTransformer("keepitreal/vietnamese-sbert")
        self.routesEmbedding = {}
        
        # Encode and store embeddings for each route based on its sample texts
        for route in self.routes:
            self.routesEmbedding[
                route.name
            ] = self.embedding.encode(route.samples)
    
    def get_route(self):
        """
        Returns the available routes.

        Returns:
            list: A list of route objects initialized in the SemanticRouter.
        """
        return self.routes
    
    def guide(self, query):
        """
        Determines the best-matching route for a given query by calculating the similarity score.

        Args:
            query (str): The user query as a string.

        Returns:
            tuple: A tuple containing the highest similarity score and the name of the best-matching route.
        """
        # Encode the query and normalize its embedding
        queryEmbedding = self.embedding.encode([query])
        queryEmbedding = queryEmbedding / np.linalg.norm(queryEmbedding)
        scores = []

        # Calculate similarity scores for each route
        for route in self.routes:
            routesEmbedding = self.routesEmbedding[route.name]/np.linalg.norm(self.routesEmbedding[route.name])
            score = np.mean(np.dot(routesEmbedding, queryEmbedding.T).flatten())
            scores.append((score, route.name))

        # Sort scores in descending order and return the best match
        scores.sort(reverse=True)
        return scores[0]
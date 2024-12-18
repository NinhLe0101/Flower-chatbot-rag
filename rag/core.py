import pymongo
from IPython.display import Markdown
import textwrap
import re

class RAG:
    def __init__(self,
                flowerDb, 
                dbCollection_data: str, 
                dbCollection_vectorsearch: str):
        self.collection_data = flowerDb[dbCollection_data]
        self.collection_vectorsearch = flowerDb[dbCollection_vectorsearch]
        # self.llm = llm
        
    def keyword_search(self, user_query: str, limit=30):
        """
        Performs a keyword search on the content field within the data collection.

        Args:
            user_query (str): The search query provided by the user.
            limit (int): The maximum number of results to return (default is 30).

        Returns:
            list: A list of titles from the search results.
        """
        keyword_results = self.collection_data.aggregate([
            {
                "$search": {
                    "index": "keyword_search",
                    "text": {
                        "query": user_query,
                        "path": "content"
                    }
                }
            },
            { "$limit": limit }
        ])
        print(keyword_results)
        return [item['title'] for item in keyword_results]
    

    def title_search(self, user_query: str):
        """
        Searches for a document with a title matching the user query.

        Args:
            user_query (str): The search query provided by the user.

        Returns:
            list: A list of documents with matching titles.
        """
        keyword_results = self.collection_data.aggregate([
            {
                "$search": {
                    "index": "keyword_search",
                    "text": {
                        "query": user_query,
                        "path": "title"  
                    }
                }
            },
            { "$limit": 1 }
        ])
        print(keyword_results)
        return list(keyword_results)
        
    
    def prefilter_and_vector_search(self, user_query: str, query_embedding: list, limit=30):
        """
        Combines keyword filtering with vector similarity search to refine the results.

        Args:
            user_query (str): The search query provided by the user.
            query_embedding (list): The embedding vector for the query.
            limit (int): The maximum number of results to return (default is 30).

        Returns:
            list: A list of titles with the highest frequency of appearance in the results.
        """
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_search_index",
                    "queryVector": query_embedding,
                    "path": "embedding",
                    "numCandidates": 400,
                    "limit": limit,
                    "filter": {
                        "title": {"$in": self.keyword_search(user_query=user_query)}
                    }
                }
            },
            {
                "$group": {
                    "_id": "$title",
                    "count": { "$sum": 1 }
                }
            },
            {
                "$sort": { "count": -1 }
            },

            {
                "$unset": "embedding"
            },
            {
                "$project": {
                    "_id": 0,
                    "title": "$_id",
                    "count": 1
            }}
        ]


        # Execute the search
        search_results = list(self.collection_vectorsearch.aggregate(pipeline))
        print(search_results)

        # Find the maximum count
        max_count = max(item['count'] for item in search_results)

        results = []
        for item in search_results:
            if item['count'] == max_count:
                results.append(item['title'])

        return results
        # return results[0]
    
    def get_search_results(self, user_query: str, query_embedding: list):
        """
        Retrieves search results by checking if the query matches specific patterns or performing vector search.

        Args:
            user_query (str): The search query provided by the user.
            query_embedding (list): The embedding vector for the query.

        Returns:
            list or None: A list of documents that match the search results or None if not found.
        """
        # If the query contains "m" or "M" followed by a number, search by title
        pattern = r'[mM]\d+'
        if re.search(pattern, user_query) and self.title_search(user_query):
            # Nếu query chứa "m" hoặc "M" và số, tìm kiếm tiêu đề có chứa chuỗi này
            return self.title_search(user_query)
        else:
            vectorsearch_result = self.prefilter_and_vector_search(user_query, query_embedding)
            return list(self.collection_data.find({"title": {"$in": vectorsearch_result}}))
            # return list(self.collection_data.find({"title": vectorsearch_result}))

    def enhance_prompt(self, user_query: str, query_embedding: list):
        """
        Enhances the user query by adding related content details from the database.

        Args:
            user_query (str): The search query provided by the user.
            query_embedding (list): The embedding vector for the query.

        Returns:
            str: An enhanced prompt with additional information for the language model.
        """
        get_knowledge = self.get_search_results(user_query, query_embedding)
        if get_knowledge:
            enhanced_prompt = ""
            for i, result in enumerate(get_knowledge, start=1):
                enhanced_prompt += f"\n {i}) Tên: {result.get('title', 'A')}"
                enhanced_prompt += f", Nội dung: {result.get('content', '')}"
                enhanced_prompt += f", Giá gốc: {result.get('original_price', '')}"
                enhanced_prompt += f", Giá khuyến mãi: {result.get('discounted_price', '')}"
                if result.get('image_urls'):
                    enhanced_prompt += f", Hình ảnh: {', '.join(result['image_urls'])}"
            print(enhanced_prompt)
            return enhanced_prompt
 
import os
from dotenv import load_dotenv
import pandas as pd
import pymongo
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import re

# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables for database and API configuration
MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('DB_NAME')
COLLECTION_FLOWER_DATA = os.getenv('DB_COLLECTION_DATA')

mongoClient = pymongo.MongoClient(MONGODB_URI)
mongoFlowerDB = mongoClient[DB_NAME]
collectionFlowerData = mongoFlowerDB[COLLECTION_FLOWER_DATA]

# Retrieve data from MongoDB
data = list(collectionFlowerData.find())
df = pd.DataFrame(data)
df.drop('url', axis=1, inplace=True)

# Xóa các dòng trong df có index thuộc null_rows
null_rows = df[df.isnull().any(axis=1)]
df = df.drop(null_rows.index)

model = SentenceTransformer('keepitreal/vietnamese-sbert')

def semantic_splitting(text, thresold=0.2):
    sentences = re.split(r'(?<=[.!?]) +', text)
    sentences = [sen.strip() for sen in sentences if sen.strip()]

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(sentences)
    vectors = tfidf_matrix.toarray()

    similarity_matrix = cosine_similarity(vectors)

    chunks = [[sentences[0]]]
    for i in range(1, len(sentences)):
        sim_score = similarity_matrix[i-1, i]
        if sim_score >= thresold:
            chunks[-1].append(sentences[i])
        else:
            chunks.append([sentences[i]])

    return [" ".join(chunk) for chunk in chunks]

def get_embedding(text):
    embedding = model.encode(text)
    return embedding.tolist()

df_for_vectorsearch = pd.DataFrame()

for index, row in df.iterrows():
    chunks = semantic_splitting(row['content'])
    for idx, chunk in enumerate(chunks):
      print(f"Chunk {idx+1}: {chunk}")
      new_row = pd.DataFrame({
          'title': [row['title']],
          'chunk_content': [chunk],
          'embedding': [get_embedding(chunk)]
          })
      df_for_vectorsearch = pd.concat([df_for_vectorsearch, new_row], ignore_index=True)

vectorsearch_collection = mongoFlowerDB["data_for_vectorsearch"]

documents = df_for_vectorsearch.to_dict("records")
vectorsearch_collection.insert_many(documents)
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import Column, Integer, String, create_engine, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util
import os
from dotenv import load_dotenv
import mysql.connector
import numpy as np

app = FastAPI()
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with the actual origin if different
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
load_dotenv()

def createConnection():
    try:
        host = os.getenv('DB_HOST')
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASS')
        database = os.getenv('DB_NAME')
        port = os.getenv("DB_PORT", "3306")
        
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
        DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        return connection, DATABASE_URL

    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None, None 

# SQLAlchemy engine setup
def get_db():
    connection, DATABASE_URL = createConnection()
    db = sessionmaker(bind=create_engine(DATABASE_URL))()
    try:
        yield db
    finally:
        db.close()

Base = declarative_base()

class Venues(Base):
    __tablename__ = 'venues'
    id = Column(String(12), primary_key=True)
    name = Column(String(255), nullable=False)
    city = Column(String(50))
    zipcode = Column(Integer)
    phone = Column(Integer)
    capacity = Column(Integer)
    style = Column(String(100))
    keywords = Column(Text)

def calculate_weighted_match_score(user_input, venue, model):
    weights = {
        'capacity': 0.3,
        'city': 0.2,
        'style': 0.3,
        'keywords': 0.2,
    }
    match_score = 0
    max_score = sum(weights.values())

    # 1. Capacity Comparison (Numeric Range Matching)
    if user_input.get('capacity') and venue.capacity:
        try:
            user_capacity = user_input['capacity'].split('-')
            user_min_capacity = int(user_capacity[0])
            user_max_capacity = int(user_capacity[1]) if len(user_capacity) > 1 else user_min_capacity
            venue_capacity = venue.capacity

            if user_min_capacity <= venue_capacity <= user_max_capacity:
                capacity_similarity = 1  # Perfect match
            else:
                capacity_similarity = 1 - min(abs(venue_capacity - user_min_capacity), 
                                              abs(venue_capacity - user_max_capacity)) / max(user_max_capacity, venue_capacity)

            capacity_similarity = max(0, capacity_similarity)  # Ensure it's non-negative
            match_score += capacity_similarity * weights['capacity']
        except ValueError:
            print("Capacity input format is invalid.")

    # 2. City Comparison (Improved Semantic Similarity)
    if user_input.get('city') and venue.city:
        city_similarity = util.pytorch_cos_sim(
            model.encode(user_input['city'].lower()), 
            model.encode(venue.city.lower())
        ).item()
        match_score += city_similarity * weights['city']

    # 3. Style Comparison (Multi-label Classification)
    if user_input.get('style') and venue.style:
        user_styles = set(user_input['style'].lower().split(','))
        venue_styles = set(venue.style.lower().split(','))
        style_overlap = len(user_styles.intersection(venue_styles))
        style_similarity = style_overlap / max(len(user_styles), len(venue_styles))
        match_score += style_similarity * weights['style']

    # 4. Keywords Comparison (Multi-label Classification + Semantic Similarity)
    if user_input.get('keywords') and venue.keywords:
        user_keywords = set(user_input['keywords'].lower().split(','))
        venue_keywords = set(venue.keywords.lower().split(','))
        
        # Exact match score
        keyword_overlap = len(user_keywords.intersection(venue_keywords))
        exact_match_score = keyword_overlap / max(len(user_keywords), len(venue_keywords))
        
        # Semantic similarity score
        semantic_similarity = util.pytorch_cos_sim(
            model.encode(', '.join(user_keywords)),
            model.encode(', '.join(venue_keywords))
        ).item()
        
        # Combine exact match and semantic similarity
        keyword_similarity = (exact_match_score + semantic_similarity) / 2
        match_score += keyword_similarity * weights['keywords']

    # Normalize the final match score and apply a more lenient scaling
    normalized_score = match_score / max_score
    final_score = min(normalized_score * 1.5, 1.0)  # Apply a 1.5x multiplier, capped at 1.0

    return final_score  # Return as a percentage

@app.get("/venues/")
async def get_all_venues(db: Session = Depends(get_db)):
    venues = db.query(Venues).all()
    response = [
        {
            "id": v.id,
            "name": v.name,
            "city": v.city,
            "zipcode": v.zipcode,
            "phone": v.phone,
            "capacity": v.capacity,
            "style": v.style,
            "keywords": v.keywords
        }
        for v in venues
    ]
    return response

@app.get("/venues/search")
async def search_venues(
    capacity: str = None, city: str = None, style: str = None, keywords: str = None, db: Session = Depends(get_db)
):
    venues = db.query(Venues).all()

    user_input = {
        'capacity': capacity,
        'city': city,
        'style': style,
        'keywords': keywords,
    }

    for venue in venues:
        venue.match_score = calculate_weighted_match_score(user_input, venue, embedding_model)

    sorted_venues = sorted(venues, key=lambda v: v.match_score, reverse=True)

    response = [
        {
            "id": v.id,
            "name": v.name,
            "city": v.city,
            "zipcode": v.zipcode,
            "phone": v.phone,
            "capacity": v.capacity,
            "style": v.style,
            "keywords": v.keywords,
            "match_score": round(v.match_score * 100, 2)
        }
        for v in sorted_venues
    ]

    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

createConnection()
get_db()

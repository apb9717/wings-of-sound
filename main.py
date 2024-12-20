from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import Column, Integer, String, Text, LargeBinary, create_engine  # Added create_engine import
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util
import os
from dotenv import load_dotenv
import mysql.connector
import numpy as np
import base64
from PIL import Image
from io import BytesIO

app = FastAPI()
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://wings-frontend-server-498263212500.us-central1.run.app"],
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
    db = sessionmaker(bind=create_engine(DATABASE_URL))()  # Corrected here with create_engine import
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
    email = Column(String(100))
    inquiry_url = Column(String(100))
    capacity = Column(Integer)
    style = Column(String(100))
    keywords = Column(Text)
    photo = Column(String(255))  # Image URL for the venue


from sentence_transformers import util

def calculate_weighted_match_score(user_input, venue, model):
    weights = {
        'capacity': 0.3,
        'city': 0.2,
        'style': 0.3,
        'keywords': 0.2,  # Fine-tune this weight if necessary
    }
    match_score = 0
    max_score = sum(weights.values())

    # City Scoring
    city_similarity = 0
    if user_input.get('city') and venue.city:
        if user_input['city'].strip().lower() == venue.city.strip().lower():
            city_similarity = 1  # Exact city match
        else:
            city_similarity = 0
    match_score += city_similarity * weights['city']

    # Capacity Scoring
    if user_input.get('capacity') and venue.capacity:
        try:
            user_capacity = user_input['capacity']
            
            if '+' in user_capacity:
                user_min_capacity = int(user_capacity.replace('+', '').strip())
                user_max_capacity = float('inf')  # No upper limit
            else:
                user_min_capacity = int(user_capacity)
                user_max_capacity = user_min_capacity

            venue_capacity = venue.capacity

            if user_min_capacity <= venue_capacity <= user_max_capacity:
                capacity_similarity = 1
            elif venue_capacity < user_min_capacity:
                capacity_similarity = max(0, 1 - (user_min_capacity - venue_capacity) / user_min_capacity)
            else:
                capacity_similarity = max(0, 1 - (venue_capacity - user_max_capacity) / venue_capacity)

            match_score += capacity_similarity * weights['capacity']

        except ValueError:
            print("Capacity input format is invalid:", user_input['capacity'])

    # Style Scoring (Updated to support partial matches)
    if user_input.get('style') and venue.style:
        user_styles = user_input['style'].lower().split(',')
        venue_styles = venue.style.lower().split(',')
        
        # Matching substrings of user input in venue styles
        style_similarity = sum(1 for user_style in user_styles if any(user_style in venue_style for venue_style in venue_styles)) / len(user_styles)

        match_score += style_similarity * weights['style']

    # Keyword Scoring (Updated to support partial matches)
    if user_input.get('keywords') and venue.keywords:
        user_keywords = user_input['keywords'].lower().split(',')
        venue_keywords = venue.keywords.lower().split(',')
        
        # Matching substrings of user input in venue keywords
        keyword_similarity = sum(1 for user_keyword in user_keywords if any(user_keyword in venue_keyword for venue_keyword in venue_keywords)) / len(user_keywords)

        match_score += keyword_similarity * weights['keywords']

    # Normalize the score
    normalized_score = match_score / max_score
    final_score = min(normalized_score * 1.5, 1.0)  # Ensure score does not exceed 1.0

    return final_score



@app.get("/venues/")  # Get all venues with pagination
async def get_all_venues(db: Session = Depends(get_db)):
    # Fetch only necessary columns excluding 'photo'
    venues = db.query(
        Venues.id,
        Venues.name,
        Venues.city,
        Venues.zipcode,
        Venues.phone,
        Venues.email,
        Venues.capacity,
        Venues.style,
        Venues.keywords,
        Venues.inquiry_url,
        Venues.photo
    ).all()

    # Prepare the response with necessary venue details
    response = [{
        "id": v.id,
        "name": v.name,
        "city": v.city,
        "zipcode": v.zipcode,
        "phone": v.phone,
        "email": v.email,
        "capacity": v.capacity,
        "style": v.style,
        "keywords": v.keywords,
        "inquiry_url": v.inquiry_url,
        "photo": v.photo
    } for v in venues]

    return response


@app.get("/venues/search")  # Search venues based on user input
async def search_venues(
    capacity: str = None, city: str = None, style: str = None, keywords: str = None, db: Session = Depends(get_db)
):
    user_input = {
        'capacity': capacity,
        'city': city,
        'style': style,
        'keywords': keywords,
    }

    # Fetch venues
    venues = db.query(
        Venues.id,
        Venues.name,
        Venues.city,
        Venues.zipcode,
        Venues.phone,
        Venues.email,
        Venues.capacity,
        Venues.style,
        Venues.keywords,
        Venues.inquiry_url,
        Venues.photo  # Keep photo URL in the database
    ).all()

    # Filter venues by exact city match (if city is provided)
    if city:
        venues = [venue for venue in venues if venue.city.strip().lower() == city.strip().lower()]

    # Calculate match scores for all venues
    sorted_venues = []
    for venue in venues:
        match_score = calculate_weighted_match_score(user_input, venue, embedding_model)
        sorted_venues.append({
            "id": venue.id,
            "name": venue.name,
            "city": venue.city,
            "zipcode": venue.zipcode,
            "phone": venue.phone,
            "email": venue.email,
            "capacity": venue.capacity,
            "style": venue.style,
            "keywords": venue.keywords,
            "inquiry_url": venue.inquiry_url,
            "match_score": round(match_score * 100, 2),
            "photo": venue.photo  # Directly include the photo URL
        })

    # Sort by match score
    sorted_venues.sort(key=lambda v: v["match_score"], reverse=True)

    # Return the top 15 venues (still ordered by match score)
    return sorted_venues[:15]



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

createConnection()
get_db()

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


def calculate_weighted_match_score(user_input, venue, model):
    weights = {
        'capacity': 0.3,
        'city': 0.2,
        'style': 0.3,
        'keywords': 0.2,
    }
    match_score = 0
    max_score = sum(weights.values())

    # City Scoring
    city_similarity = 0
    if user_input.get('city') and venue.city:
        if user_input['city'].strip().lower() == venue.city.strip().lower():
            city_similarity = 1  # Perfect match
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

    # Style Scoring
    if user_input.get('style') and venue.style:
        user_styles = set(user_input['style'].lower().split(','))
        venue_styles = set(venue.style.lower().split(','))
        style_overlap = len(user_styles.intersection(venue_styles))
        style_similarity = style_overlap / max(len(user_styles), len(venue_styles))

        match_score += style_similarity * weights['style']

    # Keyword Scoring
    if user_input.get('keywords') and venue.keywords:
        user_keywords = set(user_input['keywords'].lower().split(','))
        venue_keywords = set(venue.keywords.lower().split(','))
        
        exact_match_score = len(user_keywords.intersection(venue_keywords)) / max(len(user_keywords), len(venue_keywords))
        semantic_similarity = util.pytorch_cos_sim(
            model.encode(', '.join(user_keywords)),
            model.encode(', '.join(venue_keywords))
        ).item()
        keyword_similarity = 0.7 * exact_match_score + 0.3 * semantic_similarity

        match_score += keyword_similarity * weights['keywords']

    # Normalize the score
    normalized_score = match_score / max_score
    final_score = min(normalized_score * 1.5, 1.0)  # Ensure score does not exceed 1.0

    return final_score


def process_image(photo):
    if photo:
        img = Image.open(BytesIO(photo))
        img = img.convert('RGB')
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    return None


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
        Venues.inquiry_url
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
        "inquiry_url": v.inquiry_url
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
        Venues.inquiry_url
    ).all()

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
            "photo": None  # Initially, no photo
        })

    # Sort by match score
    sorted_venues.sort(key=lambda v: v["match_score"], reverse=True)

    # Fetch the images for the top 15 venues
    venue_ids = [v['id'] for v in sorted_venues[:15]]  # Get the IDs of the top 15 venues
    venues_with_images = db.query(Venues.id, Venues.photo).filter(Venues.id.in_(venue_ids)).all()
    

    # Create a mapping of venue ID to image for quick lookup
    # venue_images = {v.id: process_image(v.photo) if v.photo else None for v in venues_with_images}
    
    # fixed venue_images, no need to process blob images 
    venue_images = {v.id: v.photo if v.photo else None for v in venues_with_images}

    # Add images to the response
    for venue in sorted_venues[:15]:
        venue["photo"] = venue_images.get(venue["id"])

    return sorted_venues[:15]  # Return top 15 venues


createConnection()
get_db()

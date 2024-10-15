# configure fastapi to work with mySQL using SQL Alchemy as the ORM
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import mysql.connector
from sqlalchemy import Column, Integer, String, BigInteger, Text




# Load environment variables from .env
load_dotenv()

def createConnection():
    """
    Establishes a connection to the MySQL database using credentials stored in environment variables.
    Returns a connection object and DATABASE_URL or (None, None) if the connection fails.
    """
    connection = None
    try:
        # Accessing environment variables
        host = os.getenv('DB_HOST')
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASS')
        database = os.getenv('DB_NAME')
        port = os.getenv("DB_PORT", "3306")  # Default MySQL port if not set
        
        print(f"Attempting to connect to:")
        print(f"Host: {host}")
        print(f"User: {user}")
        print(f"Database: {database}")

        # Establish the connection using MySQL credentials from the .env file
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
        print("Successfully connected to the database")

        # Construct the DATABASE_URL
        DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        return connection, DATABASE_URL  # Return the connection and DATABASE_URL

    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None, None 



# Create a SQLAlchemy engine using the DATABASE_URL
def get_db():
    connection, DATABASE_URL = createConnection()
    if connection is None:
        print("Connection failed")
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    # Create a sessionmaker bound to the connection
    db = sessionmaker(bind=create_engine(DATABASE_URL))()
    try:
        yield db
    finally:
        db.close()
        connection.close()
# SQLAlchemy database setup
Base = declarative_base()

class Venues(Base):
    __tablename__ = 'venues'
    id = Column(String(12), primary_key=True)  # CHAR(12) as String(12)
    name = Column(String(255), nullable=False)  # VARCHAR(255)
    city = Column(String(50))  # VARCHAR(50)
    zipcode = Column(Integer)  # INT
    phone = Column(BigInteger)  # BIGINT
    capacity = Column(BigInteger)  # BIGINT
    style = Column(String(100))  # VARCHAR(100)
    keywords = Column(Text)

# Pydantic model for Venue (for request/response validation)
class VenueBase(BaseModel):
    name: str # name is not allowed to be null 
    city: str = None
    zipcode: int = None
    phone: int = None
    capacity: int = None
    style: str = None
    keywords: str = None

class VenueCreate(VenueBase):
    id: str  # Required for creating a new venue

class VenueUpdate(VenueBase):
    pass  # All fields are optional for updates

app = FastAPI()

### API Endpoints ###

# GET /venues/: Retrieve a list of all venues
@app.get("/venues/")
async def get_venues(db: Session = Depends(get_db)):
 try: 
    venues = db.query(Venues).all()
    return venues
 except Exception as e:
     # Log the exception and raise an HTTP error
    print(f"Error fetching venues: {e}")
    raise HTTPException(status_code=500, detail="Internal Server Error")

# GET /venues/{venue_id}: Retrieve a single venue by its ID
@app.get("/venues/{venue_id}")
async def get_venue(venue_id: str, db: Session = Depends(get_db)):
    venue = db.query(Venues).filter(Venues.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue

# POST /venues/: Create a new venue
@app.post("/venues/")
async def create_venue(venue: VenueCreate, db: Session = Depends(get_db)):
    existing_venue = db.query(Venues).filter(Venues.id == venue.id).first()
    if existing_venue:
        raise HTTPException(status_code=400, detail="Venue with this ID already exists.")
    new_venue = Venues(**venue.dict())
    db.add(new_venue)
    db.commit()
    db.refresh(new_venue)
    return new_venue

# PUT /venues/{venue_id}: Update an existing venue by its ID
@app.put("/venues/{venue_id}")
async def update_venue(venue_id: str, updated_venue: VenueUpdate, db: Session = Depends(get_db)):
    venue = db.query(Venues).filter(Venues.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    for key, value in updated_venue.dict(exclude_unset=True).items():
        setattr(venue, key, value)
    db.commit()
    db.refresh(venue)
    return venue

# DELETE /venues/{venue_id}: Delete a venue by its ID
@app.delete("/venues/{venue_id}")
async def delete_venue(venue_id: str, db: Session = Depends(get_db)):
    venue = db.query(Venues).filter(Venues.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    db.delete(venue)
    db.commit()
    return {"message": "Venue deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


createConnection()
get_db()
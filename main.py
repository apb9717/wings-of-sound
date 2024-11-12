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
from fastapi.middleware.cors import CORSMiddleware  # Import CORSMiddleware

# Load environment variables from .env
load_dotenv()

def createConnection():
    # Establishes a connection to the MySQL database using credentials stored in environment variables.
    connection = None
    try:
        host = os.getenv('DB_HOST')
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASS')
        database = os.getenv('DB_NAME')
        port = os.getenv("DB_PORT", "3306")  # Default MySQL port if not set
        
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

# Create a SQLAlchemy engine using the DATABASE_URL
def get_db():
    connection, DATABASE_URL = createConnection()
    if connection is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    db = sessionmaker(bind=create_engine(DATABASE_URL))()
    try:
        yield db
    finally:
        db.close()
        connection.close()

Base = declarative_base()

class Venues(Base):
    __tablename__ = 'venues'
    id = Column(String(12), primary_key=True)
    name = Column(String(255), nullable=False)
    city = Column(String(50))
    zipcode = Column(Integer)
    phone = Column(BigInteger)
    capacity = Column(BigInteger)
    style = Column(String(100))
    keywords = Column(Text)

class VenueBase(BaseModel):
    name: str
    city: str = None
    zipcode: int = None
    phone: int = None
    capacity: int = None
    style: str = None
    keywords: str = None

class VenueCreate(VenueBase):
    id: str

class VenueUpdate(VenueBase):
    pass

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.get("/venues/")
async def get_venues(db: Session = Depends(get_db)):
    try: 
        venues = db.query(Venues).all()
        return venues
    except Exception as e:
        print(f"Error fetching venues: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Additional endpoints can remain unchanged

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)



createConnection()
get_db()

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(String, unique=True, index=True)
    username = Column(String)
    ref_link = Column(String, unique=True)


class Referral(Base):
    __tablename__ = "referrals"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    user_tg_id = Column(String, ForeignKey("users.tg_id"))
    friend_tg_id = Column(String, ForeignKey("users.tg_id"))
    points = Column(Integer, default=0)


# Create tables
Base.metadata.create_all(bind=engine)


# Pydantic models for request/response
class UserCreate(BaseModel):
    tg_id: str
    username: str


class ReferralCreate(BaseModel):
    user_tg_id: str
    friend_tg_id: str


class UserResponse(BaseModel):
    tg_id: str
    username: str
    ref_link: str


class ReferralResponse(BaseModel):
    date: datetime
    user_tg_id: str
    friend_tg_id: str
    points: int


app = FastAPI(
    title="Referral System API",
    description="API for managing users and referrals in a Telegram bot referral system",
    version="1.0.0",
)


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper function to get or create user
def get_or_create_user(db: Session, tg_id: str, username: str):
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if not user:
        ref_link = f"https://t.me/tma123_bot?startapp={tg_id}"
        user = User(tg_id=tg_id, username=username, ref_link=ref_link)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# API routes
@app.post("/users/", response_model=UserResponse, tags=["Users"])
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user or get an existing user.

    - **tg_id**: Telegram ID of the user
    - **username**: Username of the user
    """
    return get_or_create_user(db, user.tg_id, user.username)


@app.get("/users/{tg_id}", response_model=UserResponse, tags=["Users"])
async def get_user(tg_id: str, db: Session = Depends(get_db)):
    """
    Get a user by their Telegram ID.

    - **tg_id**: Telegram ID of the user to retrieve
    """
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users/{tg_id}/friends", response_model=List[UserResponse], tags=["Users"])
async def get_user_friends(tg_id: str, db: Session = Depends(get_db)):
    """
    Get all friends (referrals) of a user.

    - **tg_id**: Telegram ID of the user whose friends to retrieve
    """
    referrals = db.query(Referral).filter(Referral.user_tg_id == tg_id).all()
    friend_ids = [referral.friend_tg_id for referral in referrals]
    friends = db.query(User).filter(User.tg_id.in_(friend_ids)).all()
    return friends


@app.post("/referrals/", response_model=ReferralResponse, tags=["Referrals"])
async def create_referral(referral: ReferralCreate, db: Session = Depends(get_db)):
    """
    Create a new referral relationship between two users.

    - **user_tg_id**: Telegram ID of the referring user
    - **friend_tg_id**: Telegram ID of the referred user
    """
    existing_referral = db.query(Referral).filter(
        Referral.user_tg_id == referral.user_tg_id,
        Referral.friend_tg_id == referral.friend_tg_id
    ).first()

    if existing_referral:
        raise HTTPException(status_code=400, detail="Referral already exists")

    new_referral = Referral(
        user_tg_id=referral.user_tg_id,
        friend_tg_id=referral.friend_tg_id,
        points=100  # You can adjust the points as needed
    )
    db.add(new_referral)
    db.commit()
    db.refresh(new_referral)
    return new_referral


@app.get("/users/{tg_id}/referral_link", tags=["Users"])
async def get_referral_link(tg_id: str, db: Session = Depends(get_db)):
    """
    Get the referral link for a user.

    - **tg_id**: Telegram ID of the user
    """
    user = db.query(User).filter(User.tg_id == tg_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"referral_link": user.ref_link}


@app.get("/users/{tg_id}/total_points", tags=["Users"])
async def get_total_points(tg_id: str, db: Session = Depends(get_db)):
    """
    Get the total points earned by a user through referrals.

    - **tg_id**: Telegram ID of the user
    """
    referrals = db.query(Referral).filter(Referral.user_tg_id == tg_id).all()
    total_points = sum(referral.points for referral in referrals)
    return {"total_points": total_points}
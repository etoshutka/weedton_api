from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from database import Base

class Referral(Base):
    __tablename__ = "referrals"
    id = Column(Integer, primary_key=True, index=True)
    user_tg_id = Column(Integer, index=True)
    friend_tg_id = Column(Integer, index=True)
    date = Column(DateTime, default=func.now())
    points = Column(Integer, default=100)
from datetime import datetime
from typing import List, Optional
from sqlalchemy import BigInteger, ForeignKey, String, Float, DateTime, Date, Boolean, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    submissions = relationship("Submission", back_populates="user")
    user_challenges = relationship("UserChallenge", back_populates="user")

class Challenge(Base):
    __tablename__ = "challenges"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # e.g., 'book', 'steps'
    target_unit: Mapped[str] = mapped_column(String(50), default="pages") # pages, steps, etc.
    time_window_start: Mapped[Optional[str]] = mapped_column(String(5)) # HH:MM
    time_window_end: Mapped[Optional[str]] = mapped_column(String(5)) # HH:MM
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    submissions = relationship("Submission", back_populates="challenge")
    user_challenges = relationship("UserChallenge", back_populates="challenge")

class UserChallenge(Base):
    __tablename__ = "user_challenges"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"))
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    max_streak: Mapped[int] = mapped_column(Integer, default=0)
    total_value: Mapped[float] = mapped_column(Float, default=0.0)
    is_joined: Mapped[bool] = mapped_column(Boolean, default=True)
    
    user = relationship("User", back_populates="user_challenges")
    challenge = relationship("Challenge", back_populates="user_challenges")

class Submission(Base):
    __tablename__ = "submissions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"))
    value: Mapped[float] = mapped_column(Float, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    date: Mapped[datetime.date] = mapped_column(Date, default=datetime.utcnow().date)
    
    user = relationship("User", back_populates="submissions")
    challenge = relationship("Challenge", back_populates="submissions")

class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="admin") # superadmin, admin

class WeeklyResult(Base):
    __tablename__ = "weekly_results"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"))
    week_start: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer)

class MonthlyResult(Base):
    __tablename__ = "monthly_results"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"))
    month: Mapped[str] = mapped_column(String(7), nullable=False) # YYYY-MM
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer)

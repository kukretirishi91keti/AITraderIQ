"""
Database models for TraderAI Pro.
Covers: Users, Watchlists, Portfolios, Alerts.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from database.engine import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    trader_style = Column(String(50), default="swing")  # day, swing, position, scalper
    risk_tolerance = Column(String(50), default="moderate")  # conservative, moderate, aggressive
    investment_horizon = Column(String(20), default="medium")  # short, medium, long
    experience_level = Column(String(20), default="intermediate")  # beginner, intermediate, advanced, expert
    capital_range = Column(String(20), default="medium")  # small, medium, large, institutional
    goals = Column(Text, default="[]")  # JSON array: income, growth, preservation, speculation
    is_active = Column(Boolean, default=True)
    # Subscription / payment tier
    plan = Column(String(20), default="free")  # free, pro, premium
    stripe_customer_id = Column(String(255), nullable=True)
    plan_expires_at = Column(DateTime, nullable=True)
    ai_queries_today = Column(Integer, default=0)
    ai_queries_reset_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    watchlist_items = relationship("WatchlistItem", back_populates="user", cascade="all, delete-orphan")
    portfolio_items = relationship("PortfolioItem", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    paper_trades = relationship("PaperTrade", back_populates="user", cascade="all, delete-orphan")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    market = Column(String(20), default="US")
    notes = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    added_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="watchlist_items")


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    shares = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    currency = Column(String(10), default="$")
    market = Column(String(20), default="US")
    notes = Column(Text, default="")
    added_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="portfolio_items")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    condition = Column(String(20), nullable=False)  # "above", "below", "rsi_above", "rsi_below"
    target_value = Column(Float, nullable=False)
    is_triggered = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="alerts")


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # "buy" or "sell"
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    status = Column(String(20), default="open")  # "open", "closed"
    strategy = Column(String(50), nullable=True)  # strategy name that triggered this
    market = Column(String(20), default="US")
    currency = Column(String(10), default="$")
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    notes = Column(Text, default="")
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="paper_trades")

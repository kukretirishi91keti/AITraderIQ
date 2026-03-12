"""
Database models for TraderAI Pro.
Covers: Users, Watchlists, Portfolios, Alerts, Credit Transactions.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database.engine import Base


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    trader_style = Column(String(50), default="swing")  # day, swing, position, scalper
    risk_tolerance = Column(String(50), default="moderate")  # conservative, moderate, aggressive
    is_active = Column(Boolean, default=True)
    tier = Column(String(20), default="free")  # free, starter, pro, unlimited
    credits_balance = Column(Integer, default=0)
    credits_granted_today = Column(Integer, default=0)
    credits_grant_date = Column(String(10), default="")  # YYYY-MM-DD for daily reset tracking
    lifetime_credits_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    watchlist_items = relationship("WatchlistItem", back_populates="user", cascade="all, delete-orphan")
    portfolio_items = relationship("PortfolioItem", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    credit_transactions = relationship("CreditTransaction", back_populates="user", cascade="all, delete-orphan")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    market = Column(String(20), default="US")
    notes = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    added_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="watchlist_items")


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    shares = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    currency = Column(String(10), default="$")
    market = Column(String(20), default="US")
    notes = Column(Text, default="")
    added_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="portfolio_items")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    condition = Column(String(20), nullable=False)  # "above", "below", "rsi_above", "rsi_below"
    target_value = Column(Float, nullable=False)
    is_triggered = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="alerts")


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # positive = credit, negative = debit
    balance_after = Column(Integer, nullable=False)
    tx_type = Column(String(30), nullable=False)  # daily_grant, ai_query, topup, bonus, refund
    description = Column(String(255), default="")
    metadata_json = Column(Text, default="{}")  # provider, model, symbol, etc.
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="credit_transactions")

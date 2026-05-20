"""
GST Fraud Detection System
Database Models (SQLAlchemy ORM)
Defines all 6 tables in PostgreSQL
"""

from sqlalchemy import (
    Column, String, Float, Integer, Boolean,
    DateTime, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db_config import Base


# ─────────────────────────────────────────
# TABLE 1: companies
# Stores all registered GSTIN companies
# ─────────────────────────────────────────
class Company(Base):
    __tablename__ = "companies"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    gstin             = Column(String(15), unique=True, nullable=False, index=True)
    company_name      = Column(String(255), nullable=False)
    state_code        = Column(String(2))
    state_name        = Column(String(100))
    industry          = Column(String(100))
    size_type         = Column(String(20))   # small / medium / large
    annual_turnover   = Column(Float)
    registration_date = Column(String(20))
    years_old         = Column(Integer)
    address_id        = Column(Integer)
    is_fraud          = Column(Integer, default=0)   # 0=legit, 1=fraud
    fraud_type        = Column(String(50), default="none")
    created_at        = Column(DateTime, server_default=func.now())
    updated_at        = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    fraud_scores = relationship("FraudScore", back_populates="company")
    alerts       = relationship("FraudAlert", back_populates="company")

    def to_dict(self):
        return {
            "gstin":            self.gstin,
            "company_name":     self.company_name,
            "state_code":       self.state_code,
            "state_name":       self.state_name,
            "industry":         self.industry,
            "size_type":        self.size_type,
            "annual_turnover":  self.annual_turnover,
            "registration_date":self.registration_date,
            "years_old":        self.years_old,
            "is_fraud":         self.is_fraud,
            "fraud_type":       self.fraud_type,
        }


# ─────────────────────────────────────────
# TABLE 2: fraud_scores
# Stores ML model scores for each GSTIN
# One row per GSTIN — updated each analysis run
# ─────────────────────────────────────────
class FraudScore(Base):
    __tablename__ = "fraud_scores"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    gstin             = Column(String(15), ForeignKey("companies.gstin"), nullable=False, index=True)

    # Individual model scores (0-100)
    xgb_score         = Column(Float, default=0)
    anomaly_score     = Column(Float, default=0)
    graph_risk_score  = Column(Float, default=0)
    rule_score        = Column(Float, default=0)

    # Final combined score
    ensemble_score    = Column(Float, default=0)
    risk_level        = Column(String(10), default="LOW")   # LOW/MEDIUM/HIGH/CRITICAL
    models_agreeing   = Column(Integer, default=0)

    # Graph features
    in_circular_ring  = Column(Boolean, default=False)
    anomaly_flag      = Column(Boolean, default=False)
    predicted_fraud   = Column(Boolean, default=False)

    # Rule flags explanation
    rule_flags        = Column(Text, default="No flags")
    flag_count        = Column(Integer, default=0)

    # Timestamps
    analyzed_at       = Column(DateTime, server_default=func.now())
    updated_at        = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    company = relationship("Company", back_populates="fraud_scores")

    def to_dict(self):
        return {
            "gstin":            self.gstin,
            "xgb_score":        self.xgb_score,
            "anomaly_score":    self.anomaly_score,
            "graph_risk_score": self.graph_risk_score,
            "rule_score":       self.rule_score,
            "ensemble_score":   self.ensemble_score,
            "risk_level":       self.risk_level,
            "models_agreeing":  self.models_agreeing,
            "in_circular_ring": self.in_circular_ring,
            "rule_flags":       self.rule_flags,
            "analyzed_at":      str(self.analyzed_at),
        }


# ─────────────────────────────────────────
# TABLE 3: ml_features
# Stores engineered features per GSTIN
# Used for retraining and analysis
# ─────────────────────────────────────────
class MLFeature(Base):
    __tablename__ = "ml_features"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    gstin                 = Column(String(15), ForeignKey("companies.gstin"), nullable=False, index=True)

    # Compliance features
    filing_rate           = Column(Float, default=0)
    missing_returns       = Column(Integer, default=0)
    avg_delay_days        = Column(Float, default=0)

    # ITC features
    avg_itc_ratio         = Column(Float, default=0)
    total_itc_claimed     = Column(Float, default=0)
    total_tax_paid        = Column(Float, default=0)

    # Transaction features
    total_outward_supply  = Column(Float, default=0)
    avg_monthly_sales     = Column(Float, default=0)
    sales_volatility      = Column(Float, default=0)
    spike_ratio           = Column(Float, default=0)

    # Invoice features
    invoices_issued       = Column(Integer, default=0)
    invoices_received     = Column(Integer, default=0)
    invoice_match_rate    = Column(Float, default=0)

    # Network features
    unique_buyers         = Column(Integer, default=0)
    unique_suppliers      = Column(Integer, default=0)
    companies_same_address= Column(Integer, default=0)

    created_at            = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "gstin":              self.gstin,
            "filing_rate":        self.filing_rate,
            "missing_returns":    self.missing_returns,
            "avg_itc_ratio":      self.avg_itc_ratio,
            "spike_ratio":        self.spike_ratio,
            "invoice_match_rate": self.invoice_match_rate,
            "sales_volatility":   self.sales_volatility,
        }


# ─────────────────────────────────────────
# TABLE 4: fraud_alerts
# High risk cases requiring investigation
# CRITICAL and HIGH risk GSTINs only
# ─────────────────────────────────────────
class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    gstin           = Column(String(15), ForeignKey("companies.gstin"), nullable=False, index=True)
    alert_type      = Column(String(20), default="AUTO")     # AUTO / MANUAL
    risk_level      = Column(String(10), nullable=False)
    ensemble_score  = Column(Float, nullable=False)
    fraud_type      = Column(String(50))
    status          = Column(String(20), default="OPEN")     # OPEN / INVESTIGATING / CLOSED
    assigned_to     = Column(String(100))                    # GST officer name
    notes           = Column(Text)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())
    resolved_at     = Column(DateTime, nullable=True)

    # Relationship
    company = relationship("Company", back_populates="alerts")

    def to_dict(self):
        return {
            "id":             self.id,
            "gstin":          self.gstin,
            "alert_type":     self.alert_type,
            "risk_level":     self.risk_level,
            "ensemble_score": self.ensemble_score,
            "fraud_type":     self.fraud_type,
            "status":         self.status,
            "assigned_to":    self.assigned_to,
            "created_at":     str(self.created_at),
        }


# ─────────────────────────────────────────
# TABLE 5: circular_rings
# Stores detected circular trading rings
# ─────────────────────────────────────────
class CircularRing(Base):
    __tablename__ = "circular_rings"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    ring_id     = Column(Integer, nullable=False)
    ring_size   = Column(Integer, nullable=False)
    gstins      = Column(Text, nullable=False)   # stored as "A->B->C->A"
    total_amount= Column(Float, default=0)
    detected_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "ring_id":    self.ring_id,
            "ring_size":  self.ring_size,
            "gstins":     self.gstins,
            "total_amount": self.total_amount,
        }


# ─────────────────────────────────────────
# TABLE 6: audit_log
# Tracks every action done in the system
# ─────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_log"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    action      = Column(String(100), nullable=False)  # GSTIN_SEARCHED / ALERT_CREATED etc
    gstin       = Column(String(15), nullable=True)
    user        = Column(String(100), default="system")
    details     = Column(Text)
    ip_address  = Column(String(45))
    created_at  = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id":         self.id,
            "action":     self.action,
            "gstin":      self.gstin,
            "user":       self.user,
            "details":    self.details,
            "created_at": str(self.created_at),
        }
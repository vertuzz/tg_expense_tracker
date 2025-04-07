import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from .database import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Expense(user_id={self.user_id}, amount={self.amount}, category='{self.category}', timestamp='{self.timestamp}')>"

# You can add more models here later if needed (e.g., for Income)
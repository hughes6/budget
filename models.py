from database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, DateTime, Float, JSON, Sequence, Date
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship
from datetime import date

class BudgetItem(Base):
    __tablename__ = 'BudgetItems'

    bucket = Column(String, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))


class Expense(Base):
    __tablename__ = 'Expenses'
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, default=date.today)
    amount = Column(Float, nullable=False)
    category = Column(String)
    description = Column(String)
    source = Column(String, default='email')
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
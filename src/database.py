from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///user_data.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)  # Telegram User ID
    first_name = Column(String, nullable=True)
    spreadsheet_id = Column(String, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db_session():
    return SessionFactory()
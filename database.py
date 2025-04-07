from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = "sqlite:///expenses.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})  # check_same_thread=False is needed for SQLite with Telegram bot handlers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    # Import models here to ensure they are registered before creating tables
    import models  # noqa: F401
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")
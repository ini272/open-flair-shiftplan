from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create SQLite database engine
# SQLite is a lightweight disk-based database that doesn't require a separate server
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
# The connect_args={"check_same_thread": False} is needed only for SQLite
# It allows SQLite to be used with FastAPI's async functionality

# Create SessionLocal class
# Each instance of SessionLocal will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
# This will be used to create database models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    # This function will be used as a dependency in FastAPI endpoints
    # It creates a new SQLAlchemy session that will be used in a single request
    # and then closed once the request is finished
    db = SessionLocal()
    try:
        yield db  # Use yield instead of return to create a dependency with "cleanup"
    finally:
        db.close()  # Session is closed after the request is finished

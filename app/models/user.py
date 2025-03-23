from sqlalchemy import Column, Integer, String, Boolean

from app.database import Base

class User(Base):
    """
    Represents the User model in the database, defining the structure and attributes of the users table.
    
    Attributes:
        id (int): Unique identifier for the user.
        username (str): Unique username for the user.
        email (str): Unique email address for the user.
        hashed_password (str): Securely hashed password for the user.
        is_active (bool): Indicates whether the user account is active.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

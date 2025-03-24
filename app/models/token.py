from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
import uuid
from datetime import datetime

from app.database import Base

def generate_token():
    """
    Generate a unique token using UUID4.
    """
    return str(uuid.uuid4())

class AccessToken(Base):
    """
    Represents an access token that can be used by multiple users.
    
    Attributes:
        id (int): Unique identifier for the token.
        token (str): The unique token string used for authentication.
        name (str): A friendly name for the token (e.g., "Team Access").
        created_at (datetime): When the token was created.
        expires_at (datetime): When the token expires (if applicable).
        is_active (bool): Whether the token is still active.
    """
    __tablename__ = "access_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, default=generate_token)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    @property
    def is_valid(self):
        """
        Check if token is valid (not expired and active).
        
        Returns:
            bool: True if the token is valid, False otherwise.
        """
        if not self.is_active:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True

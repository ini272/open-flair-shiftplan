from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

class User(Base):
    """
    Represents the User model in the database, defining the structure and attributes of the users table.
    
    Attributes:
        id (int): Unique identifier for the user.
        username (str): Unique username for the user.
        email (str): Unique email address for the user.
        is_active (bool): Indicates whether the user account is active.
        group_id (int): Foreign key reference to the group this user belongs to.
        group (relationship): Relationship to the group this user belongs to.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    
    # Add foreign key to Group
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    
    # Define relationship to Group
    group = relationship("Group", back_populates="users")

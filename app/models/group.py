from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from app.database import Base

class Group(Base):
    """
    Represents the Group model in the database, defining the structure and attributes of the groups table.
    
    Attributes:
        id (int): Unique identifier for the group.
        name (str): Unique name for the group.
        is_active (bool): Indicates whether the group is active.
        users (relationship): Relationship to the users that belong to this group.
    """
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    
    # Define the relationship to users
    # This creates the link but the actual foreign key is in the User model
    users = relationship("User", back_populates="group")
    shifts = relationship("Shift", secondary="shift_groups", back_populates="groups")

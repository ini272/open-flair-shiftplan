from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

class Shift(Base):
    """
    Represents a work shift that can have multiple users and groups assigned to it.
    
    Attributes:
        id (int): Unique identifier for the shift
        title (str): Title/name of the shift
        description (str): Optional description of the shift
        start_time (datetime): When the shift starts
        end_time (datetime): When the shift ends
        capacity (int): Maximum number of users that can be assigned (null means unlimited)
        created_at (datetime): When the shift was created
        is_active (bool): Whether the shift is active
    """
    __tablename__ = "shifts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    capacity = Column(Integer, nullable=True)  # Null means unlimited capacity
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Define relationships - many-to-many with users and groups
    users = relationship("User", secondary="shift_users", back_populates="shifts")
    groups = relationship("Group", secondary="shift_groups", back_populates="shifts")
    
    @property
    def current_user_count(self):
        """Get the current number of users assigned to this shift."""
        return len(self.users)
    
    @property
    def has_capacity(self):
        """Check if the shift has capacity for more users."""
        if self.capacity is None:  # Unlimited capacity
            return True
        return self.current_user_count < self.capacity

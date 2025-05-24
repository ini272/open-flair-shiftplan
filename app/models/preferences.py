from sqlalchemy import Column, Integer, ForeignKey, Table, Boolean
from sqlalchemy.sql import func

from app.database import Base

# Association table for user shift preferences
user_shift_preferences = Table(
    "user_shift_preferences",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("shift_id", Integer, ForeignKey("shifts.id"), primary_key=True),
    Column("can_work", Boolean, default=True)  # True = can work, False = can't work
)
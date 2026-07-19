from sqlalchemy import Boolean, Column, Integer

from app.database import Base


class PlanSettings(Base):
    """Singleton settings for the current event's published shift plan."""

    __tablename__ = "plan_settings"

    id = Column(Integer, primary_key=True)
    assignments_released = Column(Boolean, default=False, nullable=False)

from sqlalchemy.orm import Session

from app.models.plan_settings import PlanSettings


class CRUDPlanSettings:
    """Read and update the singleton publication setting for this event."""

    def assignments_are_released(self, db: Session) -> bool:
        settings = db.get(PlanSettings, 1)
        return bool(settings and settings.assignments_released)

    def set_assignments_released(self, db: Session, *, is_released: bool) -> bool:
        settings = db.get(PlanSettings, 1)
        if settings is None:
            settings = PlanSettings(id=1, assignments_released=is_released)
            db.add(settings)
        else:
            settings.assignments_released = is_released

        db.commit()
        db.refresh(settings)
        return settings.assignments_released


plan_settings = CRUDPlanSettings()

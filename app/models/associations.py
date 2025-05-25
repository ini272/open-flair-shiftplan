from sqlalchemy import Column, Integer, ForeignKey, Table, DateTime
from sqlalchemy.sql import func

from app.database import Base

# Association table for shifts and users
shift_users = Table(
    "shift_users",
    Base.metadata,
    Column("shift_id", Integer, ForeignKey("shifts.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("assigned_at", DateTime(timezone=True), server_default=func.now())
)

# Association table for shifts and groups
shift_groups = Table(
    "shift_groups",
    Base.metadata,
    Column("shift_id", Integer, ForeignKey("shifts.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
    Column("assigned_at", DateTime(timezone=True), server_default=func.now())
)

# Association table for tracking individual user opt-outs (for users without a group)
shift_user_opt_outs = Table(
    "shift_user_opt_outs",
    Base.metadata,
    Column("shift_id", Integer, ForeignKey("shifts.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("opted_out_at", DateTime(timezone=True), server_default=func.now())
)

# Association table for tracking group opt-outs
shift_group_opt_outs = Table(
    "shift_group_opt_outs",
    Base.metadata,
    Column("shift_id", Integer, ForeignKey("shifts.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
    Column("opted_out_at", DateTime(timezone=True), server_default=func.now())
)

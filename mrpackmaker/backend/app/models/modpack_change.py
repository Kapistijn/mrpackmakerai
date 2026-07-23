from __future__ import annotations
from datetime import datetime,timezone
from sqlalchemy import DateTime,ForeignKey,Integer,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.db.session import Base
class ModpackChange(Base):
 __tablename__='modpack_changes'
 id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
 project_id:Mapped[int]=mapped_column(ForeignKey('projects.id',ondelete='CASCADE'),index=True)
 action:Mapped[str]=mapped_column(String(64),nullable=False)
 mods_added:Mapped[str]=mapped_column(Text,default='[]',nullable=False)
 mods_removed:Mapped[str]=mapped_column(Text,default='[]',nullable=False)
 reason:Mapped[str]=mapped_column(Text,default='',nullable=False)
 ai_prompt:Mapped[str]=mapped_column(Text,default='',nullable=False)
 impact:Mapped[str]=mapped_column(Text,default='{}',nullable=False)
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

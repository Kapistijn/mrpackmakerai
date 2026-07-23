from __future__ import annotations
from datetime import datetime,timezone
from sqlalchemy import DateTime,ForeignKey,Integer,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.db.session import Base
class AIRequest(Base):
 __tablename__='ai_requests'
 id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
 project_id:Mapped[int]=mapped_column(ForeignKey('projects.id',ondelete='CASCADE'),index=True)
 prompt:Mapped[str]=mapped_column(Text,nullable=False)
 status:Mapped[str]=mapped_column(String(32),default='planned',nullable=False)
 plan_json:Mapped[str]=mapped_column(Text,default='{}',nullable=False)
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

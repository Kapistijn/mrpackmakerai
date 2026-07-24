from __future__ import annotations
from datetime import datetime,timezone
from sqlalchemy import DateTime,Integer,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.db.session import Base

def _now(): return datetime.now(timezone.utc)
class PackAnalysis(Base):
 __tablename__='pack_analysis'
 id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
 project_id:Mapped[int]=mapped_column(Integer,index=True,nullable=False)
 version:Mapped[int]=mapped_column(Integer,nullable=False,default=1)
 overall_score:Mapped[int]=mapped_column(Integer,nullable=False,default=0)
 report_json:Mapped[str]=mapped_column(Text,nullable=False,default='{}')
 source:Mapped[str]=mapped_column(Text,nullable=False,default='generation')
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=_now)

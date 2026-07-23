from __future__ import annotations
from datetime import datetime,timezone
from sqlalchemy import DateTime,ForeignKey,Integer,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.db.session import Base
class RepairReport(Base):
 __tablename__='repair_reports'
 id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
 project_id:Mapped[int]=mapped_column(ForeignKey('projects.id',ondelete='CASCADE'),index=True)
 source_text:Mapped[str]=mapped_column(Text,default='',nullable=False)
 report_json:Mapped[str]=mapped_column(Text,default='{}',nullable=False)
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

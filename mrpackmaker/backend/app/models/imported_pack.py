from __future__ import annotations
from datetime import datetime,timezone
from sqlalchemy import DateTime,ForeignKey,Integer,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.db.session import Base
class ImportedPack(Base):
 __tablename__='imported_packs'
 id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
 project_id:Mapped[int]=mapped_column(ForeignKey('projects.id',ondelete='CASCADE'),index=True)
 filename:Mapped[str]=mapped_column(String(255),nullable=False)
 manifest_json:Mapped[str]=mapped_column(Text,nullable=False)
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

from __future__ import annotations
from datetime import datetime,timezone
from sqlalchemy import DateTime,Integer,Text,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from app.db.session import Base
def _now():return datetime.now(timezone.utc)
class PackSnapshot(Base):
 __tablename__='pack_snapshots'
 __table_args__=(UniqueConstraint('project_id','version',name='uq_pack_snapshot_project_version'),)
 id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True);project_id:Mapped[int]=mapped_column(Integer,index=True,nullable=False);version:Mapped[int]=mapped_column(Integer,nullable=False);project_json:Mapped[str]=mapped_column(Text,nullable=False,default='{}');mods_json:Mapped[str]=mapped_column(Text,nullable=False,default='[]');analysis_json:Mapped[str]=mapped_column(Text,nullable=False,default='{}');hardware_json:Mapped[str]=mapped_column(Text,nullable=False,default='{}');pack_metadata_json:Mapped[str]=mapped_column(Text,nullable=False,default='{}');generated_files_json:Mapped[str]=mapped_column(Text,nullable=False,default='{}');reason:Mapped[str]=mapped_column(Text,nullable=False,default='');change_json:Mapped[str]=mapped_column(Text,nullable=False,default='{}');created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=_now)

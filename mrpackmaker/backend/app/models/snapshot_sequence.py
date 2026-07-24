from sqlalchemy import Integer
from sqlalchemy.orm import Mapped,mapped_column
from app.db.session import Base
class SnapshotSequence(Base):
 __tablename__='pack_snapshot_sequences'
 project_id:Mapped[int]=mapped_column(Integer,primary_key=True)
 next_version:Mapped[int]=mapped_column(Integer,nullable=False,default=1)

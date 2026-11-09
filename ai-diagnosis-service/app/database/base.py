
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


INCIDENT_SCHEMA = "incident_management"

metadata = MetaData(
    schema=INCIDENT_SCHEMA,
)

class Base(DeclarativeBase):
    metadata = metadata

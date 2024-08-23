from typing import List, Optional
from pydantic import BaseModel

# Data classes
class NamedEntity(BaseModel):
    name: str
    namedentity_id: str = None  # Optional for ID generation

class Statement(BaseModel):
    statement_text: str
    statement_id: str = None  # Optional for ID generation
    about_namedentity_id: str
    mentioned_namedentity_ids: Optional[List[str]] = None  # Optional field

from typing import List, Optional
from pydantic import BaseModel
from typing import Any, Dict
from pydantic import BaseModel, Field

# Data classes
class NamedEntity(BaseModel):
    name: str
    namedentity_id: str = None  # Optional for ID generation

class Statement(BaseModel):
    text: str
    statement_id: str = None  # Optional for ID generation
    about_namedentity_id: str
    mentioned_namedentity_ids: Optional[List[str]] = None  # Optional field

class RelationshipAttributes(BaseModel):
    source_statement_id: str
    # You can add other optional attributes here
    additional_properties: Dict[str, Any] = Field(default_factory=dict)

class Relationship(BaseModel):
    from_node: str
    to_node: str
    relationship: str
    attributes: RelationshipAttributes

class Connection(BaseModel):
    connected_entity: NamedEntity
    relationship: Relationship  # Updated to use the new Relationship class

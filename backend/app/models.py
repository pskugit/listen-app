from typing import List, Optional
from pydantic import BaseModel
from typing import Any, Dict
from pydantic import BaseModel, Field

# Data classes
class Topic(BaseModel):
    name: str
    topic_id: str = None 

    class Config:
        frozen = False  # Allow mutation of fields after instantiation

class NamedEntity(BaseModel):
    name: str
    namedentity_id: str = None 
    additional_labels: Optional[List[str]] = None  # Correctly define the optional list of strings

    class Config:
        frozen = False  # Allow mutation of fields after instantiation

class Statement(BaseModel):
    text: str
    statement_id: str = None 
    about_namedentity_id: str
    
    class Config:
        frozen = False  # Allow mutation of fields after instantiation
    

class RelationshipAttributes(BaseModel):
    source_statement_id: str
    # You can add other optional attributes here
    additional_properties: Dict[str, Any] = Field(default_factory=dict)

class Relationship(BaseModel):
    from_node: str
    to_node: str
    relationship_type: str
    attributes: Optional[RelationshipAttributes]

class Connection(BaseModel):
    connected_entity: NamedEntity
    relationship: Relationship  # Updated to use the new Relationship class

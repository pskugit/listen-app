

from app.models import Statement, NamedEntity, Relationship, RelationshipAttributes
from typing import List

from app.utils.neo4j import get_driver, get_namedentity_by_id

# Neo4j driver initialization
driver = get_driver()

def is_uppercase_and_underscore(s: str):
    return not s.isupper() or not all(c.isalpha() or c == '_' for c in s)

def derive_relationships_from_statement(statement: Statement, mentioned_namedentities: List[NamedEntity]) -> List[Relationship]:

    text = statement.about_namedentity_id
    about_namedentity: NamedEntity = get_namedentity_by_id(driver, statement.about_namedentity_id)

    # Construct prompt
    # Derive List[Relationship]

    relationships = []

    entity_ids = [about_namedentity.namedentity_id]
    entity_ids.extend([mentioned_namedentity.namedentity_id for mentioned_namedentity in mentioned_namedentities])

    for i, source_entity_id in enumerate(entity_ids):
        for target_entity_id in entity_ids[i+1:]:
            attributes = RelationshipAttributes(
                source_statement_id=statement.statement_id
            )
            relationship = Relationship(
                from_node=source_entity_id,
                to_node=target_entity_id,
                relationship_type="SOME_RELATION",
                attributes=attributes
            )
            relationships.append(relationship)

    return relationships
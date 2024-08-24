from fastapi import APIRouter, HTTPException
from typing import List
from uuid import uuid4
from app.models import Statement
from app.utils.neo4j import named_entity_exists, get_driver

router = APIRouter()

# Neo4j driver initialization
driver = get_driver()

# Helper methods
def delete_statement_relationships(session, statement_id: str):
    """Deletes relationships derived from a specific statement."""
    session.run("""
        MATCH ()-[r]->() 
        WHERE r.source_statement = $statement_id
        DELETE r
    """, statement_id=statement_id)

def create_additional_relations(session, entity_ids: List[str], source_statement: Statement, relation_type="SOME_RELATION"):
    """Create connections of type relation_type between all named entities in the list."""
    for i, source_id in enumerate(entity_ids):
        for target_id in entity_ids[i+1:]:
            session.run(f"""
                MATCH (e1:NamedEntity {{namedentity_id: $source_id}}),
                      (e2:NamedEntity {{namedentity_id: $target_id}})
                CREATE (e1)-[:{relation_type} {{source_statement_id: $source_statement_id}}]->(e2)
                CREATE (e2)-[:{relation_type} {{source_statement_id: $source_statement_id}}]->(e1)
            """, source_id=source_id, target_id=target_id, source_statement_id=source_statement.statement_id)

def create_mentions_relationships(session, statement):
    """Create MENTIONS relationships from the statement to the mentioned named entities."""
    if statement.mentioned_namedentity_ids:
        for mentioned_id in statement.mentioned_namedentity_ids:
            if named_entity_exists(driver, mentioned_id):
                session.run("""
                    MATCH (s:Statement {statement_id: $statement_id}), 
                          (m:NamedEntity {namedentity_id: $mentionedentity_id})
                    CREATE (s)-[:MENTIONS]->(m)
                """, statement_id=statement.statement_id, mentionedentity_id=mentioned_id)

# Endpoints
@router.post("/create/")
def create(statement: Statement):
    # Validate that the text is not empty
    if not statement.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")

    statement.statement_id = statement.statement_id or str(uuid4())
    
    try:
        # Check if the main NamedEntity exists
        if not named_entity_exists(driver, statement.about_namedentity_id):
            raise HTTPException(status_code=404, detail="NamedEntity that the statement is about does not exist")

        with driver.session() as session:
            # Create the Statement
            session.run("""
                CREATE (s:Statement {text: $text, statement_id: $statement_id})
            """, text=statement.text, statement_id=statement.statement_id)

            # Create the relationship to the main NamedEntity
            session.run("""
                MATCH (s:Statement {statement_id: $statement_id}), 
                      (p:NamedEntity {namedentity_id: $namedentity_id})
                CREATE (s)-[:IS_ABOUT]->(p)
            """, statement_id=statement.statement_id, namedentity_id=statement.about_namedentity_id)

            # Handle MENTIONS relationships
            create_mentions_relationships(session, statement)

            # Create additional SOME_RELATION relationships
            if statement.mentioned_namedentity_ids:
                entity_ids = statement.mentioned_namedentity_ids + [statement.about_namedentity_id]
                create_additional_relations(session, entity_ids, statement)

        return {"message": "Statement added successfully", "statement_id": statement.statement_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/update_text/")
def update_text(statement_id: str, new_text: str):
    try:
        with driver.session() as session:
            session.run("""
                MATCH (s:Statement {statement_id: $statement_id})
                SET s.text = $new_text
            """, statement_id=statement_id, new_text=new_text)
        return {"message": "Statement text updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update_mentions/")
def update_mentions(statement_id: str, mentioned_namedentity_ids: List[str]):
    try:
        with driver.session() as session:
            # Fetch the full Statement object
            result = session.run("""
                MATCH (s:Statement {statement_id: $statement_id})-[:IS_ABOUT]->(n:NamedEntity)
                RETURN s.text AS text, s.statement_id AS statement_id, n.namedentity_id AS about_namedentity_id
            """, statement_id=statement_id)
            
            record = result.single()
            if not record:
                raise HTTPException(status_code=404, detail="Statement not found")
            
            # Construct the Statement object
            statement = Statement(
                text=record["text"],
                statement_id=record["statement_id"],
                about_namedentity_id=record["about_namedentity_id"],
                mentioned_namedentity_ids=mentioned_namedentity_ids  # New mentions provided by the user
            )

            # Remove existing MENTIONS relationships
            session.run("""
                MATCH (s:Statement {statement_id: $statement_id})-[r:MENTIONS]->()
                DELETE r
            """, statement_id=statement_id)

            # Create new MENTIONS relationships
            for mentioned_id in mentioned_namedentity_ids:
                if named_entity_exists(driver, mentioned_id):
                    session.run("""
                        MATCH (s:Statement {statement_id: $statement_id}), 
                              (m:NamedEntity {namedentity_id: $mentionedentity_id})
                        CREATE (s)-[:MENTIONS]->(m)
                    """, statement_id=statement_id, mentionedentity_id=mentioned_id)

            # Remove all previous relationships between entities that had been connected by the mentions
            delete_statement_relationships(session, statement_id)

            # Create new relationships that are a result of the newly updated mentions
            entity_ids = mentioned_namedentity_ids + [statement.about_namedentity_id]
            create_additional_relations(session, entity_ids, statement)

        return {"message": "Statement mentions updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete/")
def delete_statement(statement_id: str):
    try:
        with driver.session() as session:
            delete_statement_relationships(session, statement_id)
            session.run("""
                MATCH (s:Statement {statement_id: $statement_id})
                DETACH DELETE s
            """, statement_id=statement_id)
        return {"message": "Statement deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from uuid import uuid4
from app.models import Statement
from app.genai.genai import derive_relation_type_from_text
from app.utils.neo4j import named_entity_exists, get_driver
from pydantic import BaseModel

router = APIRouter()

# Neo4j driver initialization
driver = get_driver()

# Helper methods
def create_mentions_relationships(session, statement: Statement, mentioned_namedentity_ids: List[str]):
    """Create MENTIONS relationships from the statement to the mentioned named entities."""
    for mentioned_id in mentioned_namedentity_ids:
        if named_entity_exists(driver, mentioned_id):
            session.run("""
                MATCH (s:Statement {statement_id: $statement_id}), 
                      (m:NamedEntity {namedentity_id: $mentionedentity_id})
                CREATE (s)-[:MENTIONS]->(m)
            """, statement_id=statement.statement_id, mentionedentity_id=mentioned_id)


def remove_mentions_relationships(session, statement_id: str):
    """Remove MENTIONS relationships for a given statement."""
    session.run("""
        MATCH (s:Statement {statement_id: $statement_id})-[r:MENTIONS]->()
        DELETE r
    """, statement_id=statement_id)


def create_additional_relations(session, source_statement: Statement, entity_ids: List[str]):
    relation_type = derive_relation_type_from_text(source_statement.text)
    """Create connections of type relation_type between all named entities in the list."""
    for i, source_entity_id in enumerate(entity_ids):
        for target_entity_id in entity_ids[i+1:]:
            session.run(f"""
                MATCH (e1:NamedEntity {{namedentity_id: $source_entity_id}}),
                      (e2:NamedEntity {{namedentity_id: $target_entity_id}})
                CREATE (e1)-[:{relation_type} {{source_statement_id: $source_statement_id}}]->(e2)
                CREATE (e2)-[:{relation_type} {{source_statement_id: $source_statement_id}}]->(e1)
            """, source_entity_id=source_entity_id, target_entity_id=target_entity_id, source_statement_id=source_statement.statement_id)


def delete_statement_relationships(session, statement_id: str):
    """Deletes relationships derived from a specific statement."""
    session.run("""
        MATCH ()-[r]->() 
        WHERE r.source_statement_id = $statement_id
        DELETE r
    """, statement_id=statement_id)


def handle_mentions(session, statement: Statement, mentioned_namedentity_ids: List[str]):
    if mentioned_namedentity_ids:
        # Create new MENTIONS relationships
        create_mentions_relationships(session, statement, mentioned_namedentity_ids)

        # Create additional SOME_RELATION relationships
        entity_ids = mentioned_namedentity_ids + [statement.about_namedentity_id]
        create_additional_relations(session, statement, entity_ids)


def get_statement_by_id(statement_id: str) -> Statement:
    with driver.session() as session:
        result = session.run("""
            MATCH (s:Statement {statement_id: $statement_id})-[:IS_ABOUT]->(n:NamedEntity)
            RETURN s.text AS text, s.statement_id AS statement_id, n.namedentity_id AS about_namedentity_id
        """, statement_id=statement_id)

        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Statement not found")

        statement = Statement(
            text=record["text"],
            statement_id=record["statement_id"],
            about_namedentity_id=record["about_namedentity_id"],
        )

        return statement


def delete_statement_by_id(statement_id: str):
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
    

# Endpoints
@router.post("/create/")
def create(statement: Statement):
    # Validate that the text is not empty
    if not statement.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

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

        return {"message": "Statement added successfully", "statement_id": statement.statement_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read/", response_model=Statement, description="Get a statement based on its ID.")
def read_statement(statement_id: str):
    return get_statement_by_id(statement_id)


@router.post("/set_topic/")
def set_topic(statement_id: str, topic_id: Optional[str] = None, ):
    statement = get_statement_by_id(statement_id)
    try:
        with driver.session() as session:
            # Step 1: Remove existing HAS_TOPIC relationships from the statement
            session.run("""
                MATCH (s:Statement {statement_id: $statement_id})-[r:HAS_TOPIC]->(t:Topic)
                DELETE r
            """, statement_id=statement.statement_id)

            # Step 2: If topic_id is provided and not empty, create a new HAS_TOPIC relationship to the specified topic
            if topic_id and topic_id.strip():  # Check if topic_id is not empty
                session.run("""
                    MATCH (s:Statement {statement_id: $statement_id}),
                          (t:Topic {topic_id: $topic_id})
                    CREATE (s)-[:HAS_TOPIC]->(t)
                """, statement_id=statement.statement_id, topic_id=topic_id)

        return {"message": "Topic set successfully for the statement" if topic_id and topic_id.strip() else "Topic removed from the statement"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/add_mentions/")
def add_mentions(mentioned_namedentity_ids: List[str], statement_id: str):
    statement = get_statement_by_id(statement_id)
    try:
        with driver.session() as session:
            handle_mentions(session, statement, mentioned_namedentity_ids)

        return {"message": "Mentions added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UpdateMentionsRequest(BaseModel):
    statement_id: str
    mentioned_namedentity_ids: List[str]

@router.post("/update_mentions/")
def update_mentions(request: UpdateMentionsRequest):
    statement = get_statement_by_id(request.statement_id)
    try:
        with driver.session() as session:
            # Remove existing MENTIONS relationships
            remove_mentions_relationships(session, statement.statement_id)
            
            # Remove all previous relationships between entities that had been connected by the mentions
            delete_statement_relationships(session, statement.statement_id)

            # Handle the new mentions and derived relationships
            handle_mentions(session, statement, request.mentioned_namedentity_ids)

        return {"message": "Mentions updated successfully"}
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


@router.post("/delete/")
def delete_statement(statement_id: str):
    return delete_statement_by_id(statement_id)


from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List
from uuid import uuid4
from app.models import Statement, NamedEntity, Relationship
from app.genai.genai import derive_relationships_from_statement
from app.utils.neo4j import named_entity_exists, get_driver, get_statement_by_id
from pydantic import BaseModel

router = APIRouter()

# Neo4j driver initialization
driver = get_driver()

# Helper methods
def remove_and_return(lst, element):
    return [item for item in lst if item != element]

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


def create_additional_relations(session, source_statement: Statement):
    mentioned_namedentities: List[NamedEntity] = get_mentioned_entities_for_statement(source_statement)
    relationships: List[Relationship] = derive_relationships_from_statement(source_statement, mentioned_namedentities)
    for relationship in relationships:
        source_entity_id = relationship.from_node
        target_entity_id = relationship.to_node
        session.run(f"""
                MATCH (e1:NamedEntity {{namedentity_id: $source_entity_id}}),
                      (e2:NamedEntity {{namedentity_id: $target_entity_id}})
                CREATE (e1)-[:{relationship.relationship_type} {{source_statement_id: $source_statement_id}}]->(e2)
                CREATE (e2)-[:{relationship.relationship_type} {{source_statement_id: $source_statement_id}}]->(e1)
            """, source_entity_id=source_entity_id, target_entity_id=target_entity_id, source_statement_id=source_statement.statement_id)

    #"""Create connections of type relation_type between all named entities in the list."""
    #for i, source_entity_id in enumerate(entity_ids):
    #    for target_entity_id in entity_ids[i+1:]:
    #        session.run(f"""
    #            MATCH (e1:NamedEntity {{namedentity_id: $source_entity_id}}),
    #                  (e2:NamedEntity {{namedentity_id: $target_entity_id}})
    #            CREATE (e1)-[:{relation_type} {{source_statement_id: $source_statement_id}}]->(e2)
    #            CREATE (e2)-[:{relation_type} {{source_statement_id: $source_statement_id}}]->(e1)
    #        """, source_entity_id=source_entity_id, target_entity_id=target_entity_id, source_statement_id=source_statement.statement_id)


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
        create_additional_relations(session, statement)




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
    

def get_mentioned_entities_for_statement(statement: Statement):
        with driver.session() as session:
            result = session.run("""
                MATCH (s:Statement {statement_id: $statement_id})-[:MENTIONS]->(m:NamedEntity)
                RETURN m.name AS name, m.namedentity_id AS namedentity_id, labels(m) AS labels
            """, statement_id=statement.statement_id)
            
            # Convert the result to a list of NamedEntity objects
            namedentities = [
                NamedEntity(name=record["name"], namedentity_id=record["namedentity_id"], additional_labels=remove_and_return(record["labels"],"NamedEntity"))
                for record in result
            ]
        return namedentities

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
    statement = get_statement_by_id(driver, statement_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement not found")
    raise HTTPException(status_code=404, detail="Statement not found")


@router.post("/get_mentions/")
def get_mentions(statement_id: str)  -> List[NamedEntity]:
    statement = get_statement_by_id(driver, statement_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement not found")
    try:
        get_mentioned_entities_for_statement(statement)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/set_topic/")
def set_topic(statement_id: str, topic_id: Optional[str] = None):
    statement = get_statement_by_id(driver, statement_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement not found")
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
def add_mentions(mentioned_namedentity_ids: List[str] = Query(...), statement_id: str = Query(...)):
    statement = get_statement_by_id(statement_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement not found")
    try:
        with driver.session() as session:
            handle_mentions(session, statement, mentioned_namedentity_ids)

        return {"message": "Mentions added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update_mentions/")
def update_mentions(mentioned_namedentity_ids: List[str] = Query(...), statement_id: str = Query(...)):
    statement = get_statement_by_id(driver, statement_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement not found")
    try:
        with driver.session() as session:
            # Remove existing MENTIONS relationships
            remove_mentions_relationships(session, statement.statement_id)
            
            # Remove all previous relationships between entities that had been connected by the mentions
            delete_statement_relationships(session, statement.statement_id)

            # Handle the new mentions and derived relationships
            handle_mentions(session, statement, mentioned_namedentity_ids)

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


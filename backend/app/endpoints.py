from fastapi import APIRouter, HTTPException
from neo4j import GraphDatabase
from pydantic import BaseModel
from uuid import uuid4
from app.models import NamedEntity, Statement
from app.utils.neo4j import named_entity_exists

# Create an instance of APIRouter
router = APIRouter()

# Neo4j driver initialization
driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password"))


@router.get("/test_connection")
async def test_connection():
    try:
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n)")
            count = result.single()[0]
        return {"count": count}
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))

    
# Endpoint to add a NamedEntity
@router.post("/add_namedentity/", description="Add a new NamedEntity to the database.")
def add_namedentity(named_entity: NamedEntity):
    namedentity_id = named_entity.namedentity_id or str(uuid4())
    try:
        with driver.session() as session:
            session.run("""
            CREATE (p:NamedEntity {name: $name, namedentity_id: $namedentity_id})
            """, name=named_entity.name, namedentity_id=namedentity_id)
        return {"message": "NamedEntity added successfully", "namedentity_id": namedentity_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# Endpoint to add a Statement
@router.post("/add_statement/")
def add_statement(statement: Statement):
    statement_id = statement.statement_id or str(uuid4())
    try:
        # Check if the main NamedEntity exists
        if not named_entity_exists(driver, statement.about_namedentity_id):
            raise HTTPException(status_code=404, detail="NamedEntity that the statement is about does not exist")

        # Create the Statement
        with driver.session() as session:
            session.run("""
                CREATE (s:Statement {text: $statement_text, statement_id: $statement_id})
            """, statement_text=statement.statement_text, statement_id=statement_id)

            # Create the relationship to the main NamedEntity
            session.run("""
                MATCH (s:Statement {statement_id: $statement_id}), 
                      (p:NamedEntity {namedentity_id: $namedentity_id})
                CREATE (s)-[:IS_ABOUT]->(p)
            """, statement_id=statement_id, namedentity_id=statement.about_namedentity_id)

            # Iterate over mentioned_namedentity_ids and create relationships
            if statement.mentioned_namedentity_ids:
                for mentioned_id in statement.mentioned_namedentity_ids:
                    if named_entity_exists(driver, mentioned_id):
                        session.run("""
                            MATCH (s:Statement {statement_id: $statement_id}), 
                                  (m:NamedEntity {namedentity_id: $mentionedentity_id})
                            CREATE (s)-[:MENTIONS]->(m)
                        """, statement_id=statement_id, mentionedentity_id=mentioned_id)

        return {"message": "Statement added successfully", "statement_id": statement_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Shutdown event to close the driver
@router.on_event("shutdown")
def shutdown():
    driver.close()

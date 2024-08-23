from fastapi import APIRouter, HTTPException
from neo4j import GraphDatabase
from typing import List
from uuid import uuid4
from app.models import NamedEntity, Statement, Connection, RelationshipAttributes, Relationship
from app.utils.neo4j import named_entity_exists

# Create an instance of APIRouter
router = APIRouter()

# Neo4j driver initialization
driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password"))

# Endpoint to count the elements in the whole graph and thus test the connection
@router.get("/test_connection")
async def test_connection():
    try:
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n)")
            count = result.single()[0]
        return {"count": count}
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))
    

# Endpoint to retrieve all named entities connected to a given named entity
@router.post("/get_connections_for_namedenity/", response_model=List[Connection], description="Get all named entities connected to the given named entity.")
def get_connected_namedentities(named_entity: NamedEntity):
    # Check if the NamedEntity exists
    if not named_entity_exists(driver, named_entity.namedentity_id):
        raise HTTPException(status_code=404, detail="NamedEntity does not exist")

    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (n:NamedEntity {namedentity_id: $namedentity_id})-[r]->(connected:NamedEntity)
                RETURN r AS relationship, connected
            """, namedentity_id=named_entity.namedentity_id)

            connections = []
            for record in result:
                relationship = Relationship(
                    from_node=named_entity.namedentity_id,
                    to_node=record["connected"]["namedentity_id"],
                    relationship=record["relationship"].type,  # Adjust as needed for relationship type
                    attributes=RelationshipAttributes(
                        source_statement_id=record["relationship"].get("source_statement_id")  # Adjust as needed
                    )
                )
                connected_entity = NamedEntity(**record["connected"])  # Create NamedEntity from record
                connections.append(Connection(connected_entity=connected_entity, relationship=relationship))

        return connections
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_statements_for_namedentity/", response_model=List[Statement], description="Get all statements connected to the given named entity.")
def get_statements_for_namedentity(named_entity: NamedEntity):
    # Check if the NamedEntity exists
    if not named_entity_exists(driver, named_entity.namedentity_id):
        raise HTTPException(status_code=404, detail="NamedEntity does not exist")

    try:
        with driver.session() as session:
            # First, retrieve statements related to the named entity
            result = session.run("""
                MATCH (s:Statement)-[:IS_ABOUT]->(n:NamedEntity {namedentity_id: $namedentity_id})
                RETURN s.statement_text AS statement_text, s.statement_id AS statement_id
            """, namedentity_id=named_entity.namedentity_id)

            statements = []
            for record in result:
                statement_id = record["statement_id"]
                statement_text = record["statement_text"]

                # Check if the retrieved values are not None
                if statement_text is None or statement_id is None:
                    raise HTTPException(status_code=500, detail="Statement data is incomplete")

                # Create a Statement instance with the required fields
                statement = Statement(
                    statement_text=statement_text,
                    statement_id=statement_id,
                    about_namedentity_id=named_entity.namedentity_id,  # Set the about_namedentity_id
                    mentioned_namedentity_ids=None  # Placeholder for now
                )

                # Fetch mentioned named entities for this statement
                mentioned_result = session.run("""
                    MATCH (s:Statement {statement_id: $statement_id})-[:MENTIONS]->(m:NamedEntity)
                    RETURN m.namedentity_id AS mentioned_id
                """, statement_id=statement_id)

                # Populate the mentioned_namedentity_ids field
                statement.mentioned_namedentity_ids = [record["mentioned_id"] for record in mentioned_result]
                
                statements.append(statement)

        return statements
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
    
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

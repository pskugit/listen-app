from fastapi import APIRouter, HTTPException
from neo4j import GraphDatabase
from typing import Any, Dict, List
from uuid import uuid4
from app.models import NamedEntity, Statement, Connection, RelationshipAttributes, Relationship, Topic
from app.utils.neo4j import named_entity_exists
from pydantic import ValidationError

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
    
@router.post("/get_node/", description="Get a node based on its id and label.")
def get_node(label: str, node_id: str):
    try:
        with driver.session() as session:
            result = session.run(f"""
                MATCH (n:{label} {{ {label.lower()}_id: $node_id }})
                RETURN n
            """, node_id=node_id)

            node = result.single()
            if node is None:
                raise HTTPException(status_code=404, detail=f"{label} with id {node_id} not found")

            return node["n"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
                RETURN s.text AS text, s.statement_id AS statement_id
            """, namedentity_id=named_entity.namedentity_id)

            statements = []
            for record in result:
                statement_id = record["statement_id"]
                text = record["text"]

                # Check if the retrieved values are not None
                if text is None or statement_id is None:
                    raise HTTPException(status_code=500, detail="Statement data is incomplete")

                # Create a Statement instance with the required fields
                statement = Statement(
                    text=text,
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
        return {"message": "NamedEntity added successfully", "name": named_entity.name, "namedentity_id": namedentity_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Endpoint to add a Topic
@router.post("/add_topic/", description="Add a new Topic to the database.")
def add_topic(topic: Topic):
    topic_id = topic.topic_id or str(uuid4())
    try:
        with driver.session() as session:
            session.run(""" 
            CREATE (p:Topic {name: $name, topic_id: $topic_id})
            """, name=topic.name, topic_id=topic_id)
        return {"message": "Topic added successfully", "name": topic.name, "topic_id": topic_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add_statement/")
def add_statement(statement: Statement):
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
                create_additional_relations(session, entity_ids)

        return {"message": "Statement added successfully", "statement_id": statement.statement_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def delete_statement_relationships(session, statement_id: str):
    """Deletes relationships derived from a specific statement."""
    session.run("""
        MATCH ()-[r]->() 
        WHERE r.source_statement = $statement_id
        DELETE r
    """, statement_id=statement_id)

def create_additional_relations(session, entity_ids: List[str], relation_type="SOME_RELATION"):
    """Create connections of type relation_type between all named entities in the list."""
    for i, source_id in enumerate(entity_ids):
        for target_id in entity_ids[i+1:]:
            session.run(f"""
                MATCH (e1:NamedEntity {{namedentity_id: $source_id}}),
                      (e2:NamedEntity {{namedentity_id: $target_id}})
                CREATE (e1)-[:{relation_type}]->(e2)
                CREATE (e2)-[:{relation_type}]->(e1)
            """, source_id=source_id, target_id=target_id)

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

# Endpoint to update a node
@router.post("/update_node/", description="Update a node based on its id and label.")
def update_node(label: str, node_id: str, updates: Dict[str, Any]):
    try:
        # Determine the correct Pydantic model based on the label
        model_map = {
            "statement": Statement,
            "namedentity": NamedEntity,
            "topic": Topic
        }

        model = model_map.get(label.lower())
        if model is None:
            raise HTTPException(status_code=400, detail=f"Invalid label: {label}")

        # Validate updates against the model
        try:
            validated_data = model(**updates)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Construct the SET clause for the Cypher query
        set_clause = ", ".join([f"n.{key} = ${key}" for key in validated_data.dict().keys()])
        query = f"""
            MATCH (n:{label} {{ {label.lower()}_id: $node_id }})
            SET {set_clause}
            RETURN n
        """

        with driver.session() as session:
            # Check if the label is "Statement" and handle accordingly
            if label.lower() == "statement":
                delete_statement_relationships(session, node_id)

            result = session.run(query, node_id=node_id, **validated_data.dict())

            updated_node = result.single()
            if updated_node is None:
                raise HTTPException(status_code=404, detail=f"{label} with id {node_id} not found")

            return {"message": f"{label} updated successfully", "node": updated_node["n"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/delete_node/", description="Delete a node based on its id and label.")
def delete_node(label: str, node_id: str):
    try:
        with driver.session() as session:
            # Check if the label is "Statement" and handle accordingly
            if label.lower() == "statement":
                delete_statement_relationships(session, node_id)

            # Delete the node
            result = session.run(f"""
                MATCH (n:{label} {{ {label.lower()}_id: $node_id }})
                DETACH DELETE n
            """, node_id=node_id)

            # Check if the node was deleted
            summary = result.consume()
            if summary.counters.nodes_deleted == 0:
                raise HTTPException(status_code=404, detail=f"{label} with id {node_id} not found")

            return {"message": f"{label} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/get_namedentities_with_name/", description="Get all nodes with a specific name.")
def get_namedentities_with_name(label: str, name: str):
    try:
        with driver.session() as session:
            result = session.run(f"""
                MATCH (n:{label} {{ name: $name }})
                RETURN n
            """, name=name)

            nodes = [record["n"] for record in result]
            if not nodes:
                raise HTTPException(status_code=404, detail=f"No {label} found with name {name}")

            return {"nodes": nodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Shutdown event to close the driver
@router.on_event("shutdown")
def shutdown():
    driver.close()

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from uuid import uuid4
from app.models import NamedEntity, Statement
from app.utils.neo4j import named_entity_exists, get_driver
from app.endpoints.statement import delete_statement

router = APIRouter()

# Neo4j driver initialization
driver = get_driver()

@router.post("/create", description="Add a new NamedEntity to the database.")
def create(named_entity: NamedEntity):
    namedentity_id = named_entity.namedentity_id or str(uuid4())
    try:
        # Convert the additional_types list into a string of labels
        additional_labels = ""
        if named_entity.additional_types:
            additional_labels = ":" + ":".join(named_entity.additional_types)

        with driver.session() as session:
            session.run(f"""
            CREATE (p:NamedEntity{additional_labels} {{name: $name, namedentity_id: $namedentity_id}})
            """, name=named_entity.name, namedentity_id=namedentity_id)
        return {"message": "NamedEntity added successfully", "name": named_entity.name, "namedentity_id": namedentity_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_by_name/", description="Get all NamedEntities with a specific name.")
def get_by_name(name: str):
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (n:NamedEntity { name: $name })
                RETURN n, labels(n) AS labels
            """, name=name)

            namedentities = []
            for record in result:
                node = record["n"]
                labels = record["labels"]

                # Create a NamedEntity instance
                named_entity = NamedEntity(
                    name=node["name"],
                    namedentity_id=node["namedentity_id"],
                    additional_types=[label for label in labels if label != "NamedEntity"]
                )

                namedentities.append(named_entity)

            if not namedentities:
                raise HTTPException(status_code=404, detail=f"No NamedEntity found with name {name}")

            return {"namedentities": namedentities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/get_statements/", response_model=List[Statement], description="Get all statements connected to the given named entity.")
def get_statements(namedentity_id: str):
    # Check if the NamedEntity exists
    if not named_entity_exists(driver, namedentity_id):
        raise HTTPException(status_code=404, detail="NamedEntity does not exist")

    try:
        with driver.session() as session:
            # First, retrieve statements related to the named entity
            result = session.run("""
                MATCH (s:Statement)-[:IS_ABOUT]->(n:NamedEntity {namedentity_id: $namedentity_id})
                RETURN s.text AS text, s.statement_id AS statement_id
            """, namedentity_id=namedentity_id)

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
                    about_namedentity_id=namedentity_id,  # Set the about_namedentity_id
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


@router.post("/update_type/")
def update_type(namedentity_id: str, additional_types: List[str]):
    try:
        with driver.session() as session:
            session.run(f"""
                MATCH (n:NamedEntity {{ namedentity_id: $namedentity_id }})
                SET n:{":".join(additional_types)}
            """, namedentity_id=namedentity_id)
        return {"message": "NamedEntity type updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete/")
def delete(namedentity_id: str):
    try:
        with driver.session() as session:
            # Step A: Delete all statements connected via `IS_ABOUT` relationship
            result = session.run("""
                MATCH (n:NamedEntity {namedentity_id: $namedentity_id})<-[:IS_ABOUT]-(s:Statement)
                RETURN s.statement_id AS statement_id
            """, namedentity_id=namedentity_id)

            # Call the delete_statement endpoint for each statement
            for record in result:
                statement_id = record["statement_id"]
                delete_statement(statement_id=statement_id)

            # Step B: Modify all statements connected via `:MENTIONS` relationship
            result = session.run("""
                MATCH (s:Statement)-[r:MENTIONS]->(n:NamedEntity {namedentity_id: $namedentity_id})
                RETURN s.statement_id AS statement_id, s.mentioned_namedentity_ids AS mentioned_namedentity_ids
            """, namedentity_id=namedentity_id)

            # Iterate over all statements that mention this named entity
            for record in result:
                statement_id = record["statement_id"]
                mentioned_ids = record["mentioned_namedentity_ids"]

                # Remove the namedentity_id from mentioned_namedentity_ids
                updated_mentioned_ids = [id for id in mentioned_ids if id != namedentity_id]

                # Update the statement with the new mentioned_namedentity_ids
                session.run("""
                    MATCH (s:Statement {statement_id: $statement_id})
                    SET s.mentioned_namedentity_ids = $updated_mentioned_ids
                """, statement_id=statement_id, updated_mentioned_ids=updated_mentioned_ids)

            # Step C: Finally, delete the NamedEntity itself
            result = session.run("""
                MATCH (n:NamedEntity {namedentity_id: $namedentity_id})
                DETACH DELETE n
            """, namedentity_id=namedentity_id)

            summary = result.consume()
            if summary.counters.nodes_deleted == 0:
                raise HTTPException(status_code=404, detail=f"NamedEntity with id {namedentity_id} not found")

            return {"message": f"NamedEntity with id {namedentity_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

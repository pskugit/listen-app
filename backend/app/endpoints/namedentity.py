from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from uuid import uuid4
from app.models import NamedEntity, Statement
from app.utils.neo4j import get_driver
from app.endpoints.statement import delete_statement_by_id

router = APIRouter()

# Neo4j driver initialization
driver = get_driver()

def get_namedentity_by_id(namedentity_id: str):
    with driver.session() as session:
        result = session.run("""
            MATCH (n:NamedEntity {namedentity_id: $namedentity_id})
            RETURN n, labels(n) AS labels
        """, namedentity_id=namedentity_id)

        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="NamedEntity not found")

        node = record["n"]
        labels = record["labels"]

        named_entity = NamedEntity(
            name=node["name"],
            namedentity_id=node["namedentity_id"],
            additional_labels=[label for label in labels if label != "NamedEntity"]
        )
        return named_entity
    
@router.post("/create", description="Add a new NamedEntity to the database.")
def create(named_entity: NamedEntity):
    namedentity_id = named_entity.namedentity_id or str(uuid4())
    try:
        # Convert the additional_labels list into a string of labels
        additional_labels = ""
        if named_entity.additional_labels:
            additional_labels = ":" + ":".join(named_entity.additional_labels)

        with driver.session() as session:
            session.run(f"""
            CREATE (p:NamedEntity{additional_labels} {{name: $name, namedentity_id: $namedentity_id}})
            """, name=named_entity.name, namedentity_id=namedentity_id)
        return {"message": "NamedEntity added successfully", "name": named_entity.name, "namedentity_id": namedentity_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/read/", response_model=NamedEntity, description="Get a NamedEntity based on its ID.")
def read_namedentity(namedentity_id: str):
        return get_namedentity_by_id(namedentity_id)


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
                    additional_labels=[label for label in labels if label != "NamedEntity"]
                )

                namedentities.append(named_entity)

            if not namedentities:
                raise HTTPException(status_code=404, detail=f"No NamedEntity found with name {name}")

            return {"namedentities": namedentities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/get_statements/", response_model=List[Statement], description="Get all statements connected to the given named entity.")
def get_statements(namedentity_id: str):
    named_entity = read_namedentity(namedentity_id)
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (s:Statement)-[:IS_ABOUT]->(n:NamedEntity {namedentity_id: $namedentity_id})
                RETURN s.text AS text, s.statement_id AS statement_id
            """, namedentity_id=named_entity.namedentity_id)

            mentioned_result = session.run("""
                MATCH (s:Statement {statement_id: $statement_id})-[:MENTIONS]->(m:NamedEntity)
                RETURN m.namedentity_id AS mentioned_id
            """, statement_id=statement_id)

            statements = []
            for record in result+mentioned_result:
                statement_id = record["statement_id"]
                text = record["text"]

                if text is None or statement_id is None:
                    raise HTTPException(status_code=500, detail="Statement data is incomplete")

                statement = Statement(
                    text=text,
                    statement_id=statement_id,
                    about_namedentity_id=named_entity.namedentity_id
                )
                
                statements.append(statement)

        return statements
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update_labels/")
def update_labels(
    namedentity_id: str = Query(...),
    additional_labels: Optional[List[str]] = Query(default=[])
):
    named_entity = read_namedentity(namedentity_id)
    try:
        with driver.session() as session:
            # Step 1: Match the node and extract all its labels
            labels_result = session.run("""
                MATCH (n {namedentity_id: $namedentity_id})
                RETURN labels(n) AS labels
            """, namedentity_id=named_entity.namedentity_id)

            labels = labels_result.single()["labels"]

            # Step 2: Remove all labels from the node
            for label in labels:
                session.run(f"""
                    MATCH (n {{namedentity_id: $namedentity_id}})
                    REMOVE n:`{label}`
                """, namedentity_id=named_entity.namedentity_id)

            # Step 3: Add back the NamedEntity label
            session.run("""
                MATCH (n {namedentity_id: $namedentity_id})
                SET n:NamedEntity
            """, namedentity_id=named_entity.namedentity_id)

            if additional_labels:
                # Step 4: Add the new labels (additional types)
                labels = ":".join(additional_labels)
                session.run(f"""
                    MATCH (n:NamedEntity {{ namedentity_id: $namedentity_id }})
                    SET n:{labels}
                """, namedentity_id=named_entity.namedentity_id)

        return {"message": "NamedEntity types updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/delete/")
def delete(namedentity_id: str):

    # Just return the namedentity_id to ensure it's received correctly
    print(f"deleting {namedentity_id}")

    named_entity = read_namedentity(namedentity_id)

    try:
        with driver.session() as session:
            # Delete all statements connected via `IS_ABOUT` relationship
            result = session.run("""
                MATCH (n:NamedEntity {namedentity_id: $namedentity_id})<-[:IS_ABOUT]-(s:Statement)
                RETURN s.statement_id AS statement_id
            """, namedentity_id=named_entity.namedentity_id)

            for record in result:
                statement_id = record["statement_id"]
                delete_statement_by_id(statement_id)  # Call the refactored delete function directly

            # Delete the NamedEntity itself
            result = session.run("""
                MATCH (n:NamedEntity {namedentity_id: $namedentity_id})
                DETACH DELETE n
            """, namedentity_id=named_entity.namedentity_id)

            summary = result.consume()
            if summary.counters.nodes_deleted == 0:
                raise HTTPException(status_code=404, detail=f"NamedEntity with id {named_entity.namedentity_id} not found")

            return {"message": f"NamedEntity with id {named_entity.namedentity_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

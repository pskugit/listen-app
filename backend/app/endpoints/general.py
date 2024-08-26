from fastapi import APIRouter, HTTPException
from typing import Any, Dict
from app.utils.neo4j import get_driver

label_hirarchy = {"namedentity": "namedentity",
                  "topic": "topic",
                  "statement": "statement",
                  "person": "namedentity"
                  }

router = APIRouter()

# Neo4j driver initialization
driver = get_driver()

@router.get("/describe_graph")
async def describe_graph():
    try:
        with driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n)").single()[0]
            statement_count = session.run("MATCH (s:Statement) RETURN count(s)").single()[0]
            relationship_count = session.run("MATCH ()-[r]->() RETURN count(r)").single()[0]
        return {
            "nodes": node_count,
            "statements": statement_count,
            "relationships": relationship_count
        }
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))


@router.post("/create_node/")
def create_node(label: str, properties: Dict[str, Any]):
    try:
        with driver.session() as session:
            session.run(f"""
                CREATE (n:{label} {{ {", ".join(f"{k}: ${k}" for k in properties.keys())} }})
            """, **properties)
        return {"message": f"{label} created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read_node/")
def read_node(label: str, node_id: str):
    try:
        with driver.session() as session:
            result = session.run(f"""
                MATCH (n:{label} {{ {label_hirarchy[label.lower()]}_id: $node_id }})
                RETURN n
            """, node_id=node_id)

            node = result.single()
            if node is None:
                raise HTTPException(status_code=404, detail=f"{label} with id {node_id} not found")

            return node["n"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/update_node/")
def update_node(label: str, node_id: str, updates: Dict[str, Any]):
    try:
        set_clause = ", ".join([f"n.{key} = ${key}" for key in updates.keys()])
        query = f"""
            MATCH (n:{label} {{ {label.lower()}_id: $node_id }})
            SET {set_clause}
            RETURN n
        """

        with driver.session() as session:
            result = session.run(query, node_id=node_id, **updates)

            updated_node = result.single()
            if updated_node is None:
                raise HTTPException(status_code=404, detail=f"{label} with id {node_id} not found")

            return {"message": f"{label} updated successfully", "node": updated_node["n"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete_node/")
def delete_node(label: str, node_id: str):
    try:
        with driver.session() as session:
            result = session.run(f"""
                MATCH (n:{label} {{ {label.lower()}_id: $node_id }})
                DETACH DELETE n
            """, node_id=node_id)

            summary = result.consume()
            if summary.counters.nodes_deleted == 0:
                raise HTTPException(status_code=404, detail=f"{label} with id {node_id} not found")

            return {"message": f"{label} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.on_event("shutdown")
def shutdown():
    driver.close()

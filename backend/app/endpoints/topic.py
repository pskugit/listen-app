from fastapi import APIRouter, HTTPException
from uuid import uuid4
from app.models import Topic
from app.utils.neo4j import get_driver


router = APIRouter()

# Neo4j driver initialization
driver = get_driver()

@router.post("/create/")
def create(topic: Topic):
    topic_id = topic.topic_id or str(uuid4())
    try:
        with driver.session() as session:
            session.run(""" 
            CREATE (p:Topic {name: $name, topic_id: $topic_id})
            """, name=topic.name, topic_id=topic_id)
        return {"message": "Topic added successfully", "name": topic.name, "topic_id": topic_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update_name/", description="Update the name of an existing Topic.")
def update_name(topic_id: str, new_name: str):
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (t:Topic {topic_id: $topic_id})
                SET t.name = $new_name
                RETURN t
            """, topic_id=topic_id, new_name=new_name)
            
            updated_topic = result.single()
            if updated_topic is None:
                raise HTTPException(status_code=404, detail=f"Topic with id {topic_id} not found")

            return {"message": "Topic name updated successfully", "topic": updated_topic["t"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
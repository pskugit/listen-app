from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from typing import List
from app.models import Topic
from app.utils.neo4j import get_driver

router = APIRouter()

# Neo4j driver initialization
driver = get_driver()

def get_topic_by_id(topic_id: str):
    with driver.session() as session:
        result = session.run("""
            MATCH (t:Topic {topic_id: $topic_id})
            RETURN t
        """, topic_id=topic_id)

        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Topic not found")

        node = record["t"]
        return Topic(
            name=node["name"],
            topic_id=node["topic_id"]
        )


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


@router.get("/read/", response_model=Topic, description="Get a topic based on its ID.")
def read_topic(topic_id: str):
    return get_topic_by_id(topic_id)


@router.get("/list_all_topics/", response_model=List[Topic], description="Get a list of all topics in the graph")
def list_all_topics():
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (t:Topic)
                RETURN t
            """)

            topics = []
            for record in result:
                node = record["t"]
                topic = Topic(
                    name=node["name"],
                    topic_id=node["topic_id"]
                )
                topics.append(topic)

        return topics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update_name/", description="Update the name of an existing Topic.")
def update_name(new_name: str, topic_id: str):
    topic = get_topic_by_id(topic_id)
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (t:Topic {topic_id: $topic_id})
                SET t.name = $new_name
                RETURN t
            """, topic_id=topic.topic_id, new_name=new_name)
            
            updated_topic = result.single()
            if updated_topic is None:
                raise HTTPException(status_code=404, detail=f"Topic with id {topic.topic_id} not found")

            return {"message": "Topic name updated successfully", "topic": updated_topic["t"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/delete/")
def delete(topic_id: str):
    topic = get_topic_by_id(topic_id)
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (t:Topic {topic_id: $topic_id})
                DETACH DELETE t
            """, topic_id=topic.topic_id)

            summary = result.consume()
            if summary.counters.nodes_deleted == 0:
                raise HTTPException(status_code=404, detail=f"Topic with id {topic.topic_id} not found")

            return {"message": f"Topic with id {topic.topic_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

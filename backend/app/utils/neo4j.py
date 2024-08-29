import os
from app.models import NamedEntity, Statement
from neo4j import GraphDatabase

def named_entity_exists(driver, namedentity_id: str) -> bool:
    """Check if a NamedEntity exists in the database."""
    with driver.session() as session:
        result = session.run("""
            MATCH (p:NamedEntity {namedentity_id: $namedentity_id})
            RETURN count(p) > 0 AS exists
        """, namedentity_id=namedentity_id)
        return result.single()[0]


#def get_driver(uri: str = "bolt://neo4j:7687", user: str = "neo4j", password: str = "password"):
#    driver = GraphDatabase.driver(uri, auth=(user, password))
#    return driver

def get_namedentity_by_id(driver, namedentity_id: str):
    with driver.session() as session:
        result = session.run("""
            MATCH (n:NamedEntity {namedentity_id: $namedentity_id})
            RETURN n, labels(n) AS labels
        """, namedentity_id=namedentity_id)

        record = result.single()
        if not record:
            return None 

        node = record["n"]
        labels = record["labels"]

        named_entity = NamedEntity(
            name=node["name"],
            namedentity_id=node["namedentity_id"],
            additional_labels=[label for label in labels if label != "NamedEntity"]
        )
        return named_entity
    

def get_statement_by_id(driver, statement_id: str) -> Statement:
    with driver.session() as session:
        result = session.run("""
            MATCH (s:Statement {statement_id: $statement_id})-[:IS_ABOUT]->(n:NamedEntity)
            RETURN s.text AS text, s.statement_id AS statement_id, n.namedentity_id AS about_namedentity_id
        """, statement_id=statement_id)

        record = result.single()
        if not record:
            return None

        statement = Statement(
            text=record["text"],
            statement_id=record["statement_id"],
            about_namedentity_id=record["about_namedentity_id"],
        )

        return statement


    
def get_driver():
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    print(uri,user)
    driver = GraphDatabase.driver(uri, auth=(user, password))
    return driver
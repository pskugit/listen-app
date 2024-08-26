import os
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


def get_driver():
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    return driver
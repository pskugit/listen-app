from neo4j import GraphDatabase

def named_entity_exists(driver, namedentity_id: str) -> bool:
    """Check if a NamedEntity exists in the database."""
    with driver.session() as session:
        result = session.run("""
            MATCH (p:NamedEntity {namedentity_id: $namedentity_id})
            RETURN count(p) > 0 AS exists
        """, namedentity_id=namedentity_id)
        return result.single()[0]
    
def get_driver():
    driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password"))
    return driver
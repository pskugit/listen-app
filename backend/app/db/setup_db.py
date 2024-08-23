import time
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password"))

def setup_database():
    for _ in range(5):  # Retry 5 times
        try:
            with driver.session() as session:
                session.run("CREATE CONSTRAINT FOR (s:Statement) REQUIRE s.statement_id IS UNIQUE;")
                session.run("CREATE CONSTRAINT FOR (p:NamedEntity) REQUIRE p.namedentity_id IS UNIQUE;")  # Add any other constraints as needed
            break  # Exit the loop if successful
        except ServiceUnavailable:
            print("Neo4j is not available yet, retrying...")
            time.sleep(2)  # Wait before retrying
        except Exception as e:
            print(f"An error occurred: {e}")

def fill_database_with_testdata():
    try:
        with driver.session() as session:
            # Creating test persons
            session.run("CREATE (person1:NamedEntity:Person {name: 'Bob', namedentity_id: 'ne1'})")
            session.run("CREATE (person2:NamedEntity:Person {name: 'Caroline', namedentity_id: 'ne2'})")
            session.run("CREATE (person3:NamedEntity:Person {name: 'Anna', namedentity_id: 'ne3'})")
            
            # Creating test statements and is_about relationships
            session.run("CREATE (statement1:Statement {text: 'Lieblingseis: Zitrone', statement_id: 's1'})")
            session.run("MATCH (person:NamedEntity {namedentity_id: 'ne1'}), (statement:Statement {statement_id: 's1'}) "
                        "CREATE (statement)-[:IS_ABOUT]->(person)")
            
            session.run("CREATE (statement2:Statement {text: 'has a dog', statement_id: 's2'})")
            session.run("MATCH (person:NamedEntity {namedentity_id: 'ne2'}), (statement:Statement {statement_id: 's2'}) "
                        "CREATE (statement)-[:IS_ABOUT]->(person)")
            
            session.run("CREATE (statement:Statement {text: 'Married @Anna in Venice on 26.05.2023', statement_id: 's3'})")
            session.run("MATCH (person1:NamedEntity {namedentity_id: 'ne1'}), (statement:Statement {statement_id: 's3'}) "
                        "CREATE (statement)-[:IS_ABOUT]->(person1)")
            session.run("MATCH (person2:NamedEntity {namedentity_id: 'ne3'}), (statement:Statement {statement_id: 's3'}) "
                        "CREATE (statement)-[:MENTIONS]->(person2)")
            
            # Adding bidirectional MARRIED_TO relationship between Bob and Anna
            session.run("MATCH (person1:NamedEntity {namedentity_id: 'ne1'}), (person2:NamedEntity {namedentity_id: 'ne3'}) "
                        "CREATE (person1)-[:MARRIED_TO {location: 'Venice', date: '2023-05-26', source_statement_id: 's3'}]->(person2)")
            session.run("MATCH (person1:NamedEntity {namedentity_id: 'ne1'}), (person2:NamedEntity {namedentity_id: 'ne3'}) "
                        "CREATE (person2)-[:MARRIED_TO {location: 'Venice', date: '2023-05-26', source_statement_id: 's3'}]->(person1)")
            
    except Exception as e:
        print(f"An error occurred: {e}")


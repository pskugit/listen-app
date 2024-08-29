import os
import pytest
import requests
from app.utils.neo4j import get_driver

# The FastAPI service should be running on port 8001
URL = "http://localhost:8001/"

@pytest.fixture(scope="session", autouse=True)
def set_test_env_vars():
    os.environ["NEO4J_URI"] = "bolt://localhost:7688"
    os.environ["NEO4J_USER"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "test_password"
    yield


@pytest.fixture(scope="module")
def driver():
    driver = get_driver()
    yield driver
    driver.close()  # Ensure the driver is properly closed after tests


@pytest.fixture(scope="module", autouse=True)
def database_setup_and_teardown(driver):
    # Setup: Create necessary constraints
    with driver.session() as session:
        session.run("CREATE CONSTRAINT c1 FOR (s:Statement) REQUIRE s.statement_id IS UNIQUE;")
        session.run("CREATE CONSTRAINT c2 FOR (p:NamedEntity) REQUIRE p.namedentity_id IS UNIQUE;")
    
    yield  # This is where the test runs

    # Teardown: Remove all nodes, relationships, and constraints
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        session.run("DROP CONSTRAINT c1")
        session.run("DROP CONSTRAINT c2")


def test_create_namedentity(driver):
    payload = {"name": "TestEntity", "namedentity_id": "ne1", "additional_labels": ["Person"]}
    response = requests.post(URL + "namedentity/create/", json=payload)
    
    assert response.status_code == 200
    assert response.json() == {
        "message": "NamedEntity added successfully",
        "name": "TestEntity",
        "namedentity_id": "ne1"
    }

    # Verify that the entity was actually created in the database
    with driver.session() as session:
        result = session.run("MATCH (n:NamedEntity {namedentity_id: 'ne1'}) RETURN n")
        record = result.single()
        assert record is not None
        assert record["n"]["name"] == "TestEntity"
        assert "Person" in record["n"].labels


def test_create_namedentity_duplicate(driver):
    # Attempt to create the same NamedEntity again to test for conflict handling
    payload = {
        "name": "TestEntity",
        "namedentity_id": "ne_duplicate",
        "additional_labels": ["Person"]
    }
    
    response = requests.post(URL + "namedentity/create/", json=payload)
    response = requests.post(URL + "namedentity/create/", json=payload)

    # Assuming the app should handle duplicates, adjust this check based on your logic
    assert response.status_code == 500
    assert "detail" in response.json()  # Checking if error detail is returned


def test_remove_entity_and_associated_statements(driver):
    # Create a NamedEntity
    namedentity_payload = {"name": "TestEntityToDelete", "namedentity_id": "ne_delete", "additional_labels": ["Person"]}
    response = requests.post(URL + "namedentity/create/", json=namedentity_payload)
    assert response.status_code == 200

    # Add statements associated with this NamedEntity
    statement_payload1 = {"text": "Statement 1", "statement_id": "s1", "about_namedentity_id": "ne_delete"}
    statement_payload2 = {"text": "Statement 2", "statement_id": "s2", "about_namedentity_id": "ne_delete"}
    requests.post(URL + "statement/create/", json=statement_payload1)
    requests.post(URL + "statement/create/", json=statement_payload2)

    # Delete the NamedEntity
    # Test removing an entity
    namedentity_delete_payload = {"namedentity_id": "ne_delete"}
    response = requests.post(URL + "namedentity/delete/", params=namedentity_delete_payload)
    print(response.json())  # Add this line to see the response message for debugging

    assert response.status_code == 200

    # Verify that the entity and associated statements are deleted
    with driver.session() as session:
        entity = session.run("MATCH (n:NamedEntity {namedentity_id: 'ne_delete'}) RETURN n").single()
        statement1 = session.run("MATCH (s:Statement {statement_id: 's1'}) RETURN s").single()
        statement2 = session.run("MATCH (s:Statement {statement_id: 's2'}) RETURN s").single()
        assert entity is None
        assert statement1 is None
        assert statement2 is None


def test_update_labels_for_named_entity(driver):
    # Step 1: Create a Named Entity
    entity_payload = {"name": "Entity1", "namedentity_id": "ne_update_labels", "additional_labels": ["Person"]}
    response = requests.post(URL + "namedentity/create/", json=entity_payload)
    assert response.status_code == 200

    # Step 2: Update the Labels of the Named Entity
    update_labels_payload = {"namedentity_id": "ne_update_labels", "additional_labels": ["Person", "Employee"]}
    response = requests.post(URL + "namedentity/update_labels/", params=update_labels_payload)
    assert response.status_code == 200
    assert response.json() == {"message": "NamedEntity types updated successfully"}

    # Step 3: Verify that the Labels have been Updated
    with driver.session() as session:
        result = session.run("""
            MATCH (n {namedentity_id: 'ne_update_labels'})
            RETURN labels(n) AS labels
        """).single()

        assert result, "NamedEntity not found"
        labels = result["labels"]
        assert "NamedEntity" in labels, "NamedEntity label is missing"
        assert "Person" in labels, "Person label is missing"
        assert "Employee" in labels, "Employee label is missing"
        assert len(labels) == 3, f"Expected 3 labels, but got {len(labels)}: {labels}"

    # Step 4: Remove all additional labels (optional step)
    update_labels_payload = {"namedentity_id": "ne_update_labels"}
    response = requests.post(URL + "namedentity/update_labels/", params=update_labels_payload)
    assert response.status_code == 200

    # Step 5: Verify that only the NamedEntity label remains
    with driver.session() as session:
        result = session.run("""
            MATCH (n {namedentity_id: 'ne_update_labels'})
            RETURN labels(n) AS labels
        """).single()

        assert result, "NamedEntity not found"
        labels = result["labels"]
        assert "NamedEntity" in labels, "NamedEntity label is missing"
        assert len(labels) == 1, f"Expected 1 label, but got {len(labels)}: {labels}"


def test_create_statemet_and_update_text(driver):
    # Create NamedEntities
    payload = {
        "name": "TestEntity",
        "namedentity_id": "ne2",
        "additional_labels": ["Person"]
    }
    response = requests.post(URL + "namedentity/create/", json=payload)
    assert response.status_code == 200

    # Create a statement
    statement_payload = {"text": "Some statement text", "statement_id": "s1", "about_namedentity_id": "ne2"}
    response = requests.post(URL + "statement/create/", json=statement_payload)
    assert response.status_code == 200

    # Update text of statement
    text_update_payload = {"statement_id": "s1", "new_text": "Some new text"}
    response = requests.post(URL + "statement/update_text/", params=text_update_payload)
    assert response.status_code == 200

    # Verify the text of the statement is now the updated text
    with driver.session() as session:
        result = session.run("""
            MATCH (s:Statement {statement_id: 's1'})
            RETURN s.text AS text
        """).single()
        
        # Ensure the result exists and the text is correctly updated
        assert result, "No statement found with statement_id 's1'"
        assert result["text"] == "Some new text", f"Expected text to be 'new_text', but got {result['text']}"


def test_add_mentions_and_check_connections(driver):
    # Create NamedEntities
    entity1_payload = {"name": "Entity1", "namedentity_id": "ne_mention1", "additional_labels": ["Person"]}
    entity2_payload = {"name": "Entity2", "namedentity_id": "ne_mention2", "additional_labels": ["Person"]}
    response = requests.post(URL + "namedentity/create/", json=entity1_payload)
    response = requests.post(URL + "namedentity/create/", json=entity2_payload)
    assert response.status_code == 200

    # Create a statement
    statement_payload = {"text": "Statement with mentions", "statement_id": "s4", "about_namedentity_id": "ne_mention1"}
    response = requests.post(URL + "statement/create/", json=statement_payload)
    assert response.status_code == 200

    # Add mentions to the statement
    mentions_payload = {
         "mentioned_namedentity_ids": ["ne_mention1", "ne_mention2"],
        "statement_id": "s4"
    }   
    response = requests.post(URL + "statement/update_mentions/", params=mentions_payload)
    assert response.status_code == 200

    # Verify the relationships are created
    with driver.session() as session:
        connection = session.run("""
            MATCH (e1:NamedEntity {namedentity_id: 'ne_mention1'})-[:SOME_RELATION]->(e2:NamedEntity {namedentity_id: 'ne_mention2'})
            RETURN e1, e2
        """).single()
        assert connection is not None

def test_remove_statement_and_derived_relationships(driver):
    # Create NamedEntities
    entity1_payload = {"name": "Entity1", "namedentity_id": "ne_rel1", "additional_labels": ["Person"]}
    entity2_payload = {"name": "Entity2", "namedentity_id": "ne_rel2", "additional_labels": ["Person"]}
    requests.post(URL + "namedentity/create/", json=entity1_payload)
    requests.post(URL + "namedentity/create/", json=entity2_payload)

    # Create a statement and add mentions
    statement_payload = {"text": "Statement to remove", "statement_id": "s5", "about_namedentity_id": "ne_rel1"}
    requests.post(URL + "statement/create/", json=statement_payload)
    mentions_payload = {"statement_id": "s5", "mentioned_namedentity_ids": ["ne_rel1", "ne_rel2"]}
    response = requests.post(URL + "statement/update_mentions/", params=mentions_payload)

    # Verify the relationships exist
    with driver.session() as session:
        connection = session.run("""
            MATCH (e1:NamedEntity {namedentity_id: 'ne_rel1'})-[:SOME_RELATION]->(e2:NamedEntity {namedentity_id: 'ne_rel2'})
            RETURN e1, e2
        """).single()
        assert connection is not None

    # Delete the statement
    response = requests.post(URL + "statement/delete/", params={"statement_id": "s5"})
    assert response.status_code == 200

    # Verify that the relationships based on the statement are removed
    with driver.session() as session:
        connection = session.run("""
            MATCH (e1:NamedEntity {namedentity_id: 'ne_rel1'})-[:SOME_RELATION]->(e2:NamedEntity {namedentity_id: 'ne_rel2'})
            RETURN e1, e2
        """).single()
        assert connection is None

def test_set_topic_and_update_name(driver):
    # Step 0: Create a Named Entity
    entity_payload = {"name": "Entity1", "namedentity_id": "ne_topic1", "additional_labels": ["Person"]}
    requests.post(URL + "namedentity/create/", json=entity_payload)
    
    # Step 1: Create a Topic
    topic_payload = {"topic_id": "t1", "name": "Topic 1"}
    response = requests.post(URL + "topic/create/", json=topic_payload)
    assert response.status_code == 200

    # Step 2: Create a Statement
    statement_payload = {"text": "Statement to remove", "statement_id": "s_topic", "about_namedentity_id": "ne_topic1"}
    response = requests.post(URL + "statement/create/", json=statement_payload)
    assert response.status_code == 200

    # Step 3: Set the Topic for the Statement
    set_topic_payload = {"statement_id": "s_topic", "topic_id": "t1"}
    response = requests.post(URL + "statement/set_topic/", params=set_topic_payload)
    assert response.status_code == 200
    assert response.json() == {"message": "Topic set successfully for the statement"}

    # Step 4: Verify that the HAS_TOPIC relationship has been created
    with driver.session() as session:
        result = session.run("""
            MATCH (s:Statement {statement_id: 's_topic'})-[:HAS_TOPIC]->(t:Topic {topic_id: 't1'})
            RETURN s, t
        """).single()
        assert result, "HAS_TOPIC relationship was not created"
        assert result["s"]["statement_id"] == "s_topic"
        assert result["t"]["topic_id"] == "t1"
        assert result["t"]["name"] == "Topic 1"

    # Step 5: Update the Topic's Name
    update_name_payload = {"topic_id": "t1", "new_name": "Updated Topic Name"}
    response = requests.post(URL + "topic/update_name/", params=update_name_payload)
    assert response.status_code == 200

    # Step 6: Verify that the Topic's Name has been Updated
    with driver.session() as session:
        result = session.run("""
            MATCH (t:Topic {topic_id: 't1'})
            RETURN t.name AS name
        """).single()
        assert result, "Topic not found"
        assert result["name"] == "Updated Topic Name", f"Expected 'Updated Topic Name', got {result['name']}"

    # Step 7: Remove the Topic from the Statement by setting topic_id to None
    set_topic_payload = {"statement_id": "s_topic", "topic_id": None}
    response = requests.post(URL + "statement/set_topic/", params=set_topic_payload)
    assert response.status_code == 200
    assert response.json() == {"message": "Topic removed from the statement"}

    # Step 8: Verify that the HAS_TOPIC relationship has been removed
    with driver.session() as session:
        result = session.run("""
            MATCH (s:Statement {statement_id: 's_topic'})-[:HAS_TOPIC]->(t:Topic)
            RETURN s, t
        """).single()
        assert not result, "HAS_TOPIC relationship was not removed"

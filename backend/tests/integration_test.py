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
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Statement) REQUIRE s.statement_id IS UNIQUE;")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:NamedEntity) REQUIRE p.namedentity_id IS UNIQUE;")
    
    yield  # This is where the test runs

    # Teardown: Remove all nodes, relationships, and constraints
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        session.run("DROP CONSTRAINT IF EXISTS ON (s:Statement) ASSERT s.statement_id IS UNIQUE")
        session.run("DROP CONSTRAINT IF EXISTS ON (p:NamedEntity) ASSERT p.namedentity_id IS UNIQUE")


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
        "namedentity_id": "ne1",
        "additional_labels": ["Person"]
    }
    
    response = requests.post(URL + "namedentity/create/", json=payload)

    # Assuming the app should handle duplicates, adjust this check based on your logic
    assert response.status_code == 500
    assert "detail" in response.json()  # Checking if error detail is returned


def test_cleanup(driver):
    # Clean up the test NamedEntity to ensure it doesn't interfere with other tests
    with driver.session() as session:
        session.run("MATCH (n:NamedEntity {namedentity_id: 'ne1'}) DETACH DELETE n")

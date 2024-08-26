import requests

def test_create_namedentity():
    url = "http://localhost:8001/create"  # The FastAPI service should be running on port 8001
    payload = {"name": "Test Entity", "namedentity_id": "ne1"}
    response = requests.post(url, json=payload)
    
    assert response.status_code == 200
    assert response.json() == {
        "message": "NamedEntity added successfully",
        "name": "Test Entity",
        "namedentity_id": "ne1"
    }

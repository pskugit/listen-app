# API Documentation

API documentation for all existing data classes, structured clearly with properties, requirements, and examples for each.

## NamedEntity

Represents an individual entity with personal information.

### Properties
- `name` (string, required): The name of the entity.
- `namedentity_id` (string, optional): A unique identifier for the entity.

### Example
```json
{
    "name": "Alice",
    "namedentity_id": "ne1"
}
```

---

## Statement

Represents a statement related to a NamedEntity.

### Properties
- `statement_text` (string, required): The text of the statement.
- `statement_id` (string, optional): A unique identifier for the statement.
- `about_namedentity_id` (string, required): The ID of the NamedEntity this statement is about.
- `mentioned_namedentity_ids` (array of strings, optional): IDs of other entities mentioned in the statement.

### Example
```json
{
    "statement_text": "Married @Anna in Venice on 26.05.2023",
    "statement_id": "s3",
    "about_namedentity_id": "ne1",
    "mentioned_namedentity_ids": ["ne2", "ne3"]
}
```

---

## RelationshipAttributes

Represents the attributes of a relationship.

### Properties
- `source_statement_id` (string, required): The ID of the statement that is the source of this relationship.
- `additional_properties` (object, optional): Any additional properties related to the relationship.

### Example
```json
{
    "source_statement_id": "s3",
    "additional_properties": {
        "extra_info": "Any additional data can go here."
    }
}
```

---

## Relationship

Defines the structure of a relationship between two nodes.

### Properties
- `from_node` (string, required): The ID of the starting node in the relationship.
- `to_node` (string, required): The ID of the ending node in the relationship.
- `relationship` (string, required): The type of relationship (e.g., "IS_ABOUT", "MENTIONS").
- `attributes` (RelationshipAttributes, required): The attributes associated with this relationship.

### Example
```json
{
    "from_node": "ne1",
    "to_node": "ne2",
    "relationship": "IS_ABOUT",
    "attributes": {
        "source_statement_id": "s3"
    }
}
```

---

## Connection

Represents a connection between a NamedEntity and its relationship.

### Properties
- `connected_entity` (NamedEntity, required): The entity that is connected.
- `relationship` (Relationship, required): The relationship object defining the connection.

### Example
```json
{
    "connected_entity": {
        "name": "Bob",
        "namedentity_id": "ne2"
    },
    "relationship": {
        "from_node": "ne1",
        "to_node": "ne2",
        "relationship": "MENTIONS",
        "attributes": {
            "source_statement_id": "s4"
        }
    }
}
```
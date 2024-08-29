

from app.models import Statement

def is_uppercase_and_underscore(s: str):
    return not s.isupper() or not all(c.isalpha() or c == '_' for c in s)

def derive_relation_type_from_statement(statement: Statement):

    text = statement.about_namedentity_id
    statement.me
    relation_type="SOME_RELATION"
    is_directional = False
    return relation_type, is_directional
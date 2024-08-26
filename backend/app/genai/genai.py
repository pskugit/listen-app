



def is_uppercase_and_underscore(s: str):
    return not s.isupper() or not all(c.isalpha() or c == '_' for c in s)

def derive_relation_type_from_text(text: str):
    relation_type="SOME_RELATION"
    return relation_type
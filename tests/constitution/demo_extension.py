"""External composition demonstration; imported only by verification tests."""
from runtime.constitution import ConstitutionalExtensions

def build_extension() -> ConstitutionalExtensions:
    extension = ConstitutionalExtensions()
    extension.register_kind("demonstration", {"id":"demonstration","description":"Verification-only semantic kind."})
    extension.register_schema("demonstration-schema", {"id":"demonstration-schema","kind":"demonstration","version":"1.0.0","required":[]})
    extension.register_doctrine("demonstration-doctrine", {"id":"demonstration-doctrine","kind":"doctrine"})
    extension.register_projection("demonstration-projection", lambda objects, graph: {"count":len(objects)})
    extension.register_validator("demonstration-validator", lambda value: bool(value))
    return extension

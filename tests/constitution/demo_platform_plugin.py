"""External platform plugin: constitutional definition plus implementation."""
from runtime.constitution import ConstitutionalPlugin, SubsystemAttachment

def execute(value): return value

def entrypoint():
    definition={
        "id":"service:demonstration-plugin","kind":"service","canonical_name":"Demonstration Plugin",
        "display_name":"Demonstration Plugin","description":"External verification capability.",
        "authority":{"state":"provisional","source":"tests/constitution/demo_platform_plugin.py"},"status":"active","version":"1.0.0",
        "created_at":"2026-07-21T00:00:00Z","updated_at":"2026-07-21T00:00:00Z",
        "lineage":{"parent":"domain:services","supersedes":[],"superseded_by":[]},
        "provenance":{"sources":["tests/constitution/demo_platform_plugin.py"]},
        "relationships":[{"type":"owned_by","target":"faculty:execution"},{"type":"implemented_through","target":"exile:coda"}],
        "dependencies":["faculty:execution","exile:coda"],"metadata":{"implementation_refs":["tests/constitution/demo_platform_plugin.py"]},
    }
    subsystem=SubsystemAttachment("service:demonstration-plugin",__file__)
    return ConstitutionalPlugin("plugin:demonstration","1.0.0",(definition,),subsystem)

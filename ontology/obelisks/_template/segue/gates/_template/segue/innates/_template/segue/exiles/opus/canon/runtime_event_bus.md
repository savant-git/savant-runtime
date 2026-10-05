# RUNTIME EVENT BUS
# STATUS: CANON
# OWNER: OPUS
# PURPOSE: SHARED EVENT STREAM FOR ALL EXILES

All significant runtime actions should emit events.

Events must expose:

- id
- type
- source
- payload
- request_id
- response_id
- lineage
- authority
- graph
- timestamps

Events should not require direct coupling between exiles.

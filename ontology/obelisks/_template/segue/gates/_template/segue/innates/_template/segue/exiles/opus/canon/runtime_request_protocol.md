# RUNTIME REQUEST PROTOCOL
# STATUS: CANON
# OWNER: OPUS
# PURPOSE: SHARED REQUEST/RESPONSE ABI FOR ALL EXILES

All exiles must communicate through a shared runtime request/response object.

The protocol exposes:

- id
- type
- source
- destination
- authority
- lineage
- graph
- context
- payload
- attachments
- metadata
- timestamps

No exile should depend on another exile's private internal format.

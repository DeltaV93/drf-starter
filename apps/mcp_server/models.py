"""Deliberately empty.

The MCP server owns no data. Every tool reaches the application through
`call_api`, which makes a real request against the existing API -- so there is
no state here to model, and no migration to apply.

That is also what keeps the flag independent: turning MCP off removes an
endpoint, not a table.
"""

"""Standards retrieval: the single entry point for Georgia standards.

Phase 1 stub: returns the standards already seeded in the `standards` table.
Later this module retrieves GaDOE CASE data (case.georgiastandards.org)
through the Bedrock Knowledge Base. Callers only depend on the return shape
documented below, so nothing outside this file changes.

The model never supplies standard codes. Every code the app shows comes
through retrieve_standards().
"""

from app.db_connect import query_all


def retrieve_standards(standards_set: str) -> list[dict]:
    """Return every standard in a standards set, ordered by code.

    Input:  standards_set, e.g. "GSE Science Grade 6" (matches units.standards_set).
    Output: list of dicts with standard_id, code, description, standards_set,
            source_url, framework. Empty list if the set is unknown.
    Side effects: none (read-only).
    """
    return query_all(
        "SELECT standard_id, code, description, standards_set, source_url, framework "
        "FROM standards WHERE standards_set = %s ORDER BY code",
        (standards_set,),
    )

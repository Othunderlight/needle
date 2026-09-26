def _build_alias_map(db: dict) -> dict:
    mapping = {}
    for key, data in db.items():
        mapping[key] = key
        for alias in data.get("aliases", []):
            mapping[alias.lower().strip()] = key
    return mapping

def _fuzzy_lookup(query: str, alias_map: dict, cutoff: float = 0.75) -> str | None:
    """Fuzzy searches a query string inside an alias mapping."""
    if not query:
        return None

    query = query.lower().strip()

    # 1. Exact match
    if query in alias_map:
        return alias_map[query]

    # 2. Substring matching
    for alias, key in alias_map.items():
        if query in alias or alias in query:
            return key

    # 3. Difflib close match
    matches = get_close_matches(query, list(alias_map.keys()), n=1, cutoff=cutoff)
    if matches:
        return alias_map[matches[0]]

    return None

# Fix: ChromaDB Result Count Clamp and Report Time Validation

## Bug 1 — ChromaDB Crashes When top_k Exceeds Collection Size

### Summary
Vector search failed with an unhandled `ValueError` whenever `top_k` was larger than the number of items in a collection — a common situation on new installs or small datasets.

### Root Cause
`collection.query(n_results=top_k)` was called without checking the current collection size. ChromaDB requires `n_results <= collection.count()`.

### Bug Flow

```mermaid
flowchart TD
    A[Search with top_k=10] --> B[collection.count = 3]
    B --> C[collection.query n_results=10]
    C --> D[ChromaDB: n_results 10 > collection size 3]
    D --> E[ValueError — unhandled 500 error]
```

### Fix Flow

```mermaid
flowchart TD
    A[Search with top_k=10] --> B[count = collection.count = 3]
    B --> C{count == 0?}
    C -- Yes --> D[Skip collection, return empty]
    C -- No --> E[n_results = min 10, 3 = 3]
    E --> F[collection.query n_results=3]
    F --> G[Returns up to 3 results — no crash]
```

---

## Bug 2 — Report Schedule Accepts Invalid Times Like "25:61"

### Summary
The scheduler accepted times like `"25:61"` as valid, leading to errors at execution time rather than at configuration time.

### Root Cause
`ReportConfig.time` used the regex `^\d{2}:\d{2}$` which validated format but not value range.

### Bug Flow

```mermaid
flowchart TD
    A[User sets schedule time to 25:61] --> B[Regex check: matches dd:dd pattern]
    B --> C[Validation passes]
    C --> D[Config saved to database]
    D --> E[Scheduler runs at 25:61]
    E --> F[BUG: invalid time causes scheduler error]
```

### Fix Flow

```mermaid
flowchart TD
    A[User sets schedule time to 25:61] --> B[Regex check: matches dd:dd pattern]
    B --> C[field_validator runs]
    C --> D{hour in 0-23 and minute in 0-59?}
    D -- No --> E[ValueError: time must be HH:MM 00:00–23:59]
    D -- Yes --> F[Validation passes]
    F --> G[Config saved and scheduler works correctly]
```

## Files Changed

| File | Change |
|------|--------|
| `opencontext/storage/backends/chromadb_backend.py` | `n_results=min(top_k, count)` before collection.query |
| `opencontext/server/routes/content_generation.py` | Added `field_validator` for hour/minute range check |

## PR Description

**Title:** `fix(storage,api): clamp ChromaDB result count and validate report schedule time`

ChromaDB raises ValueError when n_results exceeds the collection item count. Applied min(top_k, count) before querying, matching the pattern already used in search_similar_todos().

ReportConfig.time accepted invalid times like "25:61" that passed the regex but caused scheduler errors. Added a field_validator to check hour 0-23 and minute 0-59.

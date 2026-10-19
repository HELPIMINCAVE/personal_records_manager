from datetime import datetime
from typing import List, Optional
from models import RecordEntity

class QueryError(Exception):
    """Base exception for search and query execution errors."""
    pass

class QueryValidationError(QueryError):
    """Raised when search parameters (such as boundary dates) are malformed."""
    pass

def filter_by_category(records: List[RecordEntity], category: Optional[str]) -> List[RecordEntity]:
    """
    Filters records by exact category match (case-insensitive).
    Returns all records if category is None, empty, or set to 'All'.
    """
    if not category or not category.strip() or category.strip().lower() == "all":
        return records
    
    normalized_target = category.strip().lower()
    return [record for record in records if record.category.lower() == normalized_target]

def filter_by_keyword(records: List[RecordEntity], keyword: Optional[str]) -> List[RecordEntity]:
    """
    Executes a tokenized full-text keyword search across record titles,
    content bodies, and tags using an ALL-tokens match (Logical AND) rule.
    """
    if not keyword or not keyword.strip():
        return records
    
    # Split query into individual lowercased tokens
    tokens = keyword.strip().lower().split()
    if not tokens:
        return records
    
    matching_records: List[RecordEntity] = []
    for record in records:
        tags_str = " ".join(record.tags)
        # Construct unified search buffer
        search_buffer = f"{record.title} {record.content} {tags_str}".lower()
        
        # Verify that every search token is present in the record buffer
        if all(token in search_buffer for token in tokens):
            matching_records.append(record)
    
    return matching_records

def filter_by_date_range(
        records: List[RecordEntity],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
) -> List[RecordEntity]:
    """
    Filters records within optional YYYY-MM-DD date boundaries (inclusive).
    Raises QueryValidationError if date boundary strings are improperly formatted.
    """
    if not start_date and not end_date:
        return records
    
    try:
        start_bound = (
            datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
            if start_date and start_date.strip()
            else None
        )
        end_bound = (
            datetime.strptime(end_date.strip(), "%Y-%m-%d").date()
            if end_date and end_date.strip()
            else None
        )
    except ValueError as err:
        raise QueryValidationError(
            f"Invalid search date boundary format. Must be YYYY-MM-DD: {err}"
        ) from err
    
    matching_records: List[RecordEntity] = []
    for record in records:
        record_date = datetime.strptime(record.date, "%Y-%m-%d").date()
        
        if start_bound and record_date < start_bound:
            continue
        if end_bound and record_date > end_bound:
            continue
        
        matching_records.append(record)
    
    return matching_records

def sort_records(
        records: List[RecordEntity],
        sort_by: str = "date",
        reverse: bool = True
) -> List[RecordEntity]:
    """
    Sorts a collection of records by 'date', 'created_at', or 'title'.
    Defaults to descending order (newest first).
    """
    valid_sort_keys = {"date", "created_at", "title"}
    key = sort_by if sort_by in valid_sort_keys else "date"
    
    if key == "date":
        return sorted(
            records,
            key=lambda r: datetime.strptime(r.date, "%Y-%m-%d"),
            reverse=reverse
        )
    elif key == "created_at":
        return sorted(records, key=lambda r: r.created_at, reverse=reverse)
    elif key == "title":
        return sorted(records, key=lambda r: r.title.lower(), reverse=reverse)
    
    return records

def search_records(
        records: List[RecordEntity],
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort_by: str = "date",
        reverse: bool = True
) -> List[RecordEntity]:
    """
    Master query orchestrator. Chains category, keyword, and date range filters
    sequentially, then applies sorting to the final refined result set.
    """
    working_set = filter_by_category(records, category)
    working_set = filter_by_keyword(working_set, keyword)
    working_set = filter_by_date_range(working_set, start_date, end_date)
    
    return sort_records(working_set, sort_by=sort_by, reverse=reverse)
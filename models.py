import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Union

# --- Domain Exceptions ---

class RecordError(Exception):
    """Base exception for all domain-level record errors."""
    pass


class RecordValidationError(RecordError):
    """Raised when record input fails formatting, boundary, or value constraints."""
    pass


class RecordDataIntegrityError(RecordError):
    """Raised when a dictionary payload from disk is corrupted or missing required keys."""
    pass


# --- Domain Constants ---

ALLOWED_CATEGORIES: Set[str] = {"Health", "Certificate", "Note", "Finance"}

# --- Record Entity Model ---

@dataclass(kw_only=True)
class RecordEntity:
    """
    Represents a single personal record entity with automated post-initialization
    validation, field cleaning, and dictionary serialization logic.
    """
    title: str
    category: str
    date: str
    content: str
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tags: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    def __post_init__(self) -> None:
        """Executes automated field cleaning and validation checks upon instantiation."""
        self.title = self._clean_and_validate_text(self.title, "Title")
        self.content = self._clean_and_validate_text(self.content, "Content")
        self.category = self._clean_and_validate_category(self.category)
        self.date = self._clean_and_validate_date(self.date)
        self.tags = self._clean_and_deduplicate_tags(self.tags)
    
    @staticmethod
    def _clean_and_validate_text(value: str, field_name: str) -> str:
        """Strips whitespace and verifies the field is non-empty."""
        if not isinstance(value, str):
            raise RecordValidationError(f"{field_name} must be a string.")
        
        cleaned = value.strip()
        if not cleaned:
            raise RecordValidationError(
                f"{field_name} cannot be empty or consist only of whitespace."
            )
        return cleaned
    
    @staticmethod
    def _clean_and_validate_category(category_value: str) -> str:
        """Strips whitespace, normalizes to Title Case, and enforces allowed choices."""
        if not isinstance(category_value, str):
            raise RecordValidationError("Category must be a string.")
        
        normalized = category_value.strip().title()
        if normalized not in ALLOWED_CATEGORIES:
            allowed_str = ", ".join(sorted(ALLOWED_CATEGORIES))
            raise RecordValidationError(
                f"Invalid category '{category_value}'. Allowed options: {allowed_str}."
            )
        return normalized
    
    @staticmethod
    def _clean_and_validate_date(date_value: str) -> str:
        """Strips whitespace and verifies strict YYYY-MM-DD ISO calendar date format."""
        if not isinstance(date_value, str):
            raise RecordValidationError("Date must be a string.")
        
        cleaned = date_value.strip()
        try:
            datetime.strptime(cleaned, "%Y-%m-%d")
        except ValueError:
            raise RecordValidationError(
                f"Invalid date '{date_value}'. Must be a valid date in YYYY-MM-DD format."
            )
        return cleaned
    
    @staticmethod
    def _clean_and_deduplicate_tags(raw_tags: Union[List[str], str]) -> List[str]:
        """
        Normalizes tag strings or lists by trimming spaces, converting to lower case,
        ignoring blanks, and removing duplicates while preserving insertion order.
        """
        if isinstance(raw_tags, str):
            tag_iterable = raw_tags.split(",")
        elif isinstance(raw_tags, list):
            tag_iterable = raw_tags
        else:
            raise RecordValidationError(
                "Tags must be a list of strings or a comma-separated string."
            )
        
        clean_tags: List[str] = []
        for tag in tag_iterable:
            if not isinstance(tag, str):
                continue
            cleaned_tag = tag.strip().lower()
            if cleaned_tag and cleaned_tag not in clean_tags:
                clean_tags.append(cleaned_tag)
        
        return clean_tags
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializes the RecordEntity instance into a standard Python dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecordEntity":
        """
        Factory constructor that constructs and validates a RecordEntity from a JSON dictionary payload.

        Raises RecordDataIntegrityError if mandatory keys are missing or invalid.
        """
        if not isinstance(data, dict):
            raise RecordDataIntegrityError("Payload must be a dictionary.")
        
        # Verify mandatory keys before passing to constructor
        required_keys = {"title", "category", "date", "content"}
        missing_keys = required_keys - data.keys()
        if missing_keys:
            missing_str = ", ".join(sorted(missing_keys))
            raise RecordDataIntegrityError(
                f"Corrupt record payload: missing required field(s): {missing_str}."
            )
        
        try:
            return cls(
                title=data["title"],
                category=data["category"],
                date=data["date"],
                content=data["content"],
                id=data.get("id", str(uuid.uuid4())),
                tags=data.get("tags", []),
                created_at=data.get(
                    "created_at", datetime.now(timezone.utc).isoformat()
                ),
                updated_at=data.get(
                    "updated_at", datetime.now(timezone.utc).isoformat()
                ),
            )
        except RecordValidationError as err:
            raise RecordDataIntegrityError(
                f"Corrupt record data payload: {err}"
            ) from err
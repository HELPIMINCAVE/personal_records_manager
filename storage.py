import json, os, tempfile
from pathlib import Path
from typing import List, Union
from models import RecordDataIntegrityError, RecordEntity

# --- Custom Storage Exceptions ---

class StorageError(Exception):
    """Base exception for all storage and file-system level errors."""
    pass

class StorageFileCorruptError(StorageError):
    """Raised when disk JSON payload cannot be parsed or is corrupted."""
    pass

class RecordNotFoundError(StorageError):
    """Raised when an operation targets a record ID that does not exist."""
    pass

# --- File Helper Operations ---

def ensure_storage_file_exists(file_path: Union[str, os.PathLike]) -> Path:
    """
    Guarantees the target JSON storage file and parent directories exist.
    Initializes an empty JSON array if the file is missing.

    Returns the resolved Path object.
    """
    if isinstance(file_path, str) and not file_path.strip():
        raise StorageError("Storage file path cannot be empty.")

    path = Path(file_path).resolve()

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            # Write empty JSON array using exclusive creation ('x') to prevent race conditions
            try:
                with path.open("x", encoding="utf-8") as file:
                    json.dump([], file, indent=2)
            except FileExistsError:
                pass  # Created concurrently by another process
    except OSError as err:
        raise StorageError(f"Failed to initialize storage file at '{path}': {err}") from err

    return path


def atomic_save_json(file_path: Union[str, os.PathLike], data: list) -> None:
    """
    Safely writes a list of dictionary records to disk using atomic replacement.
    Writes to a temporary file first, flushes disk buffers, and replaces the target file.
    """
    target_path = Path(file_path).resolve()
    directory = target_path.parent
    directory.mkdir(parents=True, exist_ok=True)

    tmp_path = None
    try:
        # Create temporary file in the same directory to guarantee atomic replace across the same file system
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=directory,
            delete=False,
            encoding="utf-8",
            suffix=".tmp"
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            json.dump(data, tmp_file, indent=2, ensure_ascii=False)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        # OS-level atomic replace operation
        tmp_path.replace(target_path)
    except Exception as err:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise StorageError(f"Failed to atomically write data to '{target_path}': {err}") from err


# --- Storage CRUD API ---

def load_all_records(file_path: Union[str, os.PathLike]) -> List[RecordEntity]:
    """
    Loads all records from disk, deserializing JSON objects into RecordEntity instances.
    Skips corrupted individual records while parsing valid entries.
    """
    path = ensure_storage_file_exists(file_path)

    try:
        with path.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)
    except json.JSONDecodeError as err:
        raise StorageFileCorruptError(
            f"Storage file at '{path}' contains invalid JSON: {err}"
        ) from err
    except OSError as err:
        raise StorageError(f"Error reading storage file '{path}': {err}") from err

    if not isinstance(raw_data, list):
        raise StorageFileCorruptError(
            f"Storage file at '{path}' must contain a top-level JSON list."
        )

    records: List[RecordEntity] = []
    for item in raw_data:
        if not isinstance(item, dict):
            continue
        try:
            record = RecordEntity.from_dict(item)
            records.append(record)
        except RecordDataIntegrityError:
            # Skip unparseable record dictionaries gracefully
            continue

    return records


def save_all_records(file_path: Union[str, os.PathLike], records: List[RecordEntity]) -> None:
    """Serializes a list of RecordEntity instances and saves them atomically to disk."""
    serialized_data = [record.to_dict() for record in records]
    atomic_save_json(file_path, serialized_data)


def save_record(file_path: Union[str, os.PathLike], record: RecordEntity) -> None:
    """Appends a new record or updates an existing record matching the target ID."""
    records = load_all_records(file_path)
    updated = False

    for i, existing in enumerate(records):
        if existing.id == record.id:
            records[i] = record
            updated = True
            break

    if not updated:
        records.append(record)

    save_all_records(file_path, records)


def get_record_by_id(file_path: Union[str, os.PathLike], record_id: str) -> RecordEntity:
    """
    Retrieves a single RecordEntity by its unique ID.
    Raises RecordNotFoundError if no matching ID exists.
    """
    records = load_all_records(file_path)
    for record in records:
        if record.id == record_id:
            return record

    raise RecordNotFoundError(f"Record with ID '{record_id}' was not found.")


def delete_record_by_id(file_path: Union[str, os.PathLike], record_id: str) -> RecordEntity:
    """
    Deletes a record matching the given ID from storage and saves changes.
    Returns the deleted RecordEntity instance.
    Raises RecordNotFoundError if the ID does not exist.
    """
    records = load_all_records(file_path)
    target_index = None

    for i, record in enumerate(records):
        if record.id == record_id:
            target_index = i
            break

    if target_index is None:
        raise RecordNotFoundError(f"Cannot delete: Record with ID '{record_id}' not found.")

    deleted_record = records.pop(target_index)
    save_all_records(file_path, records)
    return deleted_record
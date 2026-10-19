import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from models import RecordEntity, RecordValidationError
from search import QueryValidationError, search_records, sort_records
from storage import *

DEFAULT_STORAGE_PATH = Path("data") / "records.json"

def print_header(title: str) -> None:
    """Prints a formatted section header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_success(message: str) -> None:
    """Prints a success message in plain text formatting"""
    print(f"[SUCCESS] {message}")


def print_error(message: str) -> None:
    """Prints an error alert message"""
    print(f"[ERROR] {message}")


def display_records_table(records: list[RecordEntity]) -> None:
    """Displays a formatted tabular summary of records for console output"""
    if not records:
        print("\nNo records found matching your criteria.")
        return
    
    print(f"\nFound {len(records)} record(s):\n")
    print(f"{'ID Snippet':<12} | {'Date':<10} | {'Category':<12} | {'Title'}")
    print("-" * 75)
    for r in records:
        id_snippet = f"{r.id[:8]}..."
        print(f"{id_snippet:<12} | {r.date:<10} | {r.category:<12} | {r.title}")
    print("-" * 75)

def handle_add_record(file_path: Path) -> None:
    """Orchestrates the workflow for creating and saving a new record"""
    print_header("Create New Personal Record")
    print("Allowed Categories: Health, Certificate, Note, Finance")
    
    try:
        category = input("Enter category: ").strip()
        title = input("Enter title: ").strip()
        date = input("Enter date (YYYY-MM-DD): ").strip()
        content = input("Enter content / notes: ").strip()
        tags_input = input("Enter tags (comma-separated): ").strip()
        
        # Construct and validate record entity via models.py
        new_record = RecordEntity(
            title=title,
            category=category,
            date=date,
            content=content,
            tags=tags_input
        )
        
        # Persist record via storage.py
        save_record(file_path, new_record)
        print_success(f"Record successfully created! (ID: {new_record.id})")
    
    except RecordValidationError as err:
        print_error(f"Validation Error: {err}")
    except StorageError as err:
        print_error(f"Persistence Error: {err}")

def handle_search_records(file_path: Path) -> None:
    """Orchestrates the multi-criteria search, filtering, and sorting workflow."""
    print_header("Search & Filter Records")
    
    keyword = input("Enter keyword search (press Enter to skip): ").strip()
    category = input("Enter category filter (Health/Certificate/Note/Finance, or Enter for all): ").strip()
    start_date = input("Enter start date boundary (YYYY-MM-DD, or Enter to skip): ").strip()
    end_date = input("Enter end date boundary (YYYY-MM-DD, or Enter to skip): ").strip()
    
    sort_choice = input("Sort by [date / title / created_at] (default: date): ").strip().lower()
    order_choice = input("Sort order [newest / oldest] (default: newest): ").strip().lower()
    
    try:
        all_records = load_all_records(file_path)
        
        sort_key = sort_choice if sort_choice in {"date", "title", "created_at"} else "date"
        reverse_order = False if order_choice == "oldest" else True
        
        # FIXED: Changed 'records_list' to 'records' to match search.py signature
        results = search_records(
            records=all_records,
            category=category if category else None,
            keyword=keyword if keyword else None,
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None,
            sort_by=sort_key,
            reverse=reverse_order
        )
        
        display_records_table(results)
    
    except (QueryValidationError, StorageError) as err:
        print_error(f"Search Execution Error: {err}")

def handle_view_all_records(file_path: Path) -> None:
    """Loads and displays all stored records sorted by date descending"""
    print_header("All Personal Records")
    try:
        all_records = load_all_records(file_path)
        if not all_records:
            print("No records found in storage.")
            return
        
        sorted_records = sort_records(all_records, sort_by="date", reverse=True)
        display_records_table(sorted_records)
    
    except StorageError as err:
        print_error(f"Failed to load records: {err}")


def handle_record_detail_action(file_path: Path) -> None:
    """Handles viewing full details, updating, or deleting a specific record by ID"""
    print_header("View / Manage Record by ID")
    target_id = input("Enter exact Record ID (or first 8+ characters): ").strip()
    
    if not target_id:
        print_error("ID cannot be empty.")
        return
    
    try:
        all_records = load_all_records(file_path)
        matching_record: Optional[RecordEntity] = None
        
        # Support partial ID matching for convenience
        for record in all_records:
            if record.id.startswith(target_id):
                matching_record = record
                break
        
        if not matching_record:
            raise RecordNotFoundError(f"No record found matching ID prefix '{target_id}'.")
        
        # Display full detailed record view
        print("\n" + "-" * 50)
        print(f"ID          : {matching_record.id}")
        print(f"Title       : {matching_record.title}")
        print(f"Category    : {matching_record.category}")
        print(f"Date        : {matching_record.date}")
        print(f"Tags        : {', '.join(matching_record.tags)}")
        print(f"Created At  : {matching_record.created_at}")
        print(f"Updated At  : {matching_record.updated_at}")
        print("Content     :")
        print(f"  {matching_record.content}")
        print("-" * 50)
        
        print("\nActions: [1] Update Record  [2] Delete Record  [3] Back to Menu")
        action = input("Select action (1-3): ").strip()
        
        if action == "2":
            confirm = input("Are you sure you want to delete this record? (y/n): ").strip().lower()
            if confirm == "y":
                delete_record_by_id(file_path, matching_record.id)
                print_success("Record successfully deleted from storage.")
            else:
                print("Deletion cancelled.")
        
        elif action == "1":
            print("\nEnter new values (press Enter to keep existing value):")
            new_title = input(f"Title [{matching_record.title}]: ").strip()
            new_category = input(f"Category [{matching_record.category}]: ").strip()
            new_date = input(f"Date [{matching_record.date}]: ").strip()
            new_content = input(f"Content [{matching_record.content}]: ").strip()
            new_tags_str = input(f"Tags [{', '.join(matching_record.tags)}]: ").strip()
            
            final_title = new_title if new_title else matching_record.title
            final_category = new_category if new_category else matching_record.category
            final_date = new_date if new_date else matching_record.date
            final_content = new_content if new_content else matching_record.content
            final_tags = new_tags_str if new_tags_str else matching_record.tags
            
            updated_record = RecordEntity(
                id=matching_record.id,
                title=final_title,
                category=final_category,
                date=final_date,
                content=final_content,
                tags=final_tags,
                created_at=matching_record.created_at,
                updated_at=datetime.now(timezone.utc).isoformat()
            )
            
            save_record(file_path, updated_record)
            print_success("Record successfully updated!")
    
    except (RecordNotFoundError, RecordValidationError, StorageError) as err:
        print_error(f"Error: {err}")

def main() -> None:
    """Main execution controller loop"""
    storage_path = DEFAULT_STORAGE_PATH
    
    try:
        ensure_storage_file_exists(storage_path)
    except StorageError as err:
        print_error(f"Fatal initialization error: {err}")
        sys.exit(1)
    
    while True:
        print_header("Personal Records Manager")
        print(" 1. Add New Record")
        print(" 2. Search & Filter Records")
        print(" 3. View All Records")
        print(" 4. View / Manage Record by ID")
        print(" 5. Exit Application")
        print("-" * 60)
        
        choice = input("Select an option (1-5): ").strip()
        
        if choice == "1":
            handle_add_record(storage_path)
        elif choice == "2":
            handle_search_records(storage_path)
        elif choice == "3":
            handle_view_all_records(storage_path)
        elif choice == "4":
            handle_record_detail_action(storage_path)
        elif choice == "5":
            print("\nExiting Personal Records Manager. Goodbye!\n")
            break
        else:
            print_error("Invalid selection. Please choose a number between 1 and 5.")

if __name__ == "__main__":
    main()
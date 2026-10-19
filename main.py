from models import *
from search import *
from storage import *

def handle_record(storage_file_path):
    print("=== Create New Personal Record ===")
    
    while True:
        print("Allowed Categories: Health, Certificate, Note, Finance")
        category = input("Enter category: ").strip().lower()
        title = input("Enter title: ").strip()
        date = input("Enter date (YYYY-MM-DD): ").strip()
        content = input("Enter content / notes: ").strip()
        tags_input = input("Enter tags (comma-separated): ").strip()
        
        try:
            new_record = RecordEntity(title=title,
                category=category,
                date=date,
                content=content,
                tags=tags_input.split(","))
        
            save_record(storage_file_path, new_record)
            print(f"Record successfully created and saved to disk! (ID: {new_record.id})")
        except RecordValidationError as err:
            print(f"Validation Error: {str(err)}")
            print("Please try again.\n")
        except StorageError as err:
            raise StorageError(f"Persistence Error: {str(err)}")

def handle_search(storage_file_path):
    print("=== Search & Filter Records ===")
    
    query_keyword = input("Enter keyword search (press Enter to skip): ").strip()
    query_category = input("Enter category filter (Health/Certificate/Note/Finance, or Enter for all): ").strip()
    
    
    
    
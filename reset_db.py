import os

DB_NAME = 'school_portal.db'
LOGO_PATH = 'static/uploads/logo.jpg'

def reset_school_database():
    print("--- Zaria Hyfam Portal Database Reset Utility ---")
    
    # Confirm action
    confirm = input("Are you sure you want to delete the entire school database and reset uploaded assets? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("Database reset operation cancelled.")
        return

    # Delete SQLite Database file
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
            print(f"[{DB_NAME}] successfully deleted.")
        except Exception as e:
            print(f"Error deleting database file: {e}")
    else:
        print(f"Database file [{DB_NAME}] not found.")

    # Delete uploaded logo if exists
    if os.path.exists(LOGO_PATH):
        try:
            os.remove(LOGO_PATH)
            print(f"[{LOGO_PATH}] successfully removed.")
        except Exception as e:
            print(f"Error removing logo file: {e}")
    else:
        print("No custom school logo file found to remove.")

    print("\nDatabase reset complete! Running your main application script again will automatically recreate fresh tables and default accounts.")

if __name__ == '__main__':
    reset_school_database()
import sqlite3
from pathlib import Path

def fix_camera_device_indexes():
    """
    Connects to the SIAC database and assigns unique, sequential device_index
    values to each camera to prevent conflicts in the orchestrator.
    """
    db_path = Path(__file__).parent / "siac_industrial.db"
    
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        return

    print(f"Connecting to database at {db_path}...")
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Fetch all cameras, ordering by ID to ensure consistent re-indexing
        print("Fetching all cameras from the database...")
        cursor.execute("SELECT id FROM cameras ORDER BY id")
        cameras = cursor.fetchall()

        if not cameras:
            print("No cameras found in the database. Nothing to do.")
            return

        print(f"Found {len(cameras)} cameras. Updating device_index for each...")
        
        # Update each camera with a new, sequential device_index
        for i, camera_row in enumerate(cameras):
            camera_id = camera_row['id']
            new_device_index = i
            print(f"  - Updating camera ID {camera_id} to device_index = {new_device_index}")
            cursor.execute(
                "UPDATE cameras SET device_index = ? WHERE id = ?",
                (new_device_index, camera_id)
            )

        conn.commit()
        print("\nSuccessfully updated all camera device indexes.")

    except sqlite3.Error as e:
        print(f"\nDatabase error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    fix_camera_device_indexes()

"""
Simple test to verify the Calendar and Tasks migration works.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import directly to avoid __init__ dependency issues
import importlib.util

# Load auth module
auth_spec = importlib.util.spec_from_file_location("auth", os.path.join("src", "google_api_client", "auth", "auth.py"))
auth_module = importlib.util.module_from_spec(auth_spec)
auth_spec.loader.exec_module(auth_module)

# Load calendar client
calendar_spec = importlib.util.spec_from_file_location("calendar_client", os.path.join("src", "google_api_client", "clients", "calendar", "client.py"))
calendar_module = importlib.util.module_from_spec(calendar_spec)
sys.modules['google_api_client.clients.calendar.client'] = calendar_module
calendar_spec.loader.exec_module(calendar_module)

# Load tasks client
tasks_spec = importlib.util.spec_from_file_location("tasks_client", os.path.join("src", "google_api_client", "clients", "tasks", "client.py"))
tasks_module = importlib.util.module_from_spec(tasks_spec)
sys.modules['google_api_client.clients.tasks.client'] = tasks_module
tasks_spec.loader.exec_module(tasks_module)

get_credentials_from_file = auth_module.get_credentials_from_file
get_calendar_service = auth_module.get_calendar_service
get_tasks_service = auth_module.get_tasks_service
CalendarEvent = calendar_module.CalendarEvent
Task = tasks_module.Task
TaskList = tasks_module.TaskList

def test_migration():
    """Test the migrated auth approach."""
    print("Testing Calendar and Tasks migration...")
    
    try:
        # Get credentials using new auth approach
        print("1. Getting credentials...")
        credentials = get_credentials_from_file()
        print("✓ Credentials obtained successfully")
        
        # Get services using new approach
        print("2. Creating services...")
        calendar_service = get_calendar_service(credentials)
        tasks_service = get_tasks_service(credentials)
        print("✓ Services created successfully")
        
        # Test Calendar with new approach
        print("3. Testing Calendar API...")
        events = CalendarEvent.list_events(calendar_service, number_of_results=5)
        print(f"✓ Retrieved {len(events)} calendar events")
        
        # Test Tasks with new approach
        print("4. Testing Tasks API...")
        task_lists = TaskList.list_task_lists(tasks_service)
        print(f"✓ Retrieved {len(task_lists)} task lists")
        
        if task_lists:
            # Test getting tasks from first task list
            tasks = Task.list_tasks(tasks_service, task_lists[0].id, max_results=5)
            print(f"✓ Retrieved {len(tasks)} tasks from first task list")
        
        print("🎉 Migration test completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        raise

if __name__ == "__main__":
    test_migration()
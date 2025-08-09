#!/usr/bin/env python3
"""
Complete multi-user example demonstrating dependency injection across all Google API clients.
"""

from src.google_api_client.auth.manager import AuthManager
from src.google_api_client.clients.gmail.client import EmailMessage
from src.google_api_client.clients.calendar.client import CalendarEvent
from src.google_api_client.clients.tasks.client import TaskList, Task
from datetime import datetime, timedelta

def main():
    """Demonstrate multi-user authentication across all services."""
    
    print("=== Complete Multi-User Google API Example ===\n")
    
    # Create separate auth managers for different users
    user1_auth = AuthManager(
        token_path="tokens/user1_token.json",
        credentials_path="shared_credentials.json"
    )
    
    user2_auth = AuthManager(
        token_path="tokens/user2_token.json", 
        credentials_path="shared_credentials.json"
    )
    
    # === GMAIL EXAMPLES ===
    print("=== Gmail Multi-User Examples ===")
    
    try:
        # User 1 Gmail operations
        user1_emails = EmailMessage.list_emails(
            auth_manager_instance=user1_auth,
            max_results=5
        )
        print(f"User 1 has {len(user1_emails)} emails")
        
        # User 2 Gmail operations  
        user2_emails = EmailMessage.list_emails(
            auth_manager_instance=user2_auth,
            max_results=5
        )
        print(f"User 2 has {len(user2_emails)} emails")
        
        # Instance methods automatically use correct auth
        if user1_emails:
            first_email = user1_emails[0]
            # first_email.mark_as_read()  # Uses user1_auth automatically
            # first_email.delete_email()  # Uses user1_auth automatically
            
        if user2_emails:
            first_email = user2_emails[0] 
            # first_email.mark_as_read()  # Uses user2_auth automatically
            
    except Exception as e:
        print(f"Gmail error: {e}")
    
    # === CALENDAR EXAMPLES ===
    print("\n=== Calendar Multi-User Examples ===")
    
    try:
        # User 1 Calendar operations
        user1_events = CalendarEvent.list_events(
            auth_manager_instance=user1_auth,
            number_of_results=5
        )
        print(f"User 1 has {len(user1_events)} events")
        
        # User 2 Calendar operations
        user2_events = CalendarEvent.list_events(
            auth_manager_instance=user2_auth,
            number_of_results=5
        )
        print(f"User 2 has {len(user2_events)} events")
        
        # Create events for different users
        tomorrow = datetime.now() + timedelta(days=1)
        end_time = tomorrow + timedelta(hours=1)
        
        user1_event = CalendarEvent.create_event(
            auth_manager_instance=user1_auth,
            start=tomorrow,
            end=end_time,
            summary="User 1 Meeting",
            description="Meeting for user 1"
        )
        print(f"Created event for User 1: {user1_event.summary}")
        
        user2_event = CalendarEvent.create_event(
            auth_manager_instance=user2_auth,
            start=tomorrow,
            end=end_time,
            summary="User 2 Meeting", 
            description="Meeting for user 2"
        )
        print(f"Created event for User 2: {user2_event.summary}")
        
        # Instance methods use correct auth
        # user1_event.delete_event()  # Uses user1_auth
        # user2_event.delete_event()  # Uses user2_auth
        
    except Exception as e:
        print(f"Calendar error: {e}")
    
    # === TASKS EXAMPLES ===
    print("\n=== Tasks Multi-User Examples ===")
    
    try:
        # User 1 Tasks operations
        user1_task_lists = TaskList.list_task_lists(
            auth_manager_instance=user1_auth
        )
        print(f"User 1 has {len(user1_task_lists)} task lists")
        
        # User 2 Tasks operations
        user2_task_lists = TaskList.list_task_lists(
            auth_manager_instance=user2_auth
        )
        print(f"User 2 has {len(user2_task_lists)} task lists")
        
        # Create tasks for different users
        if user1_task_lists:
            user1_task = Task.create_task(
                auth_manager_instance=user1_auth,
                title="User 1 Task",
                notes="Task for user 1"
            )
            print(f"Created task for User 1: {user1_task.title}")
        
        if user2_task_lists:
            user2_task = Task.create_task(
                auth_manager_instance=user2_auth,
                title="User 2 Task",
                notes="Task for user 2"
            )
            print(f"Created task for User 2: {user2_task.title}")
            
        # Instance methods use correct auth
        # user1_task.complete_task()  # Uses user1_auth
        # user2_task.delete_task()    # Uses user2_auth
        
    except Exception as e:
        print(f"Tasks error: {e}")
    
    print("\n=== Example Complete ===")
    print("Key Features:")
    print("✅ No global auth_manager - pure dependency injection")
    print("✅ auth_manager_instance is REQUIRED for all class methods")
    print("✅ Thread-safe - each user has isolated authentication")
    print("✅ Instance methods automatically use correct auth")
    print("✅ Works across Gmail, Calendar, and Tasks APIs")
    print("✅ No backward compatibility - forces explicit auth management")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Example demonstrating multi-user authentication with dependency injection.
"""

from src.google_api_client.auth.manager import AuthManager
from src.google_api_client.clients.gmail.client import EmailMessage

def main():
    """Demonstrate multi-user authentication."""
    
    # Create separate auth managers for different users
    user1_auth = AuthManager(
        token_path="tokens/user1_token.json",
        credentials_path="shared_credentials.json"
    )
    
    user2_auth = AuthManager(
        token_path="tokens/user2_token.json", 
        credentials_path="shared_credentials.json"
    )
    
    print("=== Multi-User Gmail API Example ===\n")
    
    # Method 1: Pass auth_manager to class methods (auth_manager is now first parameter)
    print("1. Using auth_manager parameter in class methods:")
    try:
        user1_emails = EmailMessage.list_emails(
            auth_manager_instance=user1_auth,
            max_results=5
        )
        print(f"User 1 has {len(user1_emails)} emails")
        
        user2_emails = EmailMessage.list_emails(
            auth_manager_instance=user2_auth,
            max_results=5
        )
        print(f"User 2 has {len(user2_emails)} emails")
        
    except Exception as e:
        print(f"Error fetching emails: {e}")
    
    # Method 2: Instance methods automatically use the correct auth
    print("\n2. Instance methods use the correct user's auth:")
    try:
        if user1_emails:
            first_email = user1_emails[0]
            print(f"User 1's first email subject: {first_email.subject}")
            
            # All instance methods (delete_email, mark_as_read, etc.) 
            # will automatically use user1_auth
            # first_email.mark_as_read()  # Uses user1_auth
            # first_email.delete_email()  # Uses user1_auth
            
        if user2_emails:
            first_email = user2_emails[0]
            print(f"User 2's first email subject: {first_email.subject}")
            
            # These methods will automatically use user2_auth
            # first_email.mark_as_read()  # Uses user2_auth
            # first_email.delete_email()  # Uses user2_auth
            
    except Exception as e:
        print(f"Error with instance methods: {e}")
        
    # Method 3: Get specific email for each user
    print("\n3. Getting specific emails for each user:")
    try:
        # Each call uses the appropriate user's authentication
        user1_specific = EmailMessage.get_email(
            message_id="some_message_id", 
            auth_manager_instance=user1_auth
        )
        
        user2_specific = EmailMessage.get_email(
            message_id="some_other_message_id",
            auth_manager_instance=user2_auth
        )
        
        print("Successfully retrieved emails for both users with different auth")
        
    except Exception as e:
        print(f"Error getting specific emails: {e}")
    
    print("\n=== Example complete ===")
    print("Key benefits:")
    print("- Each user has separate authentication")
    print("- No shared state between users") 
    print("- Thread-safe for concurrent users")
    print("- Instance methods automatically use correct auth")
    print("- No global auth_manager - explicit dependency injection")
    print("- auth_manager_instance is REQUIRED for all class methods")

if __name__ == "__main__":
    main()
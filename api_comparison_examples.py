"""
API Design Comparison Examples

This demonstrates three different approaches to multi-user Google API access:
1. Current approach (service parameters)
2. User-centric approach (recommended)
3. Hybrid approach
"""

from datetime import datetime, timedelta

# =============================================================================
# APPROACH 1: Current Service Parameter Approach
# =============================================================================

def current_approach_example():
    """Current approach - explicit service parameters."""
    print("=== Current Approach (Service Parameters) ===")
    
    # Each user needs explicit service management
    from google_api_client.auth.auth import get_credentials_from_file, get_calendar_service, get_gmail_service
    
    # User 1
    user1_creds = get_credentials_from_file("user1_credentials.json", "user1_token.json")
    user1_calendar_service = get_calendar_service(user1_creds)
    user1_gmail_service = get_gmail_service(user1_creds)
    
    # User 2  
    user2_creds = get_credentials_from_file("user2_credentials.json", "user2_token.json")
    user2_calendar_service = get_calendar_service(user2_creds)
    user2_gmail_service = get_gmail_service(user2_creds)
    
    # Usage - verbose and error-prone
    from google_api_client.clients.calendar.client import CalendarEvent
    from google_api_client.clients.gmail.client import EmailMessage
    
    # User 1 operations
    user1_events = CalendarEvent.list_events(user1_calendar_service, number_of_results=10)
    user1_emails = EmailMessage.list_emails(user1_gmail_service, max_results=20)
    
    # User 2 operations  
    user2_events = CalendarEvent.list_events(user2_calendar_service, number_of_results=10)
    user2_emails = EmailMessage.list_emails(user2_gmail_service, max_results=20)
    
    print("✓ Works but verbose and repetitive")
    print("✗ Easy to mix up services between users")
    print("✗ No clear user context")
    

# =============================================================================
# APPROACH 2: User-Centric Approach (RECOMMENDED)
# =============================================================================

def user_centric_approach_example():
    """User-centric approach - clean and intuitive."""
    print("\n=== User-Centric Approach (RECOMMENDED) ===")
    
    from google_api_client.user_client import UserClient
    
    # Single user scenario
    user = UserClient.from_file()
    events = user.calendar.list_events(number_of_results=10)
    emails = user.gmail.list_emails(max_results=20)
    tasks = user.tasks.list_tasks()
    
    # Multi-user scenario
    app_credentials = {"installed": {"client_id": "...", "client_secret": "..."}}
    user1_token = {"access_token": "...", "refresh_token": "..."}
    user2_token = {"access_token": "...", "refresh_token": "..."}
    
    user_1 = UserClient.from_credentials_info(app_credentials, user1_token)
    user_2 = UserClient.from_credentials_info(app_credentials, user2_token)
    
    # Clean, intuitive usage
    user1_events = user_1.calendar.list_events(number_of_results=10)
    user1_emails = user_1.gmail.list_emails(max_results=20)
    
    user2_events = user_2.calendar.list_events(number_of_results=10) 
    user2_emails = user_2.gmail.list_emails(max_results=20)
    
    # Query builders work naturally
    user1_recent_emails = (user_1.gmail.query()
                          .limit(50)
                          .from_sender("boss@company.com")
                          .execute())
    
    user2_meetings = (user_2.calendar.query()
                     .in_date_range(datetime.now(), datetime.now() + timedelta(days=7))
                     .search("meeting")
                     .execute())
    
    print("✓ Clean, intuitive API")
    print("✓ Clear user context")
    print("✓ No service mix-ups possible")
    print("✓ Works great for both single and multi-user")


# =============================================================================
# APPROACH 3: Hybrid Approach
# =============================================================================

def hybrid_approach_example():
    """Hybrid approach - user clients + direct service access when needed."""
    print("\n=== Hybrid Approach ===")
    
    from google_api_client.user_client import UserClient
    
    # User-centric for common operations
    user = UserClient.from_file()
    events = user.calendar.list_events()
    
    # Direct service access for advanced operations
    calendar_service = user.get_calendar_service()
    # Custom operations that aren't wrapped
    raw_response = calendar_service.events().list(calendarId="primary").execute()
    
    print("✓ Best of both worlds")
    print("✓ Clean API for common operations")
    print("✓ Direct access for advanced scenarios")


# =============================================================================
# REAL-WORLD USAGE SCENARIOS
# =============================================================================

def multi_user_dashboard_example():
    """Example: Multi-user dashboard application."""
    print("\n=== Multi-User Dashboard Example ===")
    
    from google_api_client.user_client import UserClient
    
    # Application manages multiple users
    app_credentials = load_app_credentials()
    
    users = {}
    for user_id in ["alice", "bob", "charlie"]:
        token_data = load_user_token(user_id)  # From database
        users[user_id] = UserClient.from_credentials_info(app_credentials, token_data)
    
    # Generate dashboard data for each user
    dashboard_data = {}
    for user_id, user_client in users.items():
        dashboard_data[user_id] = {
            "upcoming_events": user_client.calendar.list_events(number_of_results=5),
            "recent_emails": user_client.gmail.list_emails(max_results=10),
            "pending_tasks": user_client.tasks.list_tasks(max_results=5)
        }
    
    print("✓ Each user has isolated, clean API access")
    print("✓ No risk of data leakage between users")


def enterprise_integration_example():
    """Example: Enterprise application with service accounts."""
    print("\n=== Enterprise Integration Example ===")
    
    # Domain admin can create UserClient instances for any domain user
    from google_api_client.user_client import UserClient
    
    def get_user_client(email: str) -> UserClient:
        """Get UserClient for domain user via service account."""
        # Service account credentials with domain-wide delegation
        service_account_creds = get_service_account_credentials()
        delegated_creds = service_account_creds.with_subject(email)
        return UserClient(delegated_creds)
    
    # Access any domain user's data
    ceo = get_user_client("ceo@company.com")
    marketing = get_user_client("marketing@company.com")
    
    ceo_meetings = ceo.calendar.list_events()
    marketing_campaigns = marketing.gmail.list_emails(query="campaign")
    
    print("✓ Clean API even with service account delegation")


# Helper functions (mockups)
def load_app_credentials():
    return {"installed": {"client_id": "mock", "client_secret": "mock"}}

def load_user_token(user_id):
    return {"access_token": f"mock_token_{user_id}", "refresh_token": f"mock_refresh_{user_id}"}

def get_service_account_credentials():
    pass  # Mock implementation


if __name__ == "__main__":
    print("Google API Client - Design Approach Comparison\n")
    
    # Show all approaches
    current_approach_example()
    user_centric_approach_example() 
    hybrid_approach_example()
    
    # Real-world scenarios
    multi_user_dashboard_example()
    enterprise_integration_example()
    
    print("\n" + "="*60)
    print("RECOMMENDATION: Use the User-Centric Approach")
    print("="*60)
    print("✓ Most intuitive and clean")
    print("✓ Prevents user data mix-ups") 
    print("✓ Scales well from single to multi-user")
    print("✓ Maintains all current functionality")
    print("✓ Easy to understand and maintain")
"""
Simple test to verify the migration signatures are correct.
"""

import inspect
import sys
import os

def test_function_signatures():
    """Test that the migrated functions have the correct signatures."""
    print("Testing function signatures...")
    
    # Test auth module
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    # Import and check auth functions
    from google_api_client.auth import auth
    
    # Check that service functions exist
    assert hasattr(auth, 'get_gmail_service'), "get_gmail_service function missing"
    assert hasattr(auth, 'get_calendar_service'), "get_calendar_service function missing"
    assert hasattr(auth, 'get_tasks_service'), "get_tasks_service function missing"
    
    # Check function signatures
    gmail_sig = inspect.signature(auth.get_gmail_service)
    calendar_sig = inspect.signature(auth.get_calendar_service)
    tasks_sig = inspect.signature(auth.get_tasks_service)
    
    assert 'credentials' in gmail_sig.parameters, "get_gmail_service missing credentials parameter"
    assert 'credentials' in calendar_sig.parameters, "get_calendar_service missing credentials parameter"
    assert 'credentials' in tasks_sig.parameters, "get_tasks_service missing credentials parameter"
    
    print("Auth module signatures are correct")
    
    # Test that we can import the clients without errors in a separate process
    import subprocess
    
    # Test calendar client import
    result = subprocess.run([
        sys.executable, '-c', 
        'import sys; sys.path.insert(0, "src"); exec(open("src/google_api_client/clients/calendar/client.py").read())'
    ], cwd=os.path.dirname(__file__), capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Calendar client import failed: {result.stderr}")
        return False
    
    print("Calendar client can be loaded")
    
    # Test tasks client import
    result = subprocess.run([
        sys.executable, '-c', 
        'import sys; sys.path.insert(0, "src"); exec(open("src/google_api_client/clients/tasks/client.py").read())'
    ], cwd=os.path.dirname(__file__), capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Tasks client import failed: {result.stderr}")
        return False
    
    print("Tasks client can be loaded")
    
    print("Migration signature test passed!")
    return True

if __name__ == "__main__":
    test_function_signatures()
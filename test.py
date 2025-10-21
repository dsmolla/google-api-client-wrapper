from google_client.api_service import APIServiceLayer
import json
import asyncio


with open(r"C:\Users\dagms\Projects\Credentials\token-1.json", 'r') as f:
    user_info = json.load(f)
#%%
import asyncio
api_service = APIServiceLayer(user_info)
email_ids = asyncio.run(api_service.gmail.list_emails(max_results=10))
emails = asyncio.run(api_service.gmail.batch_get_emails(email_ids))
print(emails)

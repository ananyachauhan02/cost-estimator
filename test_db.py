import sys
import logging
from database import delete_client, get_all_clients, SessionLocal, Client, Estimate

logging.basicConfig(level=logging.DEBUG)

print("Before:")
clients = get_all_clients()
print([c['name'] for c in clients])

if clients:
    cid = clients[-1]['id']
    cname = clients[-1]['name']
    print(f"\nAttempting to delete {cname} (ID: {cid})")
    try:
        success = delete_client(cid)
        print(f"Delete returned: {success}")
    except Exception as e:
        print(f"Error: {e}")

print("\nAfter:")
clients = get_all_clients()
print([c['name'] for c in clients])

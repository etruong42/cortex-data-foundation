import os

CURRENT_FILE = os.path.abspath("backend/chat_service.py")
BACKEND_DIR = os.path.dirname(CURRENT_FILE)
ROOT_DIR = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

print(f"Current File (simulated): {CURRENT_FILE}")
print(f"Backend Dir: {BACKEND_DIR}")
print(f"Root Dir: {ROOT_DIR}")
print(f"Frontend Dir: {FRONTEND_DIR}")
print(f"Frontend Dir Exists: {os.path.exists(FRONTEND_DIR)}")
print(f"Index HTML Exists: {os.path.exists(os.path.join(FRONTEND_DIR, 'index.html'))}")

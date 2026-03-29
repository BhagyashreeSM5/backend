print("Starting test...")

try:
    from rag.rag_engine import embed_codebase, chat_with_code
    print("Import successful!")
except Exception as e:
    print(f"Import error: {e}")
    exit()

test_files = [
    {
        "path": "auth.py",
        "content": """
def authenticate(username, password):
    if username == "admin" and password == "secret":
        return generate_token(username)
    return None

def generate_token(username):
    import hashlib
    return hashlib.md5(username.encode()).hexdigest()
"""
    }
]

try:
    print("Embedding codebase...")
    count = embed_codebase("test123", test_files)
    print(f"Stored {count} chunks!")
except Exception as e:
    print(f"Embed error: {e}")
    exit()

try:
    print("Asking question...")
    answer = chat_with_code("test123", "How does authentication work?")
    print("Answer:", answer)
except Exception as e:
    print(f"Chat error: {e}")
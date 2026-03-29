# import chromadb
# import google.generativeai as genai
# import os
# from dotenv import load_dotenv

# load_dotenv()

# # 🧠 WHY: Configure Gemini with our API key from .env file
# # Never hardcode API keys — always use environment variables!
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# # 🧠 WHY: ChromaDB client stores vectors locally in a folder called "chroma_db"
# # This folder is created automatically — no setup needed!
# chroma_client = chromadb.PersistentClient(path="./chroma_db")


# def get_or_create_collection(codebase_id: str):
#     """
#     🧠 WHY: Each uploaded codebase gets its OWN collection in ChromaDB.
#     Think of it like a separate folder per project.
#     codebase_id = unique ID for this upload
#     """
#     return chroma_client.get_or_create_collection(
#         name=f"codebase_{codebase_id}",
#         metadata={"hnsw:space": "cosine"}
#         # 🧠 cosine = measure similarity by angle, not distance
#         # Best for text/code embeddings
#     )


# def embed_codebase(codebase_id: str, files: list):
#     """
#     🧠 HOW IT WORKS:
#     1. For each file → split into chunks (one chunk per function)
#     2. Store each chunk in ChromaDB with its metadata
#     3. ChromaDB automatically creates embeddings using its built-in model

#     files = list of {"path": "...", "content": "..."}
#     """
#     collection = get_or_create_collection(codebase_id)

#     documents = []  # the actual code text
#     metadatas = []  # extra info about each chunk
#     ids = []        # unique ID for each chunk

#     for file in files:
#         content = file["content"]
#         file_path = file["path"]

#         # 🧠 WHY split into chunks?
#         # If we store the whole file as one vector, searches are less accurate.
#         # Smaller chunks = more precise retrieval
#         # We split by lines of 50 — simple but effective
#         lines = content.split("\n")
#         chunk_size = 50

#         for i in range(0, len(lines), chunk_size):
#             chunk = "\n".join(lines[i:i + chunk_size])
#             if chunk.strip():  # skip empty chunks
#                 chunk_id = f"{codebase_id}_{file_path}_{i}"
#                 documents.append(chunk)
#                 metadatas.append({
#                     "file": file_path,
#                     "start_line": str(i),
#                     "end_line": str(min(i + chunk_size, len(lines)))
#                 })
#                 ids.append(chunk_id)

#     # 🧠 WHY upsert instead of add?
#     # upsert = update if exists, insert if not
#     # This way re-uploading same codebase doesn't cause duplicates
#     if documents:
#         collection.upsert(
#             documents=documents,
#             metadatas=metadatas,
#             ids=ids
#         )

#     return len(documents)


# def search_codebase(codebase_id: str, query: str, n_results: int = 5) -> list:
#     """
#     🧠 HOW IT WORKS:
#     1. Convert query to vector
#     2. Find n_results most similar vectors in ChromaDB
#     3. Return the matching code chunks

#     This is the RETRIEVAL part of RAG
#     """
#     collection = get_or_create_collection(codebase_id)

#     results = collection.query(
#         query_texts=[query],  # ChromaDB converts this to vector automatically
#         n_results=min(n_results, collection.count() or 1)
#     )

#     # Format results nicely
#     chunks = []
#     if results["documents"]:
#         for i, doc in enumerate(results["documents"][0]):
#             chunks.append({
#                 "content": doc,
#                 "file": results["metadatas"][0][i]["file"],
#                 "start_line": results["metadatas"][0][i]["start_line"]
#             })

#     return chunks


# def chat_with_code(codebase_id: str, question: str, chat_history: list = []) -> str:
#     """
#     🧠 HOW IT WORKS:
#     1. Search ChromaDB for relevant code chunks (Retrieval)
#     2. Build a prompt with: question + relevant code (Augmentation)
#     3. Send to Gemini and get answer (Generation)
#     This is the full RAG pipeline!

#     chat_history = list of {"role": "user/assistant", "content": "..."}
#     """
#     # Step 1: RETRIEVE relevant code chunks
#     relevant_chunks = search_codebase(codebase_id, question)

#     if not relevant_chunks:
#         return "No relevant code found for your question. Please upload a codebase first."

#     # Step 2: AUGMENT the prompt with retrieved context
#     context = "\n\n".join([
#         f"File: {chunk['file']} (line {chunk['start_line']})\n{chunk['content']}"
#         for chunk in relevant_chunks
#     ])

#     # 🧠 WHY this prompt structure?
#     # We tell Gemini exactly what role it plays and give it the code context
#     # This is called "prompt engineering" — how you frame the question matters!
#     prompt = f"""You are an expert code assistant helping a developer understand a codebase.

# Here are the most relevant code sections for the question:

# {context}

# Based on the code above, please answer this question:
# {question}

# Be specific and reference the actual code when explaining.
# If the answer is not in the provided code, say so clearly."""

#     # Step 3: GENERATE answer using Gemini
#     model = genai.GenerativeModel("gemini-2.5-flash")

#     # 🧠 WHY include chat history?
#     # So Gemini remembers previous questions in the conversation
#     # "What does authenticate() do?" → "How is it called?" 
#     # Without history, Gemini wouldn't know what "it" refers to!
#     history = []
#     for msg in chat_history[-6:]:  # last 6 messages only (token limit)
#         history.append({
#             "role": msg["role"],
#             "parts": [msg["content"]]
#         })

#     if history:
#         chat = model.start_chat(history=history)
#         response = chat.send_message(prompt)
#     else:
#         response = model.generate_content(prompt)

#     return response.text


# def delete_codebase(codebase_id: str):
#     """
#     🧠 WHY: When user deletes a codebase, clean up ChromaDB too.
#     Otherwise storage grows forever!
#     """
#     try:
#         chroma_client.delete_collection(f"codebase_{codebase_id}")
#         return True
#     except Exception:
#         return False






# import chromadb
# import google.generativeai as genai
# import os
# from dotenv import load_dotenv

# # ✅ FIX 1: Correct .env loading (important)
# load_dotenv(dotenv_path="backend/.env")

# api_key = os.getenv("GEMINI_API_KEY")

# if not api_key:
#     raise ValueError("❌ GEMINI_API_KEY not found. Check your .env file")

# genai.configure(api_key=api_key)

# # ✅ ChromaDB setup
# chroma_client = chromadb.PersistentClient(path="./chroma_db")


# def get_or_create_collection(codebase_id: str):
#     return chroma_client.get_or_create_collection(
#         name=f"codebase_{codebase_id}",
#         metadata={"hnsw:space": "cosine"}
#     )


# def embed_codebase(codebase_id: str, files: list):
#     collection = get_or_create_collection(codebase_id)

#     documents, metadatas, ids = [], [], []

#     for file in files:
#         content = file["content"]
#         file_path = file["path"]

#         lines = content.split("\n")
#         chunk_size = 50

#         for i in range(0, len(lines), chunk_size):
#             chunk = "\n".join(lines[i:i + chunk_size])
#             if chunk.strip():
#                 chunk_id = f"{codebase_id}_{file_path}_{i}"

#                 documents.append(chunk)
#                 metadatas.append({
#                     "file": file_path,
#                     "start_line": str(i),
#                     "end_line": str(min(i + chunk_size, len(lines)))
#                 })
#                 ids.append(chunk_id)

#     if documents:
#         collection.upsert(
#             documents=documents,
#             metadatas=metadatas,
#             ids=ids
#         )

#     return len(documents)


# def search_codebase(codebase_id: str, query: str, n_results: int = 5):
#     collection = get_or_create_collection(codebase_id)

#     results = collection.query(
#         query_texts=[query],
#         n_results=min(n_results, collection.count() or 1)
#     )

#     chunks = []
#     if results.get("documents"):
#         for i, doc in enumerate(results["documents"][0]):
#             chunks.append({
#                 "content": doc,
#                 "file": results["metadatas"][0][i]["file"],
#                 "start_line": results["metadatas"][0][i]["start_line"]
#             })

#     return chunks


# def chat_with_code(codebase_id: str, question: str, chat_history: list = []):
#     try:
#         # 🔍 Step 1: Retrieve
#         relevant_chunks = search_codebase(codebase_id, question)

#         if not relevant_chunks:
#             return "No relevant code found."

#         # 🧠 Step 2: Build context
#         context = "\n\n".join([
#             f"File: {chunk['file']} (line {chunk['start_line']})\n{chunk['content']}"
#             for chunk in relevant_chunks
#         ])

#         prompt = f"""
# You are an expert code assistant.

# Code:
# {context}

# Question:
# {question}

# Answer clearly based only on the code.
# """

#         # ✅ FIX 2: Safe model (works always)
#         model = genai.GenerativeModel("gemini-2.0-flash")

#         # 🧠 Chat history
#         history = []
#         for msg in chat_history[-6:]:
#             history.append({
#                 "role": msg["role"],
#                 "parts": [msg["content"]]
#             })

#         # 🤖 Step 3: Generate
#         if history:
#             chat = model.start_chat(history=history)
#             response = chat.send_message(prompt)
#         else:
#             response = model.generate_content(prompt)

#         # ✅ FIX 3: Safe response
#         return response.text if hasattr(response, "text") else "No response from AI"

#     except Exception as e:
#         print("❌ Gemini Error:", str(e))
#         return f"Error: {str(e)}"


# def delete_codebase(codebase_id: str):
#     try:
#         chroma_client.delete_collection(f"codebase_{codebase_id}")
#         return True
#     except Exception as e:
#         print("Delete Error:", str(e))
#         return False



import chromadb
import requests
import os
from dotenv import load_dotenv

# ✅ Load .env
load_dotenv()  # Loads .env from cwd (works locally and on Render)

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("❌ OPENROUTER_API_KEY not found. Check your .env file")

# ✅ ChromaDB setup
chroma_client = chromadb.PersistentClient(path="./chroma_db")


def get_or_create_collection(codebase_id: str):
    return chroma_client.get_or_create_collection(
        name=f"codebase_{codebase_id}",
        metadata={"hnsw:space": "cosine"}
    )


def embed_codebase(codebase_id: str, files: list):
    collection = get_or_create_collection(codebase_id)

    documents, metadatas, ids = [], [], []

    for file in files:
        content = file["content"]
        file_path = file["path"]

        lines = content.split("\n")
        chunk_size = 50

        for i in range(0, len(lines), chunk_size):
            chunk = "\n".join(lines[i:i + chunk_size])
            if chunk.strip():
                chunk_id = f"{codebase_id}_{file_path}_{i}"

                documents.append(chunk)
                metadatas.append({
                    "file": file_path,
                    "start_line": str(i),
                    "end_line": str(min(i + chunk_size, len(lines)))
                })
                ids.append(chunk_id)

    if documents:
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    return len(documents)


def search_codebase(codebase_id: str, query: str, n_results: int = 3):
    collection = get_or_create_collection(codebase_id)

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count() or 1)
    )

    chunks = []
    if results.get("documents"):
        for i, doc in enumerate(results["documents"][0]):
            chunks.append({
                "content": doc,
                "file": results["metadatas"][0][i]["file"],
                "start_line": results["metadatas"][0][i]["start_line"]
            })

    return chunks


# ✅ NEW: OpenRouter AI call
def generate_ai_response(prompt):
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        )

        if response.status_code != 200:
            print("❌ API Error:", response.text)
            return "AI service error"

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print("❌ Request Error:", str(e))
        return "AI service unavailable"


def chat_with_code(codebase_id: str, question: str, chat_history: list = []):
    try:
        # 🔍 Step 1: Retrieve
        relevant_chunks = search_codebase(codebase_id, question)

        if not relevant_chunks:
            return "No relevant code found."

        # 🧠 Step 2: Context
        context = "\n\n".join([
            f"File: {chunk['file']} (line {chunk['start_line']})\n{chunk['content']}"
            for chunk in relevant_chunks
        ])

        # limit size (important)
        context = context[:1200]

        prompt = f"""
You are an expert code assistant.

Code:
{context}

Question:
{question}

Answer clearly based only on the code.
"""

        # 🤖 Step 3: Generate
        answer = generate_ai_response(prompt)

        return answer

    except Exception as e:
        print("❌ Chat Error:", str(e))
        return "Error processing request"


def delete_codebase(codebase_id: str):
    try:
        chroma_client.delete_collection(f"codebase_{codebase_id}")
        return True
    except Exception as e:
        print("Delete Error:", str(e))
        return False
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

from code_parsers.code_parser import parse_multiple_files
from rag.rag_engine import embed_codebase, chat_with_code, delete_codebase

app = FastAPI(title="CodeLens AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for production frontend to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Firebase Admin init
# It first tries to read FIREBASE_CREDENTIALS to securely deploy without committing JSON string
firebase_creds = os.getenv("FIREBASE_CREDENTIALS")
if firebase_creds:
    import json
    cred_dict = json.loads(firebase_creds)
    cred = credentials.Certificate(cred_dict)
else:
    # Local fallback
    cred = credentials.Certificate("serviceAccount.json")

firebase_admin.initialize_app(cred)
db = firestore.client()

# In-memory cache
codebases = {}

class ChatRequest(BaseModel):
    codebase_id: str
    question: str
    chat_history: Optional[List[dict]] = []

@app.get("/")
def root():
    return {"message": "CodeLens AI is running!", "status": "ok"}

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    codebase_id = str(uuid.uuid4())[:8]
    file_list = []
    supported_extensions = {".py", ".js", ".jsx", ".java"}

    for file in files:
        _, ext = os.path.splitext(file.filename.lower())
        if ext not in supported_extensions:
            continue
        content = await file.read()
        try:
            text = content.decode("utf-8", errors="ignore")
            file_list.append({"path": file.filename, "content": text})
        except Exception:
            continue

    if not file_list:
        raise HTTPException(status_code=400, detail="No supported files found.")

    graph_data = parse_multiple_files(file_list)

    try:
        chunks_stored = embed_codebase(codebase_id, file_list)
    except Exception as e:
        chunks_stored = 0
        print(f"RAG embedding error: {e}")

    languages = list(set([
        info["language"] for info in graph_data["file_map"].values()
    ]))

    # Save to Firestore for shareable links
    try:
        db.collection("codebases").document(codebase_id).set({
            "codebase_id": codebase_id,
            "files": [f["path"] for f in file_list],
            "nodes": graph_data["nodes"],
            "edges": graph_data["edges"],
            "file_map": graph_data["file_map"],
            "languages": languages,
            "chunks_stored": chunks_stored,
            "created_at": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Firestore error: {e}")

    codebases[codebase_id] = {
        "files": [f["path"] for f in file_list],
        "graph": graph_data,
        "chunks": chunks_stored
    }

    return {
        "codebase_id": codebase_id,
        "files_processed": len(file_list),
        "chunks_stored": chunks_stored,
        "nodes": graph_data["nodes"],
        "edges": graph_data["edges"],
        "file_map": graph_data["file_map"],
        "languages": languages,
        "message": f"Successfully analyzed {len(file_list)} files!"
    }

@app.get("/graph/{codebase_id}")
def get_graph(codebase_id: str):
    # First check memory cache
    if codebase_id in codebases:
        graph = codebases[codebase_id]["graph"]
        languages = list(set([
            info["language"] for info in graph["file_map"].values()
        ]))
        return {
            "nodes": graph["nodes"],
            "edges": graph["edges"],
            "file_map": graph["file_map"],
            "languages": languages,
            "codebase_id": codebase_id
        }

    # Fallback to Firestore
    try:
        doc = db.collection("codebases").document(codebase_id).get()
        if doc.exists:
            data = doc.to_dict()
            return {
                "nodes": data["nodes"],
                "edges": data["edges"],
                "file_map": data["file_map"],
                "languages": data["languages"],
                "codebase_id": codebase_id
            }
    except Exception as e:
        print(f"Firestore fetch error: {e}")

    raise HTTPException(status_code=404, detail="Codebase not found")

@app.post("/chat")
async def chat(request: ChatRequest):
    # Load from Firestore if not in memory
    if request.codebase_id not in codebases:
        try:
            doc = db.collection("codebases").document(request.codebase_id).get()
            if doc.exists:
                data = doc.to_dict()
                codebases[request.codebase_id] = {
                    "files": data["files"],
                    "graph": {
                        "nodes": data["nodes"],
                        "edges": data["edges"],
                        "file_map": data["file_map"]
                    },
                    "chunks": data["chunks_stored"]
                }
        except Exception as e:
            raise HTTPException(status_code=404, detail="Codebase not found")

    try:
        answer = chat_with_code(
            codebase_id=request.codebase_id,
            question=request.question,
            chat_history=request.chat_history
        )
        return {"answer": answer, "codebase_id": request.codebase_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/share/{codebase_id}")
def get_shared_codebase(codebase_id: str):
    """Public endpoint for shareable links"""
    try:
        doc = db.collection("codebases").document(codebase_id).get()
        if doc.exists:
            data = doc.to_dict()
            return {
                "nodes": data["nodes"],
                "edges": data["edges"],
                "file_map": data["file_map"],
                "languages": data["languages"],
                "codebase_id": codebase_id,
                "files": data["files"]
            }
    except Exception as e:
        print(f"Share fetch error: {e}")
    raise HTTPException(status_code=404, detail="Shared codebase not found")
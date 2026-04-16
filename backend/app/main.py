from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Cultural Artifact KG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Cultural Artifact Knowledge Graph API is running"
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/api/mock/context")
def mock_context():
    return {
        "artifact": "襄",
        "pages": [12, 13],
        "mode": "single",
        "candidates": 5
    }

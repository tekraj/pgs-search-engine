# main.py (or wherever your FastAPI app is defined)
from fastapi import FastAPI
from user_search.router import router as user_search_router

app = FastAPI(title="User Search API")

# Include the user search router
app.include_router(user_search_router)

# Optional: Add startup/shutdown events for the gRPC client
from user_search.grpc_client import get_grpc_client, _grpc_client

@app.on_event("startup")
async def startup_event():
    get_grpc_client()  # Initialize connection

@app.on_event("shutdown")
async def shutdown_event():
    if _grpc_client:
        _grpc_client.close()
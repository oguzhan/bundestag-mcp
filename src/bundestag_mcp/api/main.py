"""FastAPI application for Bundestag data API."""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .routes import votes, parties, mps, documents, chat

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="Bundestag MCP API",
    description="API providing access to German Bundestag parliamentary data and voting records",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(votes.router, prefix="/api/v1", tags=["Votes"])
app.include_router(parties.router, prefix="/api/v1", tags=["Parties"])
app.include_router(mps.router, prefix="/api/v1", tags=["Members of Parliament"])
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Bundestag MCP API",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


def main():
    """Run the API server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        "bundestag_mcp.api.main:app",
        host=host,
        port=port,
        reload=os.getenv("ENV", "development") == "development",
    )


if __name__ == "__main__":
    main()

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
import uvicorn

# ---- Global Logging Config ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

# App Imports
from routes.authentication_route import router as auth_router
from routes.chat_route import router as chat_router
from routes.query_router import router as query_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

# FastAPI App Initialization
app = FastAPI(
    title="Fitness & Dance Instructor AI",
    description="Your virtual instructor for fitness and dance routines.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monitoring (Prometheus)
Instrumentator().instrument(app).expose(app)

# Routers
app.include_router(auth_router, prefix="/api/auth", tags=["User Authentication"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat History"])
app.include_router(query_router, prefix="/api/query", tags=["Instructor AI Chat"])

# Health Endpoints
@app.get("/")
async def root():
    return {"message": "Server is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Run the App
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1234, log_level="info")

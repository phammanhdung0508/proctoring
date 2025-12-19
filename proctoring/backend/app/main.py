"""
Main FastAPI application entry point.

This module initializes the FastAPI application and configures
middleware, routes, and event handlers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import websocket
from app.config import settings
from app.services.websocket_manager import manager

# Create FastAPI application instance
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-Powered Proctoring System for Cheating Detection",
    debug=settings.DEBUG,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """
    Root endpoint - Health check.

    Returns:
        dict: Welcome message and system status
    """
    return {
        "message": "AI Proctoring System API",
        "version": settings.VERSION,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: System health status
    """
    return {
        "status": "healthy",
        "version": settings.VERSION,
    }


@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.

    Initialize services, load models, setup database connections, etc.
    """
    print(f"[STARTUP] {settings.APP_NAME} v{settings.VERSION} starting...")
    print(f"[INFO] Server running on http://{settings.HOST}:{settings.PORT}")
    print(f"[INFO] API docs available at http://{settings.HOST}:{settings.PORT}/docs")
    print(f"[INFO] WebSocket endpoint: ws://{settings.HOST}:{settings.PORT}/ws/{{session_id}}")

    # Initialize detection pipeline
    print("[INIT] Initializing detection modules...")
    websocket.initialize_pipeline()

    # TODO: Setup database connection
    # TODO: Create necessary directories

    print("[SUCCESS] Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.

    Cleanup resources, close connections, etc.
    """
    print("[SHUTDOWN] Shutting down application...")

    # Close all WebSocket connections
    await manager.close_all()

    # Cleanup detection pipeline sessions
    if websocket.pipeline:
        websocket.pipeline.clear_all_sessions()

    # TODO: Close database connections
    # TODO: Cleanup temporary files

    print("[SUCCESS] Application shutdown complete")


# Include routers
app.include_router(websocket.router, tags=["websocket"])

# TODO: Add additional routers
# from app.api import sessions, reports
# app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
# app.include_router(reports.router, prefix="/api/reports", tags=["reports"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )

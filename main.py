"""Entry point for running the application."""
import uvicorn
import logging
from app.config import settings

logging.basicConfig(level=settings.log_level)

if __name__ == "__main__":
    print("API running at: http://localhost:8000")
    print("API docs at:    http://localhost:8000/docs")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # Listen on all interfaces (required for Docker/Render)
        port=8000,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )

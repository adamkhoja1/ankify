"""Main FastAPI application for web interface."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .routes import cards, config, generation, llm, sessions


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="Ankification API",
        description="API for generating and managing Anki flashcards",
        version="0.1.0",
    )

    # Configure CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:8000",  # FastAPI server
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "message": "Ankification API is running"}

    @app.get("/", response_class=HTMLResponse)
    async def root() -> str:
        """Root endpoint - shows API info or serves frontend."""
        static_dir = Path(__file__).parent / "static"
        if static_dir.exists():
            # Serve the built frontend
            index_file = static_dir / "index.html"
            if index_file.exists():
                return index_file.read_text()

        # Development mode - show API info
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ankification API</title>
            <style>
                body {
                    font-family: system-ui, -apple-system, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    line-height: 1.6;
                }
                h1 { color: #2563eb; }
                .endpoint {
                    background: #f1f5f9;
                    padding: 10px;
                    margin: 10px 0;
                    border-radius: 5px;
                    font-family: monospace;
                }
                a { color: #2563eb; }
            </style>
        </head>
        <body>
            <h1>🎴 Ankification API</h1>
            <p>The FastAPI backend is running successfully!</p>

            <h2>Quick Links</h2>
            <ul>
                <li><a href="/docs">📚 Interactive API Documentation (Swagger UI)</a></li>
                <li><a href="/redoc">📖 Alternative API Documentation (ReDoc)</a></li>
                <li><a href="/api/health">❤️ Health Check</a></li>
            </ul>

            <h2>Frontend Development</h2>
            <p>To start the React frontend development server:</p>
            <div class="endpoint">
                cd web<br>
                npm run dev
            </div>
            <p>The frontend will be available at <a href="http://localhost:5173">http://localhost:5173</a></p>

            <h2>API Endpoints</h2>
            <ul>
                <li><strong>Cards:</strong> <code>/api/cards</code></li>
                <li><strong>Sessions:</strong> <code>/api/sessions</code></li>
                <li><strong>Generation:</strong> <code>/api/generate</code></li>
                <li><strong>LLM:</strong> <code>/api/llm</code></li>
                <li><strong>Config:</strong> <code>/api/config</code></li>
            </ul>
        </body>
        </html>
        """

    # Include API routers
    app.include_router(cards.router)
    app.include_router(sessions.router)
    app.include_router(generation.router)
    app.include_router(llm.router)
    app.include_router(config.router)

    return app


# Create app instance
app = create_app()

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import cases
from app.api import auth

app = FastAPI(
    title="VYAPAR PULSE AI API",
    version="1.0.0",
    description="Evidence-First Financial Health Card and Credit-Twin for MSMEs.",
)

# Replace with exact frontend URL in production
FRONTEND_URL = "http://localhost:3000"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        
        # If no origin but we have referer, we can check referer.
        check_val = origin or (referer.split('/')[2] if referer else None)
        
        # Very simple CSRF check for prototype
        if check_val and "localhost:3000" not in check_val:
            # For strict CSRF, we might block this, but for dev we can pass
            pass
            
    return await call_next(request)

app.include_router(auth.router)
app.include_router(cases.router)

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "vyapar-pulse-api", "version": "1.0.0"}

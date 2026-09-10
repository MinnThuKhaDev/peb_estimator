import os
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from . import estimator, file_parser
from .auth import router as auth_router, users_router, get_current_user
from .database import SessionLocal, init_db
from .models import Project, User
from .schemas import EstimateRequest, ProjectCreate, ProjectOut

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

ALLOWED_UPLOAD_EXTS = {"xlsx", "xls", "pdf", "png", "jpg", "jpeg", "txt", "dwg", "dxf"}

app = FastAPI(title="PEB Estimate Assistant")

# Restrict CORS to configured origins in production (set ALLOWED_ORIGINS as a
# comma-separated list, e.g. https://your-app.onrender.com). Defaults to "*"
# for easy local development.
_origins = os.getenv("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _origins == "*" else [o.strip() for o in _origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(auth_router)
app.include_router(users_router)


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------- projects (history) — login required
@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(_: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        return db.query(Project).order_by(Project.id.desc()).all()
    finally:
        db.close()


@app.post("/api/projects", response_model=ProjectOut)
def create_project(p: ProjectCreate, _: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        proj = Project(**p.dict())
        db.add(proj)
        db.commit()
        db.refresh(proj)
        return proj
    finally:
        db.close()


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, _: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        proj = db.get(Project, project_id)
        if not proj:
            raise HTTPException(404, "Project not found")
        db.delete(proj)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# ---------------------------------------------------------------- estimate — login required
@app.post("/api/estimate")
def calc_estimate(req: EstimateRequest, _: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        historical = db.query(Project).all()
        return estimator.compute_estimate(req.dict(), historical)
    finally:
        db.close()


# ---------------------------------------------------------------- offline file parse (also handles DWG storage)
@app.post("/api/upload-parse")
async def upload_parse(file: UploadFile = File(...), _: User = Depends(get_current_user)):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(400, f"Unsupported file type: .{ext}")

    content = await file.read()

    # Store the raw file (needed for DWG, useful as a reference for everything else)
    safe_name = Path(file.filename).name
    dest = UPLOADS_DIR / safe_name
    dest.write_bytes(content)

    try:
        text = file_parser.extract_text(file.filename, content)
    except Exception as e:
        raise HTTPException(400, f"Could not read file: {e}")
    fields = file_parser.regex_extract(text) if ext != "dwg" else {}
    return {"fields": fields, "preview": text[:3000], "stored_as": safe_name}


@app.get("/api/uploads/{filename}")
def download_upload(filename: str, _: User = Depends(get_current_user)):
    path = UPLOADS_DIR / Path(filename).name
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path)


# ---------------------------------------------------------------- AI extract — prefers free Gemini
@app.post("/api/ai-extract")
async def ai_extract_endpoint(
    file: UploadFile = File(...),
    note: Optional[str] = Form(None),
    _: User = Depends(get_current_user),
):
    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    content = await file.read()
    try:
        if provider == "anthropic":
            from . import ai_extract
            return ai_extract.extract_with_ai(file.filename, content, note)
        from . import ai_gemini
        return ai_gemini.extract_with_ai(file.filename, content, note)
    except Exception as e:
        # Both AIConfigError and provider HTTP errors land here with a clear message
        raise HTTPException(400, str(e))

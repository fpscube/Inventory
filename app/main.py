from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("INVENTORY_DATA_DIR", Path.home() / ".inventory")).expanduser()
PHOTO_DIR = DATA_DIR / "photos"
DB_PATH = DATA_DIR / "inventory.sqlite3"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PHOTOS = 5
MAX_ITEM_RESULTS = 50
MAX_IMAGE_SIDE = 1600
TARGET_IMAGE_BYTES = 200 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

APP_VERSION = "0.3.3"
app = FastAPI(title="Inventory", version=APP_VERSION, description="Inventaire personnel sur réseau local")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")


@app.middleware("http")
async def disable_caching(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS photos (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                position INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_items_updated ON items(updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_photos_item ON photos(item_id, position);
        """)


@app.on_event("startup")
def startup() -> None:
    init_db()


def item_json(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    photos = conn.execute(
        "SELECT id FROM photos WHERE item_id = ? ORDER BY position", (row["id"],)
    ).fetchall()
    return {
        "id": row["id"], "description": row["description"], "location": row["location"],
        "created_at": row["created_at"], "updated_at": row["updated_at"],
        "photos": [f"/api/photos/{p['id']}" for p in photos],
    }


def encode_image(raw: bytes) -> bytes:
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image trop volumineuse (maximum 20 Mo).")
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.format not in ALLOWED_FORMATS:
                raise HTTPException(415, "Format d’image non pris en charge.")
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(415, "Fichier image invalide ou non pris en charge.") from exc
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
    quality = 82
    while True:
        output = io.BytesIO()
        image.save(output, "JPEG", quality=quality, optimize=True)
        data = output.getvalue()
        if len(data) <= TARGET_IMAGE_BYTES or quality <= 45:
            return data
        quality -= 7


async def read_photo(file: UploadFile) -> bytes:
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if not raw:
        raise HTTPException(400, "La photo est vide.")
    return encode_image(raw)


@app.get("/")
def home() -> HTMLResponse:
    html = (APP_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html.replace("{{APP_VERSION}}", APP_VERSION))


@app.get("/api/version")
def version() -> dict:
    return {"version": APP_VERSION}


@app.get("/api/items")
def list_items(q: str = "") -> list[dict]:
    with db() as conn:
        if q.strip():
            needle = f"%{q.strip()}%"
            rows = conn.execute("""
                SELECT DISTINCT i.* FROM items i
                LEFT JOIN photos p ON p.item_id = i.id
                WHERE i.description LIKE ? COLLATE NOCASE OR i.location LIKE ? COLLATE NOCASE
                ORDER BY i.updated_at DESC LIMIT ?
            """, (needle, needle, MAX_ITEM_RESULTS)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM items ORDER BY updated_at DESC LIMIT ?", (MAX_ITEM_RESULTS,)).fetchall()
        return [item_json(conn, row) for row in rows]


@app.get("/api/items/{item_id}")
def get_item(item_id: str) -> dict:
    with db() as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Objet introuvable.")
        return item_json(conn, row)


@app.post("/api/items", status_code=201)
async def create_item(
    description: str = Form(...), location: str = Form(...),
    photos: list[UploadFile] = File(...),
) -> dict:
    description, location = description.strip(), location.strip()
    if not description or not location:
        raise HTTPException(422, "La description et l’emplacement sont obligatoires.")
    if not photos or len(photos) > MAX_PHOTOS:
        raise HTTPException(422, "Ajoutez entre 1 et 5 photos.")
    encoded = [await read_photo(photo) for photo in photos]
    item_id, timestamp = str(uuid4()), now()
    written: list[Path] = []
    try:
        with db() as conn:
            conn.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?)",
                         (item_id, description, location, timestamp, timestamp))
            for position, data in enumerate(encoded):
                photo_id = str(uuid4())
                path = PHOTO_DIR / f"{photo_id}.jpg"
                path.write_bytes(data)
                written.append(path)
                conn.execute("INSERT INTO photos VALUES (?, ?, ?, ?)",
                             (photo_id, item_id, path.name, position))
        return get_item(item_id)
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise


@app.put("/api/items/{item_id}")
async def update_item(
    item_id: str, description: str = Form(...), location: str = Form(...),
    photos: list[UploadFile] | None = File(None),
) -> dict:
    description, location = description.strip(), location.strip()
    if not description or not location:
        raise HTTPException(422, "La description et l’emplacement sont obligatoires.")
    encoded = [await read_photo(photo) for photo in photos] if photos else []
    if len(encoded) > MAX_PHOTOS:
        raise HTTPException(422, "Maximum 5 photos.")
    with db() as conn:
        old = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not old:
            raise HTTPException(404, "Objet introuvable.")
        conn.execute("UPDATE items SET description=?, location=?, updated_at=? WHERE id=?",
                     (description, location, now(), item_id))
        if encoded:
            previous = conn.execute("SELECT filename FROM photos WHERE item_id=?", (item_id,)).fetchall()
            conn.execute("DELETE FROM photos WHERE item_id=?", (item_id,))
            for position, data in enumerate(encoded):
                photo_id = str(uuid4())
                path = PHOTO_DIR / f"{photo_id}.jpg"
                path.write_bytes(data)
                conn.execute("INSERT INTO photos VALUES (?, ?, ?, ?)",
                             (photo_id, item_id, path.name, position))
            for row in previous:
                (PHOTO_DIR / row["filename"]).unlink(missing_ok=True)
    return get_item(item_id)


@app.delete("/api/items/{item_id}", status_code=204)
def delete_item(item_id: str) -> None:
    with db() as conn:
        photos = conn.execute("SELECT filename FROM photos WHERE item_id=?", (item_id,)).fetchall()
        cur = conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Objet introuvable.")
        for photo in photos:
            (PHOTO_DIR / photo["filename"]).unlink(missing_ok=True)


@app.get("/api/photos/{photo_id}")
def get_photo(photo_id: str) -> FileResponse:
    with db() as conn:
        row = conn.execute("SELECT filename FROM photos WHERE id=?", (photo_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Photo introuvable.")
    path = PHOTO_DIR / row["filename"]
    if not path.is_file():
        raise HTTPException(404, "Fichier photo introuvable.")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/export")
def export_zip() -> StreamingResponse:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stream = io.BytesIO()
    with db() as conn:
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        items = [dict(row) for row in conn.execute("SELECT * FROM items ORDER BY id")]
        photos = [dict(row) for row in conn.execute("SELECT * FROM photos ORDER BY item_id, position")]
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(DB_PATH, "inventory.sqlite3")
        archive.writestr("manifest.json", json.dumps({"format_version": 1, "items": items, "photos": photos}, ensure_ascii=False, indent=2))
        for photo in photos:
            path = PHOTO_DIR / photo["filename"]
            if path.is_file():
                archive.write(path, f"photos/{photo['filename']}")
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="inventory-{datetime.now():%Y%m%d-%H%M%S}.zip"'
    })


@app.post("/api/import")
async def import_zip(file: UploadFile = File(...)) -> JSONResponse:
    raw = await file.read(250 * 1024 * 1024 + 1)
    if len(raw) > 250 * 1024 * 1024:
        raise HTTPException(413, "Archive trop volumineuse (maximum 250 Mo).")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format_version") != 1:
            raise ValueError("version inconnue")
        items, photos = manifest["items"], manifest["photos"]
        item_ids = {item["id"] for item in items}
        if len(item_ids) != len(items) or any(p["item_id"] not in item_ids for p in photos):
            raise ValueError("relations invalides")
        if any(not p["filename"].endswith(".jpg") or PurePosixPath(p["filename"]).name != p["filename"] for p in photos):
            raise ValueError("chemin photo invalide")
        image_data = {}
        for photo in photos:
            data = archive.read(f"photos/{photo['filename']}")
            image_data[photo["filename"]] = encode_image(data)
    except (zipfile.BadZipFile, KeyError, ValueError, TypeError, json.JSONDecodeError, HTTPException) as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(400, "Archive ZIP invalide ou incompatible.") from exc
    with tempfile.TemporaryDirectory(dir=DATA_DIR) as temp_name:
        temp_photos = Path(temp_name)
        for name, data in image_data.items():
            (temp_photos / name).write_bytes(data)
        with db() as conn:
            conn.execute("DELETE FROM items")
            for item in items:
                conn.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?)",
                             (item["id"], item["description"], item["location"], item["created_at"], item["updated_at"]))
            for photo in photos:
                conn.execute("INSERT INTO photos VALUES (?, ?, ?, ?)",
                             (photo["id"], photo["item_id"], photo["filename"], photo["position"]))
            for old_photo in PHOTO_DIR.glob("*.jpg"):
                old_photo.unlink(missing_ok=True)
            for path in temp_photos.iterdir():
                shutil.move(str(path), str(PHOTO_DIR / path.name))
    return JSONResponse({"imported_items": len(items)})

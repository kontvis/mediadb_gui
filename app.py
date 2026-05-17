import csv
import io
import json
import base64
from datetime import date

import anthropic
from PIL import Image, ImageOps
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

from config import Config

load_dotenv()

# Initialize Flask app and configuration
app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy
db = SQLAlchemy(app)


# --- Database models ---
class MediaItem(db.Model):
    __tablename__ = "media_item"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    media_type = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer)
    notes = db.Column(db.Text)
    date_added = db.Column(db.Date, default=date.today)

    book = db.relationship(
        "BookDetails",
        uselist=False,
        back_populates="media",
        cascade="all, delete-orphan",
    )
    audio = db.relationship(
        "AudioDetails",
        uselist=False,
        back_populates="media",
        cascade="all, delete-orphan",
    )
    video = db.relationship(
        "VideoDetails",
        uselist=False,
        back_populates="media",
        cascade="all, delete-orphan",
    )


class BookDetails(db.Model):
    __tablename__ = "book_details"
    id = db.Column(
        db.Integer, db.ForeignKey("media_item.id"), primary_key=True
    )
    author = db.Column(db.Text)
    isbn = db.Column(db.Text)
    publisher = db.Column(db.Text)
    page_count = db.Column(db.Integer)
    physical_description = db.Column(db.Text)
    genre = db.Column(db.Text)

    media = db.relationship("MediaItem", back_populates="book")


class AudioDetails(db.Model):
    __tablename__ = "audio_details"
    id = db.Column(
        db.Integer, db.ForeignKey("media_item.id"), primary_key=True
    )
    artist = db.Column(db.Text)
    album = db.Column(db.Text)
    track_count = db.Column(db.Integer)
    format = db.Column(db.Text)
    genre = db.Column(db.Text)

    media = db.relationship("MediaItem", back_populates="audio")


class VideoDetails(db.Model):
    __tablename__ = "video_details"
    id = db.Column(
        db.Integer, db.ForeignKey("media_item.id"), primary_key=True
    )
    director = db.Column(db.Text)
    runtime_minutes = db.Column(db.Integer)
    rating = db.Column(db.Text)
    format = db.Column(db.Text)
    genre = db.Column(db.Text)

    media = db.relationship("MediaItem", back_populates="video")


def parse_optional_int(raw_value):
    """Convert a form/CSV value to int or None."""
    value = (
        (raw_value or "").strip() if isinstance(raw_value, str) else raw_value
    )
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# --- Routes ---
@app.route("/")
def index():
    """Redirect to the media list (home)."""
    return redirect(url_for("list_media"))


@app.route("/media")
def list_media():
    """List all media items with search and sort.

    Query params: q (search), sort_by (column), sort_dir (asc/desc).
    """
    q = request.args.get("q", "").strip()
    sort_by = request.args.get("sort_by", "date_added").strip()
    sort_dir = request.args.get("sort_dir", "desc").strip()

    items = MediaItem.query

    # Search filter: title, media_type, or genre
    if q:
        like = f"%{q}%"
        items = items.filter(
            db.or_(
                MediaItem.title.ilike(like),
                MediaItem.media_type.ilike(like),
                MediaItem.book.has(BookDetails.genre.ilike(like)),
                MediaItem.audio.has(AudioDetails.genre.ilike(like)),
                MediaItem.video.has(VideoDetails.genre.ilike(like)),
            )
        )

    # Sorting
    is_asc = sort_dir == "asc"
    if sort_by == "title":
        items = items.order_by(
            MediaItem.title.asc() if is_asc else MediaItem.title.desc()
        )
    elif sort_by == "type":
        items = items.order_by(
            MediaItem.media_type.asc()
            if is_asc
            else MediaItem.media_type.desc()
        )
    elif sort_by == "year":
        items = items.order_by(
            MediaItem.year.asc() if is_asc else MediaItem.year.desc()
        )
    elif sort_by == "genre":
        # Sort by coalesced genre from the three detail tables
        items = items.outerjoin(BookDetails, BookDetails.id == MediaItem.id)
        items = items.outerjoin(AudioDetails, AudioDetails.id == MediaItem.id)
        items = items.outerjoin(VideoDetails, VideoDetails.id == MediaItem.id)
        genre_coalesce = db.func.coalesce(
            BookDetails.genre, AudioDetails.genre, VideoDetails.genre
        )
        items = items.order_by(
            genre_coalesce.asc() if is_asc else genre_coalesce.desc()
        )
    else:  # default: date_added
        items = items.order_by(
            MediaItem.date_added.asc()
            if is_asc
            else MediaItem.date_added.desc()
        )

    items = items.all()
    return render_template(
        "list_media.html", items=items, q=q, sort_by=sort_by, sort_dir=sort_dir
    )


@app.route("/media/<int:item_id>")
def view_media(item_id):
    """Detail view for a single media item."""
    item = MediaItem.query.get_or_404(item_id)
    return render_template("view_media.html", item=item)


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    """Delete a media item."""
    item = MediaItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash(
        f'{item.media_type.title()} "{item.title}" deleted successfully.',
        "success",
    )
    return redirect(url_for("list_media"))


def _auto_rotate_image(image_bytes):
    """Apply EXIF-based auto-rotation so upside-down/sideways photos are corrected."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        buf = io.BytesIO()
        fmt = img.format or "JPEG"
        img.save(buf, format=fmt)
        return buf.getvalue()
    except Exception:
        return image_bytes


_TITLE_PAGE_PROMPT = """
You are analyzing an image of a book title page. Extract the fields below and
return ONLY a valid JSON object — no prose, no markdown fences.

Rules:
- "title" is required; every title page has one.
- "author" is usually present. If only editors are listed and no authors, use
  the editors as the author value (comma-separated if more than one).
- "publisher" is usually present. Publisher names often contain words like
  Press, Publishing, Books, University, Inc., Ltd.
- City names that appear on the page are publisher location info — put them in
  "notes", not "publisher".
- "year" and "isbn" are rare on title pages; only populate if clearly present.
- NEVER populate genre or page_count — title pages never list these.
- "notes" receives any other text that does not fit the above fields
  (cities, edition info, marketing phrases, etc.).
- Use null for any field not found. Use a plain string for all values.
- "media_type" should be "book" for a title page; use "audio" or "video" only
  if the image is clearly not a book.

Return exactly this JSON shape:
{
  "media_type": "book",
  "title": null,
  "author": null,
  "publisher": null,
  "year": null,
  "isbn": null,
  "notes": null
}
"""


def process_image_for_media(image_data):
    """Send image to Claude and return extracted book metadata as structured fields."""
    api_key = app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "Anthropic API key not configured"}

    try:
        encoded = image_data.split(",", maxsplit=1)[-1]
        image_bytes = base64.b64decode(encoded)
        image_bytes = _auto_rotate_image(image_bytes)
        image_content = base64.b64encode(image_bytes).decode("utf-8")

        client = anthropic.Anthropic(api_key=api_key)
        model = app.config.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
        message = client.messages.create(
            model=model,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_content,
                        },
                    },
                    {"type": "text", "text": _TITLE_PAGE_PROMPT},
                ],
            }],
        )

        raw = message.content[0].text.strip()
        extracted = json.loads(raw)

        return {
            "media_type": extracted.get("media_type") or "book",
            "title":      extracted.get("title"),
            "author":     extracted.get("author"),
            "publisher":  extracted.get("publisher"),
            "isbn":       extracted.get("isbn"),
            "year":       extracted.get("year"),
            "notes":      extracted.get("notes"),
            "full_text":  "",
            "confidence": 1.0,
        }

    except json.JSONDecodeError as e:
        return {"error": f"Could not parse Claude response as JSON: {e}"}
    except Exception as e:
        return {"error": f"Claude API error: {str(e)}"}


@app.route("/scan")
def scan_ui():
    """Render photo capture UI."""
    return render_template("scan.html")


@app.route("/process_image", methods=["POST"])
def process_image():
    """Accept image JSON and return extracted metadata."""
    data = request.get_json(force=True)
    image_data = data.get("image") if data else None
    if not image_data:
        return ({"error": "image required"}, 400)

    try:
        meta = process_image_for_media(image_data)
        if "error" in meta:
            return ({"error": meta["error"]}, 500)

        # Normalize response fields to form-compatible keys
        notes_val = meta.get("notes") or ""
        full_text = meta.get("full_text", "")
        if full_text:
            notes_val = (notes_val + "\n\nOCR Text:\n" + full_text).strip()
        response = {
            "media_type": meta.get("media_type"),
            "title": meta.get("title"),
            "author": meta.get("author"),
            "publisher": meta.get("publisher"),
            "isbn": meta.get("isbn"),
            "year": meta.get("year"),
            "notes": notes_val or None,
            "confidence": meta.get("confidence"),
        }
        return (response, 200)
    except Exception as e:
        return ({"error": f"Processing error: {str(e)}"}, 500)


# --- Add forms ---
@app.route("/add/book", methods=["GET", "POST"])
def add_book():
    """Add a new book: insert into media_item then book_details."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        year = parse_optional_int(request.form.get("year"))
        notes = request.form.get("notes")

        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("add_book"))

        item = MediaItem(
            title=title, media_type="book", year=year, notes=notes
        )
        db.session.add(item)
        db.session.commit()

        details = BookDetails(
            id=item.id,
            author=request.form.get("author"),
            isbn=request.form.get("isbn"),
            publisher=request.form.get("publisher"),
            page_count=parse_optional_int(request.form.get("page_count")),
            physical_description=request.form.get("physical_description"),
            genre=request.form.get("genre"),
        )
        db.session.add(details)
        db.session.commit()
        flash("Book added successfully.", "success")
        return redirect(url_for("view_media", item_id=item.id))

    return render_template("add_book.html")


@app.route("/add/audio", methods=["GET", "POST"])
def add_audio():
    """Add a new audio item."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("add_audio"))

        item = MediaItem(
            title=title,
            media_type="audio",
            year=parse_optional_int(request.form.get("year")),
            notes=request.form.get("notes"),
        )
        db.session.add(item)
        db.session.commit()

        details = AudioDetails(
            id=item.id,
            artist=request.form.get("artist"),
            album=request.form.get("album"),
            track_count=parse_optional_int(request.form.get("track_count")),
            format=request.form.get("format"),
            genre=request.form.get("genre"),
        )
        db.session.add(details)
        db.session.commit()
        flash("Audio item added successfully.", "success")
        return redirect(url_for("view_media", item_id=item.id))

    return render_template("add_audio.html")


@app.route("/add/video", methods=["GET", "POST"])
def add_video():
    """Add a new video item."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("add_video"))

        item = MediaItem(
            title=title,
            media_type="video",
            year=parse_optional_int(request.form.get("year")),
            notes=request.form.get("notes"),
        )
        db.session.add(item)
        db.session.commit()

        details = VideoDetails(
            id=item.id,
            director=request.form.get("director"),
            runtime_minutes=parse_optional_int(
                request.form.get("runtime_minutes")
            ),
            rating=request.form.get("rating"),
            format=request.form.get("format"),
            genre=request.form.get("genre"),
        )
        db.session.add(details)
        db.session.commit()
        flash("Video item added successfully.", "success")
        return redirect(url_for("view_media", item_id=item.id))

    return render_template("add_video.html")


# --- Edit routes ---
@app.route("/edit/book/<int:item_id>", methods=["GET", "POST"])
def edit_book(item_id):
    """Edit an existing book (media_item + book_details)."""
    item = MediaItem.query.get_or_404(item_id)
    details = BookDetails.query.get(item_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("edit_book", item_id=item_id))

        item.title = title
        item.year = parse_optional_int(request.form.get("year"))
        item.notes = request.form.get("notes")

        if not details:
            details = BookDetails(id=item.id)
            db.session.add(details)

        details.author = request.form.get("author")
        details.isbn = request.form.get("isbn")
        details.publisher = request.form.get("publisher")
        details.page_count = parse_optional_int(request.form.get("page_count"))
        details.physical_description = request.form.get("physical_description")
        details.genre = request.form.get("genre")

        db.session.commit()
        flash("Book updated successfully.", "success")
        return redirect(url_for("view_media", item_id=item.id))

    return render_template("edit_book.html", item=item, details=details)


@app.route("/edit/audio/<int:item_id>", methods=["GET", "POST"])
def edit_audio(item_id):
    """Edit an existing audio item."""
    item = MediaItem.query.get_or_404(item_id)
    details = AudioDetails.query.get(item_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("edit_audio", item_id=item_id))

        item.title = title
        item.year = parse_optional_int(request.form.get("year"))
        item.notes = request.form.get("notes")

        if not details:
            details = AudioDetails(id=item.id)
            db.session.add(details)

        details.artist = request.form.get("artist")
        details.album = request.form.get("album")
        details.track_count = parse_optional_int(
            request.form.get("track_count")
        )
        details.format = request.form.get("format")
        details.genre = request.form.get("genre")

        db.session.commit()
        flash("Audio updated successfully.", "success")
        return redirect(url_for("view_media", item_id=item.id))

    return render_template("edit_audio.html", item=item, details=details)


@app.route("/edit/video/<int:item_id>", methods=["GET", "POST"])
def edit_video(item_id):
    """Edit an existing video item."""
    item = MediaItem.query.get_or_404(item_id)
    details = VideoDetails.query.get(item_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("edit_video", item_id=item_id))

        item.title = title
        item.year = parse_optional_int(request.form.get("year"))
        item.notes = request.form.get("notes")

        if not details:
            details = VideoDetails(id=item.id)
            db.session.add(details)

        details.director = request.form.get("director")
        details.runtime_minutes = parse_optional_int(
            request.form.get("runtime_minutes")
        )
        details.rating = request.form.get("rating")
        details.format = request.form.get("format")
        details.genre = request.form.get("genre")

        db.session.commit()
        flash("Video updated successfully.", "success")
        return redirect(url_for("view_media", item_id=item.id))

    return render_template("edit_video.html", item=item, details=details)


# --- CSV Upload ---
@app.route("/upload-csv", methods=["GET", "POST"])
def upload_csv():
    """Upload a CSV file to bulk add media items."""
    if request.method == "POST":
        if "csv_file" not in request.files:
            flash("No file selected.", "danger")
            return redirect(url_for("upload_csv"))

        file = request.files["csv_file"]
        if file.filename == "":
            flash("No file selected.", "danger")
            return redirect(url_for("upload_csv"))

        if not file.filename.endswith(".csv"):
            flash("File must be a CSV.", "danger")
            return redirect(url_for("upload_csv"))

        try:
            stream = io.StringIO(file.read().decode("utf-8"), newline=None)
            reader = csv.DictReader(stream)

            added_count = 0
            for row in reader:
                title = row.get("title", "").strip()
                media_type = row.get("media_type", "").strip()

                # Only title and media_type are required
                if not title or not media_type:
                    continue

                # Create media_item
                item = MediaItem(
                    title=title,
                    media_type=media_type,
                    year=parse_optional_int(row.get("year")),
                    notes=row.get("notes", "").strip() or None,
                    date_added=date.today(),
                )
                db.session.add(item)
                db.session.flush()  # Get the ID without committing yet

                # Create type-specific details
                if media_type.lower() == "book":
                    details = BookDetails(
                        id=item.id,
                        author=row.get("author", "").strip() or None,
                        isbn=row.get("isbn", "").strip() or None,
                        publisher=row.get("publisher", "").strip() or None,
                        page_count=parse_optional_int(row.get("page_count")),
                        physical_description=row.get(
                            "physical_description", ""
                        ).strip()
                        or None,
                        genre=row.get("book_genre", "").strip() or None,
                    )
                    db.session.add(details)
                elif media_type.lower() == "audio":
                    details = AudioDetails(
                        id=item.id,
                        artist=row.get("artist", "").strip() or None,
                        album=row.get("album", "").strip() or None,
                        track_count=parse_optional_int(row.get("track_count")),
                        format=row.get("audio_format", "").strip() or None,
                        genre=row.get("audio_genre", "").strip() or None,
                    )
                    db.session.add(details)
                elif media_type.lower() == "video":
                    details = VideoDetails(
                        id=item.id,
                        director=row.get("director", "").strip() or None,
                        runtime_minutes=parse_optional_int(
                            row.get("runtime_minutes")
                        ),
                        rating=row.get("rating", "").strip() or None,
                        format=row.get("video_format", "").strip() or None,
                        genre=row.get("video_genre", "").strip() or None,
                    )
                    db.session.add(details)

                added_count += 1

            db.session.commit()
            flash(f"{added_count} item(s) added successfully.", "success")
            return redirect(url_for("list_media"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error processing CSV: {str(e)}", "danger")
            return redirect(url_for("upload_csv"))

    return render_template("upload_csv.html")


if __name__ == "__main__":
    # Create tables if running locally with sqlite fallback
    with app.app_context():
        db.create_all()
    app.run(debug=True)

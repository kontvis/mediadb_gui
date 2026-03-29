# AI Coding Assistant Instructions

## Architecture Overview
This is a Flask web application for managing a family media catalog (books, audio, video) using SQLAlchemy ORM with PostgreSQL/SQLite.

**Core Pattern**: Media items use a "header-detail" structure:
- `MediaItem` table stores common fields (title, type, year, notes, date_added)
- Type-specific details in separate tables (`BookDetails`, `AudioDetails`, `VideoDetails`) linked by foreign key
- Relationships configured with `back_populates` and `cascade='all, delete-orphan'`

**Key Files**:
- `app.py`: Main application logic, routes, models, barcode lookups
- `config.py`: Environment-based configuration (DATABASE_URL, SECRET_KEY)
- `templates/`: Jinja2 templates with Bootstrap 5 responsive design
- Database tables auto-created via `db.create_all()` when using SQLite

## Database Schema & Relationships
```python
# Always create MediaItem first, then details
item = MediaItem(title=title, media_type='book', ...)
db.session.add(item)
db.session.commit()  # Get ID

details = BookDetails(id=item.id, author=..., ...)
db.session.add(details)
db.session.commit()
```

**Querying with relationships**:
```python
# Access details: item.book.author, item.audio.genre, etc.
# Search across types: use outer joins with coalesce for genre sorting
items = items.outerjoin(BookDetails).outerjoin(AudioDetails).outerjoin(VideoDetails)
genre_expr = db.func.coalesce(BookDetails.genre, AudioDetails.genre, VideoDetails.genre)
```

## Barcode Scanning & API Integration
**Photo Processing Logic** (`process_image_for_media`):
- Accept base64 image data from client
- Use Google Vision API for object detection (book/CD/DVD) and OCR
- Parse OCR text to extract title, author, year using heuristics
- Return media_type, title, author, year, notes (with OCR text)

**API Response Normalization**: Convert Vision API results to consistent form keys

**Client-Side**: File input with camera capture stores prefill data in `localStorage`, redirects to add form with JavaScript autofill.

## Form Handling Patterns
**Add/Edit Flow**:
1. Validate required fields (title always required)
2. Create/update `MediaItem` 
3. Create/update type-specific details (handle missing details gracefully)
4. Use `flash()` for user feedback, redirect to `view_media`

**CSV Upload**: 
- Required columns: title, media_type
- Map CSV columns to model fields (e.g., `book_genre` → `BookDetails.genre`)
- Use `db.session.flush()` to get IDs before creating details
- Bulk commit with error rollback

## UI/UX Patterns
**Responsive Design**:
- Bootstrap 5 with `table-responsive`, `d-none d-sm-table-cell` for column hiding
- Small-screen sort controls (select dropdowns) + stacked card layout
- Mobile forms: single-column, `btn-lg`, input types (`number`, `tel`)

**Navigation**: Navbar with direct links to add forms, search bar integrated

**Search/Sort**: Query params `q`, `sort_by`, `sort_dir` with URL-based state

## Development Workflow
**Setup**:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql://...'  # or omit for SQLite
export GOOGLE_VISION_API_KEY='...'  # for photo processing
flask run --host=127.0.0.1 --port=5000
# Tables auto-create on first run with SQLite
```

**Adding New Media Type**:
1. Create `NewDetails` model with FK to `MediaItem.id`
2. Add relationship to `MediaItem`
3. Create add/edit routes following existing pattern
4. Add navbar links and templates
5. Update CSV processing and barcode detection

**API Keys**: Set `TMDB_API_KEY` env var for video barcode lookups (optional), `GOOGLE_VISION_API_KEY` for photo processing (service account JSON or API key)

## Code Style Notes
- Use `request.form.get('field')` with manual type conversion (int/float checks)
- Handle optional fields: `None` for missing values
- Exception handling in API calls with fallbacks
- Consistent flash message categories: 'success', 'danger'</content>
<parameter name="filePath">/home/zemyna/code/dbgui/.github/copilot-instructions.md
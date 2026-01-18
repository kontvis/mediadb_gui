from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date
import os
import csv
import io
import requests
import json
import base64
from config import Config

# Initialize Flask app and configuration
app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy
db = SQLAlchemy(app)


# --- Database models ---
class MediaItem(db.Model):
    __tablename__ = 'media_item'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    media_type = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer)
    notes = db.Column(db.Text)
    date_added = db.Column(db.Date, default=date.today)

    book = db.relationship('BookDetails', uselist=False, back_populates='media', cascade='all, delete-orphan')
    audio = db.relationship('AudioDetails', uselist=False, back_populates='media', cascade='all, delete-orphan')
    video = db.relationship('VideoDetails', uselist=False, back_populates='media', cascade='all, delete-orphan')


class BookDetails(db.Model):
    __tablename__ = 'book_details'
    id = db.Column(db.Integer, db.ForeignKey('media_item.id'), primary_key=True)
    author = db.Column(db.Text)
    isbn = db.Column(db.Text)
    publisher = db.Column(db.Text)
    page_count = db.Column(db.Integer)
    physical_description = db.Column(db.Text)
    genre = db.Column(db.Text)

    media = db.relationship('MediaItem', back_populates='book')


class AudioDetails(db.Model):
    __tablename__ = 'audio_details'
    id = db.Column(db.Integer, db.ForeignKey('media_item.id'), primary_key=True)
    artist = db.Column(db.Text)
    album = db.Column(db.Text)
    track_count = db.Column(db.Integer)
    format = db.Column(db.Text)
    genre = db.Column(db.Text)

    media = db.relationship('MediaItem', back_populates='audio')


class VideoDetails(db.Model):
    __tablename__ = 'video_details'
    id = db.Column(db.Integer, db.ForeignKey('media_item.id'), primary_key=True)
    director = db.Column(db.Text)
    runtime_minutes = db.Column(db.Integer)
    rating = db.Column(db.Text)
    format = db.Column(db.Text)
    genre = db.Column(db.Text)

    media = db.relationship('MediaItem', back_populates='video')


# --- Routes ---
@app.route('/')
def index():
    """Redirect to the media list (home)."""
    return redirect(url_for('list_media'))


@app.route('/media')
def list_media():
    """List all media items with search and sort. Query params: q (search), sort_by (column), sort_dir (asc/desc)."""
    q = request.args.get('q', '').strip()
    sort_by = request.args.get('sort_by', 'date_added').strip()
    sort_dir = request.args.get('sort_dir', 'desc').strip()
    
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
    is_asc = sort_dir == 'asc'
    if sort_by == 'title':
        items = items.order_by(MediaItem.title.asc() if is_asc else MediaItem.title.desc())
    elif sort_by == 'type':
        items = items.order_by(MediaItem.media_type.asc() if is_asc else MediaItem.media_type.desc())
    elif sort_by == 'year':
        items = items.order_by(MediaItem.year.asc() if is_asc else MediaItem.year.desc())
    elif sort_by == 'genre':
        # Sort by coalesced genre from the three detail tables
        items = items.outerjoin(BookDetails, BookDetails.id == MediaItem.id)
        items = items.outerjoin(AudioDetails, AudioDetails.id == MediaItem.id)
        items = items.outerjoin(VideoDetails, VideoDetails.id == MediaItem.id)
        genre_coalesce = db.func.coalesce(BookDetails.genre, AudioDetails.genre, VideoDetails.genre)
        items = items.order_by(genre_coalesce.asc() if is_asc else genre_coalesce.desc())
    else:  # default: date_added
        items = items.order_by(MediaItem.date_added.asc() if is_asc else MediaItem.date_added.desc())
    
    items = items.all()
    return render_template('list_media.html', items=items, q=q, sort_by=sort_by, sort_dir=sort_dir)


@app.route('/media/<int:item_id>')
def view_media(item_id):
    """Detail view for a single media item."""
    item = MediaItem.query.get_or_404(item_id)
    return render_template('view_media.html', item=item)


# --- Barcode lookup helpers ---
def lookup_isbn(isbn):
    """Try Google Books then OpenLibrary for ISBN metadata."""
    result = {}
    # Google Books
    try:
        gb_url = f'https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}'
        r = requests.get(gb_url, timeout=5)
        if r.ok:
            data = r.json()
            if data.get('totalItems', 0) > 0:
                vol = data['items'][0]['volumeInfo']
                result.update({
                    'title': vol.get('title'),
                    'author': ', '.join(vol.get('authors', [])) if vol.get('authors') else None,
                    'publisher': vol.get('publisher'),
                    'year': vol.get('publishedDate', '')[:4] if vol.get('publishedDate') else None,
                    'isbn': isbn,
                })
                return result
    except Exception:
        pass

    # OpenLibrary
    try:
        ol_url = f'https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data'
        r = requests.get(ol_url, timeout=5)
        if r.ok:
            data = r.json()
            key = f'ISBN:{isbn}'
            if key in data:
                item = data[key]
                result.update({
                    'title': item.get('title'),
                    'author': ', '.join([a.get('name') for a in item.get('authors', [])]) if item.get('authors') else None,
                    'publisher': item.get('publishers')[0].get('name') if item.get('publishers') else None,
                    'year': item.get('publish_date', '')[:4] if item.get('publish_date') else None,
                    'isbn': isbn,
                })
                return result
    except Exception:
        pass

    return None


def lookup_upc_musicbrainz(upc):
    """Lookup UPC via MusicBrainz (release search). Returns artist/title/year if found."""
    try:
        url = f'https://musicbrainz.org/ws/2/release/?query=barcode:{upc}&fmt=json'
        r = requests.get(url, headers={'User-Agent': 'dbgui/1.0 (email@example.com)'}, timeout=5)
        if r.ok:
            data = r.json()
            if data.get('releases'):
                rel = data['releases'][0]
                title = rel.get('title')
                artist = None
                if rel.get('artist-credit'):
                    artist = ', '.join([a.get('name') for a in rel.get('artist-credit') if a.get('name')])
                year = rel.get('date', '')[:4] if rel.get('date') else None
                return {'title': title, 'artist': artist, 'year': year, 'upc': upc}
    except Exception:
        pass
    return None


def lookup_upc_tmdb(upc):
    """Lookup UPC for video via TMDB if API key provided. Returns basic metadata."""
    tmdb_key = os.environ.get('TMDB_API_KEY')
    if not tmdb_key:
        return None
    try:
        url = f'https://api.themoviedb.org/3/search/movie?api_key={tmdb_key}&query={upc}'
        r = requests.get(url, timeout=5)
        if r.ok:
            data = r.json()
            if data.get('results'):
                mv = data['results'][0]
                return {'title': mv.get('title'), 'year': mv.get('release_date', '')[:4] if mv.get('release_date') else None, 'upc': upc}
    except Exception:
        pass
    return None


def detect_and_lookup(barcode):
    """Detect barcode type simply by length/prefix then use appropriate lookup functions."""
    bc = barcode.strip()
    # Heuristic: ISBN-10 (10) or ISBN-13 (13)
    if len(bc) in (10, 13):
        res = lookup_isbn(bc)
        if res:
            res['detected_type'] = 'isbn'
            res['media_type'] = 'book'
            return res

    # UPC/EAN typically 12 or 13 digits
    if len(bc) in (12, 13):
        # try musicbrainz
        res = lookup_upc_musicbrainz(bc)
        if res:
            res['detected_type'] = 'upc'
            res['media_type'] = 'audio'
            return res
        # try tmdb
        res = lookup_upc_tmdb(bc)
        if res:
            res['detected_type'] = 'upc'
            res['media_type'] = 'video'
            return res

    return None


def process_image_for_media(image_data):
    """Process uploaded image using Google Vision API to detect media type and extract text."""
    api_key = app.config.get('GOOGLE_VISION_API_KEY')
    if not api_key:
        return {'error': 'Google Vision API key not configured'}

    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[1])  # Remove data:image/jpeg;base64,

        # Use requests to call Vision API directly with API key
        vision_url = f'https://vision.googleapis.com/v1/images:annotate?key={api_key}'
        
        image_content = base64.b64encode(image_bytes).decode('utf-8')
        
        request_body = {
            "requests": [{
                "image": {"content": image_content},
                "features": [
                    {"type": "OBJECT_LOCALIZATION", "maxResults": 10},
                    {"type": "TEXT_DETECTION", "maxResults": 1}
                ]
            }]
        }
        
        response = requests.post(vision_url, json=request_body)
        if response.status_code != 200:
            return {'error': f'Vision API error: {response.text}'}
        
        data = response.json()
        if 'responses' not in data or not data['responses']:
            return {'error': 'No response from Vision API'}
        
        result = data['responses'][0]
        
        # Extract objects
        objects = result.get('localizedObjectAnnotations', [])
        media_type = None
        confidence = 0
        for obj in objects:
            name = obj['name'].lower()
            score = obj['score']
            if 'book' in name and score > confidence:
                media_type = 'book'
                confidence = score
            elif ('cd' in name or 'disc' in name) and score > confidence:
                media_type = 'audio'  # Assume CD is audio
                confidence = score
            elif ('dvd' in name or 'bluray' in name or 'video' in name) and score > confidence:
                media_type = 'video'
                confidence = score
        
        # Extract text
        text_result = result.get('textAnnotations', [])
        full_text = text_result[0]['description'] if text_result else ""
        
        # Parse text for fields
        extracted = parse_media_text(full_text, media_type or 'book')
        
        return {
            'media_type': media_type or 'book',
            'title': extracted.get('title'),
            'author': extracted.get('author'),
            'year': extracted.get('year'),
            'full_text': full_text,
            'confidence': confidence
        }

    except Exception as e:
        return {'error': f'Vision API error: {str(e)}'}


def parse_media_text(text, media_type):
    """Parse OCR text to extract title, author, etc. using heuristics."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    extracted = {}

    # Simple heuristics
    for line in lines:
        # Look for author patterns (common names, "by Author")
        if 'by ' in line.lower() or len(line.split()) == 2 and not any(char.isdigit() for char in line):
            if not extracted.get('author'):
                extracted['author'] = line.replace('by ', '').strip()

        # Look for year (4 digits)
        import re
        years = re.findall(r'\b(19|20)\d{2}\b', line)
        if years and not extracted.get('year'):
            extracted['year'] = years[0]

    # Assume first line or longest line is title
    if lines:
        potential_titles = [line for line in lines if len(line) > 10 and not line.lower().startswith(('isbn', 'by ', 'copyright'))]
        if potential_titles:
            extracted['title'] = max(potential_titles, key=len)

    return extracted


@app.route('/scan')
def scan_ui():
    """Render photo capture UI."""
    return render_template('scan.html')


@app.route('/process_image', methods=['POST'])
def process_image():
    """API endpoint: accepts JSON { image: 'data:image/jpeg;base64,...' } and returns extracted metadata JSON."""
    data = request.get_json(force=True)
    image_data = data.get('image') if data else None
    if not image_data:
        return ({'error': 'image required'}, 400)

    try:
        meta = process_image_for_media(image_data)
        if 'error' in meta:
            return ({'error': meta['error']}, 500)

        # Normalize response fields to form-compatible keys
        response = {
            'media_type': meta.get('media_type'),
            'title': meta.get('title'),
            'year': meta.get('year'),
            'notes': f"OCR Text: {meta.get('full_text', '')}",
            'author': meta.get('author'),
            'confidence': meta.get('confidence'),
        }
        return (response, 200)
    except Exception as e:
        return ({'error': f'Processing error: {str(e)}'}, 500)


@app.route('/lookup_barcode', methods=['POST'])
def lookup_barcode():
    """API endpoint: accepts JSON { barcode: '...' } and returns metadata JSON."""
    data = request.get_json(force=True)
    barcode = data.get('barcode') if data else None
    if not barcode:
        return ({'error': 'barcode required'}, 400)

    try:
        meta = detect_and_lookup(barcode)
        if not meta:
            return ({'error': 'No metadata found for barcode', 'barcode': barcode}, 404)
        # Normalize response fields to form-compatible keys
        response = {
            'barcode': barcode,
            'media_type': meta.get('media_type'),
            'title': meta.get('title'),
            'year': meta.get('year'),
            'notes': None,
            'author': meta.get('author') or meta.get('artist'),
            'isbn': meta.get('isbn'),
            'publisher': meta.get('publisher'),
            'page_count': None,
            'physical_description': None,
            'book_genre': meta.get('genre') if meta.get('media_type') == 'book' else None,
            'artist': meta.get('artist') if meta.get('media_type') == 'audio' else None,
            'album': None,
            'track_count': None,
            'audio_format': None,
            'audio_genre': None,
            'director': meta.get('director') if meta.get('media_type') == 'video' else None,
            'runtime_minutes': None,
            'rating': None,
            'video_format': None,
            'video_genre': None,
        }
        return (response, 200)
    except Exception as e:
        return ({'error': f'Lookup error: {str(e)}'}, 500)

# --- Add forms ---
@app.route('/add/book', methods=['GET', 'POST'])
def add_book():
    """Add a new book: insert into media_item then book_details."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        year = request.form.get('year') or None
        notes = request.form.get('notes')

        if not title:
            flash('Title is required.', 'danger')
            return redirect(url_for('add_book'))

        item = MediaItem(title=title, media_type='book', year=(int(year) if year else None), notes=notes)
        db.session.add(item)
        db.session.commit()

        details = BookDetails(
            id=item.id,
            author=request.form.get('author'),
            isbn=request.form.get('isbn'),
            publisher=request.form.get('publisher'),
            page_count=(int(request.form.get('page_count')) if request.form.get('page_count') else None),
            physical_description=request.form.get('physical_description'),
            genre=request.form.get('genre'),
        )
        db.session.add(details)
        db.session.commit()
        flash('Book added successfully.', 'success')
        return redirect(url_for('view_media', item_id=item.id))

    return render_template('add_book.html')


@app.route('/add/audio', methods=['GET', 'POST'])
def add_audio():
    """Add a new audio item."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Title is required.', 'danger')
            return redirect(url_for('add_audio'))

        item = MediaItem(title=title, media_type='audio', year=(int(request.form.get('year')) if request.form.get('year') else None), notes=request.form.get('notes'))
        db.session.add(item)
        db.session.commit()

        details = AudioDetails(
            id=item.id,
            artist=request.form.get('artist'),
            album=request.form.get('album'),
            track_count=(int(request.form.get('track_count')) if request.form.get('track_count') else None),
            format=request.form.get('format'),
            genre=request.form.get('genre'),
        )
        db.session.add(details)
        db.session.commit()
        flash('Audio item added successfully.', 'success')
        return redirect(url_for('view_media', item_id=item.id))

    return render_template('add_audio.html')


@app.route('/add/video', methods=['GET', 'POST'])
def add_video():
    """Add a new video item."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Title is required.', 'danger')
            return redirect(url_for('add_video'))

        item = MediaItem(title=title, media_type='video', year=(int(request.form.get('year')) if request.form.get('year') else None), notes=request.form.get('notes'))
        db.session.add(item)
        db.session.commit()

        details = VideoDetails(
            id=item.id,
            director=request.form.get('director'),
            runtime_minutes=(int(request.form.get('runtime_minutes')) if request.form.get('runtime_minutes') else None),
            rating=request.form.get('rating'),
            format=request.form.get('format'),
            genre=request.form.get('genre'),
        )
        db.session.add(details)
        db.session.commit()
        flash('Video item added successfully.', 'success')
        return redirect(url_for('view_media', item_id=item.id))

    return render_template('add_video.html')


# --- Edit routes ---
@app.route('/edit/book/<int:item_id>', methods=['GET', 'POST'])
def edit_book(item_id):
    """Edit an existing book (media_item + book_details)."""
    item = MediaItem.query.get_or_404(item_id)
    details = BookDetails.query.get(item_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Title is required.', 'danger')
            return redirect(url_for('edit_book', item_id=item_id))

        item.title = title
        item.year = (int(request.form.get('year')) if request.form.get('year') else None)
        item.notes = request.form.get('notes')

        if not details:
            details = BookDetails(id=item.id)
            db.session.add(details)

        details.author = request.form.get('author')
        details.isbn = request.form.get('isbn')
        details.publisher = request.form.get('publisher')
        details.page_count = (int(request.form.get('page_count')) if request.form.get('page_count') else None)
        details.physical_description = request.form.get('physical_description')
        details.genre = request.form.get('genre')

        db.session.commit()
        flash('Book updated successfully.', 'success')
        return redirect(url_for('view_media', item_id=item.id))

    return render_template('edit_book.html', item=item, details=details)


@app.route('/edit/audio/<int:item_id>', methods=['GET', 'POST'])
def edit_audio(item_id):
    """Edit an existing audio item."""
    item = MediaItem.query.get_or_404(item_id)
    details = AudioDetails.query.get(item_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Title is required.', 'danger')
            return redirect(url_for('edit_audio', item_id=item_id))

        item.title = title
        item.year = (int(request.form.get('year')) if request.form.get('year') else None)
        item.notes = request.form.get('notes')

        if not details:
            details = AudioDetails(id=item.id)
            db.session.add(details)

        details.artist = request.form.get('artist')
        details.album = request.form.get('album')
        details.track_count = (int(request.form.get('track_count')) if request.form.get('track_count') else None)
        details.format = request.form.get('format')
        details.genre = request.form.get('genre')

        db.session.commit()
        flash('Audio updated successfully.', 'success')
        return redirect(url_for('view_media', item_id=item.id))

    return render_template('edit_audio.html', item=item, details=details)


@app.route('/edit/video/<int:item_id>', methods=['GET', 'POST'])
def edit_video(item_id):
    """Edit an existing video item."""
    item = MediaItem.query.get_or_404(item_id)
    details = VideoDetails.query.get(item_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Title is required.', 'danger')
            return redirect(url_for('edit_video', item_id=item_id))

        item.title = title
        item.year = (int(request.form.get('year')) if request.form.get('year') else None)
        item.notes = request.form.get('notes')

        if not details:
            details = VideoDetails(id=item.id)
            db.session.add(details)

        details.director = request.form.get('director')
        details.runtime_minutes = (int(request.form.get('runtime_minutes')) if request.form.get('runtime_minutes') else None)
        details.rating = request.form.get('rating')
        details.format = request.form.get('format')
        details.genre = request.form.get('genre')

        db.session.commit()
        flash('Video updated successfully.', 'success')
        return redirect(url_for('view_media', item_id=item.id))

    return render_template('edit_video.html', item=item, details=details)


# --- CSV Upload ---
@app.route('/upload-csv', methods=['GET', 'POST'])
def upload_csv():
    """Upload a CSV file to bulk add media items."""
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(url_for('upload_csv'))
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('upload_csv'))
        
        if not file.filename.endswith('.csv'):
            flash('File must be a CSV.', 'danger')
            return redirect(url_for('upload_csv'))
        
        try:
            stream = io.StringIO(file.read().decode('utf-8'), newline=None)
            reader = csv.DictReader(stream)
            
            added_count = 0
            for row in reader:
                title = row.get('title', '').strip()
                media_type = row.get('media_type', '').strip()
                
                # Only title and media_type are required
                if not title or not media_type:
                    continue
                
                # Create media_item
                item = MediaItem(
                    title=title,
                    media_type=media_type,
                    year=int(row.get('year')) if row.get('year') else None,
                    notes=row.get('notes', '').strip() or None,
                    date_added=date.today()
                )
                db.session.add(item)
                db.session.flush()  # Get the ID without committing yet
                
                # Create type-specific details
                if media_type.lower() == 'book':
                    details = BookDetails(
                        id=item.id,
                        author=row.get('author', '').strip() or None,
                        isbn=row.get('isbn', '').strip() or None,
                        publisher=row.get('publisher', '').strip() or None,
                        page_count=int(row.get('page_count')) if row.get('page_count') else None,
                        physical_description=row.get('physical_description', '').strip() or None,
                        genre=row.get('book_genre', '').strip() or None,
                    )
                    db.session.add(details)
                elif media_type.lower() == 'audio':
                    details = AudioDetails(
                        id=item.id,
                        artist=row.get('artist', '').strip() or None,
                        album=row.get('album', '').strip() or None,
                        track_count=int(row.get('track_count')) if row.get('track_count') else None,
                        format=row.get('audio_format', '').strip() or None,
                        genre=row.get('audio_genre', '').strip() or None,
                    )
                    db.session.add(details)
                elif media_type.lower() == 'video':
                    details = VideoDetails(
                        id=item.id,
                        director=row.get('director', '').strip() or None,
                        runtime_minutes=int(row.get('runtime_minutes')) if row.get('runtime_minutes') else None,
                        rating=row.get('rating', '').strip() or None,
                        format=row.get('video_format', '').strip() or None,
                        genre=row.get('video_genre', '').strip() or None,
                    )
                    db.session.add(details)
                
                added_count += 1
            
            db.session.commit()
            flash(f'{added_count} item(s) added successfully.', 'success')
            return redirect(url_for('list_media'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing CSV: {str(e)}', 'danger')
            return redirect(url_for('upload_csv'))
    
    return render_template('upload_csv.html')


if __name__ == '__main__':
    # Create tables if running locally with sqlite fallback
    with app.app_context():
        db.create_all()
    app.run(debug=True)

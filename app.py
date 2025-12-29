from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date
import os
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
    """List all media items with search and sort. Query params: q (search), sort_by (title, type, year, genre)."""
    q = request.args.get('q', '').strip()
    sort_by = request.args.get('sort_by', 'date').strip()
    
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
    if sort_by == 'title':
        items = items.order_by(MediaItem.title.asc())
    elif sort_by == 'type':
        items = items.order_by(MediaItem.media_type.asc())
    elif sort_by == 'year':
        items = items.order_by(MediaItem.year.desc())
    else:
        # Default: by date added (newest first)
        items = items.order_by(MediaItem.date_added.desc())
    
    items = items.all()
    return render_template('list_media.html', items=items, q=q, sort_by=sort_by)


@app.route('/media/<int:item_id>')
def view_media(item_id):
    """Detail view for a single media item."""
    item = MediaItem.query.get_or_404(item_id)
    return render_template('view_media.html', item=item)


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


if __name__ == '__main__':
    # Create tables if running locally with sqlite fallback
    with app.app_context():
        db.create_all()
    app.run(debug=True)

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from routes.auth import login_required, get_current_user
from database import db
from PIL import Image
import os
import uuid
from datetime import datetime

media_bp = Blueprint('media', __name__)

def allowed_file(filename, file_type):
    """Check if file extension is allowed"""
    from config import Config
    
    if file_type == 'image':
        allowed_extensions = Config.ALLOWED_IMAGE_EXTENSIONS
    elif file_type == 'video':
        allowed_extensions = Config.ALLOWED_VIDEO_EXTENSIONS
    elif file_type == 'document':
        allowed_extensions = Config.ALLOWED_DOCUMENT_EXTENSIONS
    else:
        return False
    
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_file_type(filename):
    """Determine file type based on extension"""
    from config import Config
    
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if extension in Config.ALLOWED_IMAGE_EXTENSIONS:
        return 'image'
    elif extension in Config.ALLOWED_VIDEO_EXTENSIONS:
        return 'video'
    elif extension in Config.ALLOWED_DOCUMENT_EXTENSIONS:
        return 'document'
    else:
        return 'unknown'

@media_bp.route('/upload/<tournament_id>', methods=['GET', 'POST'])
@login_required
def upload(tournament_id):
    """Upload media files to tournament"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if user has permission to upload
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    if not is_organizer:
        flash('Permission denied', 'error')
        return redirect(url_for('tournament.view', tournament_id=tournament_id))
    
    if request.method == 'POST':
        # Check if files were uploaded
        if 'files[]' not in request.files:
            flash('No files selected', 'error')
            return redirect(request.url)
        
        files = request.files.getlist('files[]')
        uploaded_files = []
        
        for file in files:
            if file and file.filename:
                # Validate file
                file_type = get_file_type(file.filename)
                if not allowed_file(file.filename, file_type):
                    flash(f'File type not allowed: {file.filename}', 'error')
                    continue
                
                # Generate unique filename
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                
                # Determine upload directory
                if file_type == 'image':
                    upload_dir = os.path.join('static', 'uploads', 'images')
                elif file_type == 'video':
                    upload_dir = os.path.join('static', 'uploads', 'videos')
                elif file_type == 'document':
                    upload_dir = os.path.join('static', 'uploads', 'documents')
                else:
                    continue
                
                # Ensure directory exists
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                
                # Process image files (resize if too large)
                if file_type == 'image':
                    try:
                        process_uploaded_image(file_path)
                    except Exception as e:
                        print(f"Error processing image: {e}")
                
                # Save file info to database
                file_data = {
                    'tournament_id': tournament_id,
                    'uploaded_by': session['user_id'],
                    'title': request.form.get('title', filename),
                    'description': request.form.get('description', ''),
                    'file_name': filename,
                    'file_path': file_path.replace('\\', '/'),  # Normalize path separators
                    'file_type': file_type,
                    'file_size': os.path.getsize(file_path),
                    'mime_type': file.mimetype or 'application/octet-stream',
                    'is_featured': request.form.get('is_featured') == 'on'
                }
                
                # Mock database save (in real app, save to Supabase)
                file_data['id'] = str(uuid.uuid4())
                file_data['created_at'] = datetime.now().isoformat()
                
                uploaded_files.append(file_data)
        
        if uploaded_files:
            flash(f'Successfully uploaded {len(uploaded_files)} file(s)', 'success')
        else:
            flash('No files were uploaded', 'error')
        
        return redirect(url_for('media.gallery', tournament_id=tournament_id))
    
    return render_template('media/upload.html', tournament=tournament)

@media_bp.route('/gallery/<tournament_id>')
def gallery(tournament_id):
    """View tournament media gallery"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get media files (mock data for now)
    media_files = get_tournament_media(tournament_id)
    
    # Group by type
    images = [f for f in media_files if f['file_type'] == 'image']
    videos = [f for f in media_files if f['file_type'] == 'video']
    documents = [f for f in media_files if f['file_type'] == 'document']
    
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    
    return render_template('media/gallery.html', 
                         tournament=tournament,
                         images=images,
                         videos=videos,
                         documents=documents,
                         is_organizer=is_organizer)

@media_bp.route('/file/<file_id>')
def view_file(file_id):
    """View individual media file"""
    # Get file details (mock for now)
    file_data = get_media_file(file_id)
    if not file_data:
        flash('File not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    tournament = db.get_tournament_by_id(file_data['tournament_id'])
    
    return render_template('media/view_file.html', 
                         file=file_data,
                         tournament=tournament)

@media_bp.route('/delete/<file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    """Delete media file"""
    file_data = get_media_file(file_id)
    if not file_data:
        return jsonify({'success': False, 'error': 'File not found'})
    
    tournament = db.get_tournament_by_id(file_data['tournament_id'])
    if not tournament or session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    try:
        # Delete physical file
        if os.path.exists(file_data['file_path']):
            os.remove(file_data['file_path'])
        
        # Delete from database (mock for now)
        # In real app: delete from Supabase
        
        return jsonify({'success': True, 'message': 'File deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error deleting file: {str(e)}'})

@media_bp.route('/update/<file_id>', methods=['POST'])
@login_required
def update_file(file_id):
    """Update file metadata"""
    file_data = get_media_file(file_id)
    if not file_data:
        return jsonify({'success': False, 'error': 'File not found'})
    
    tournament = db.get_tournament_by_id(file_data['tournament_id'])
    if not tournament or session.get('user_id') != tournament.get('organizer_id'):
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    # Update file metadata
    update_data = {
        'title': request.form.get('title', '').strip(),
        'description': request.form.get('description', '').strip(),
        'is_featured': request.form.get('is_featured') == 'on'
    }
    
    # Update in database (mock for now)
    file_data.update(update_data)
    
    return jsonify({'success': True, 'file': file_data})

@media_bp.route('/serve/<path:filename>')
def serve_media(filename):
    """Serve uploaded media files"""
    # Security: Only serve files from uploads directory
    safe_path = secure_filename(filename)
    
    # Try to find file in upload directories
    upload_dirs = ['static/uploads/images', 'static/uploads/videos', 'static/uploads/documents']
    
    for upload_dir in upload_dirs:
        file_path = os.path.join(upload_dir, safe_path)
        if os.path.exists(file_path):
            return send_from_directory(upload_dir, safe_path)
    
    # File not found
    return "File not found", 404

@media_bp.route('/news/<tournament_id>', methods=['GET', 'POST'])
@login_required
def manage_news(tournament_id):
    """Manage tournament news and updates"""
    tournament = db.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    is_organizer = session.get('user_id') == tournament.get('organizer_id')
    if not is_organizer:
        flash('Permission denied', 'error')
        return redirect(url_for('tournament.view', tournament_id=tournament_id))
    
    if request.method == 'POST':
        # Create news update
        news_data = {
            'tournament_id': tournament_id,
            'author_id': session['user_id'],
            'title': request.form.get('title', '').strip(),
            'content': request.form.get('content', '').strip(),
            'is_published': request.form.get('is_published') == 'on'
        }
        
        if not news_data['title'] or not news_data['content']:
            flash('Title and content are required', 'error')
        else:
            # Save to database (mock for now)
            news_data['id'] = str(uuid.uuid4())
            news_data['created_at'] = datetime.now().isoformat()
            news_data['published_at'] = datetime.now().isoformat() if news_data['is_published'] else None
            
            flash('News update created successfully!', 'success')
            return redirect(url_for('media.manage_news', tournament_id=tournament_id))
    
    # Get existing news updates (mock data)
    news_updates = get_tournament_news(tournament_id)
    
    return render_template('media/news.html', 
                         tournament=tournament,
                         news_updates=news_updates)

# Helper functions
def process_uploaded_image(file_path):
    """Process uploaded image (resize if too large)"""
    try:
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Resize if image is too large
            max_size = (1920, 1080)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(file_path, 'JPEG', quality=85, optimize=True)
    except Exception as e:
        print(f"Error processing image {file_path}: {e}")

def get_tournament_media(tournament_id):
    """Get all media files for a tournament"""
    # Mock media files
    return [
        {
            'id': 'media_1',
            'tournament_id': tournament_id,
            'title': 'Team Photo',
            'description': 'Team photo before the match',
            'file_name': 'team_photo.jpg',
            'file_path': 'static/uploads/images/team_photo.jpg',
            'file_type': 'image',
            'file_size': 2048000,
            'is_featured': True,
            'created_at': datetime.now().isoformat()
        },
        {
            'id': 'media_2',
            'tournament_id': tournament_id,
            'title': 'Match Highlights',
            'description': 'Best moments from the final',
            'file_name': 'highlights.mp4',
            'file_path': 'static/uploads/videos/highlights.mp4',
            'file_type': 'video',
            'file_size': 50000000,
            'is_featured': False,
            'created_at': datetime.now().isoformat()
        }
    ]

def get_media_file(file_id):
    """Get individual media file"""
    # Mock file data
    return {
        'id': file_id,
        'tournament_id': 'tournament_123',
        'title': 'Sample File',
        'description': 'A sample media file',
        'file_name': 'sample.jpg',
        'file_path': 'static/uploads/images/sample.jpg',
        'file_type': 'image',
        'file_size': 1024000,
        'is_featured': False,
        'created_at': datetime.now().isoformat()
    }

def get_tournament_news(tournament_id):
    """Get tournament news updates"""
    # Mock news data
    return [
        {
            'id': 'news_1',
            'tournament_id': tournament_id,
            'title': 'Tournament Begins Tomorrow!',
            'content': 'All teams are ready and the tournament starts tomorrow at 10 AM.',
            'author_name': 'Tournament Admin',
            'is_published': True,
            'published_at': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat()
        },
        {
            'id': 'news_2',
            'tournament_id': tournament_id,
            'title': 'Registration Update',
            'content': 'Registration deadline has been extended by one week.',
            'author_name': 'Tournament Admin',
            'is_published': True,
            'published_at': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat()
        }
    ]

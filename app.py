import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import mimetypes
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip', 'rar', 'mp3', 'mp4', 'avi'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Simple JSON database for file metadata
DATABASE_FILE = 'file_database.json'

def load_database():
    """Load file metadata from JSON database"""
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_database(db):
    """Save file metadata to JSON database"""
    with open(DATABASE_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size_mb(filepath):
    """Get file size in MB"""
    size_bytes = os.path.getsize(filepath)
    return round(size_bytes / (1024 * 1024), 2)

@app.route('/')
def index():
    """Main page - show uploaded files and search"""
    db = load_database()
    search_query = request.args.get('search', '').strip()
    
    files = []
    for file_id, file_info in db.items():
        if search_query:
            # Search in filename, original name, and description
            search_text = f"{file_info['original_name']} {file_info.get('description', '')}".lower()
            if search_query.lower() not in search_text:
                continue
        files.append({
            'id': file_id,
            'original_name': file_info['original_name'],
            'filename': file_info['filename'],
            'upload_date': file_info['upload_date'],
            'file_size': file_info['file_size'],
            'file_type': file_info['file_type'],
            'description': file_info.get('description', 'No description')
        })
    
    # Sort by upload date (newest first)
    files.sort(key=lambda x: x['upload_date'], reverse=True)
    
    return render_template('index.html', files=files, search_query=search_query)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload page"""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        description = request.form.get('description', '').strip()
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Save file
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # Get file info
            file_size = get_file_size_mb(filepath)
            file_type = mimetypes.guess_type(filepath)[0] or 'Unknown'
            
            # Save metadata to database
            db = load_database()
            file_id = str(uuid.uuid4())
            db[file_id] = {
                'original_name': original_filename,
                'filename': unique_filename,
                'upload_date': datetime.now().isoformat(),
                'file_size': file_size,
                'file_type': file_type,
                'description': description
            }
            save_database(db)
            
            flash(f'File "{original_filename}" uploaded successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid file type. Allowed types: ' + ', '.join(ALLOWED_EXTENSIONS), 'error')
    
    return render_template('upload.html')

@app.route('/download/<file_id>')
def download(file_id):
    """Download file by ID"""
    db = load_database()
    
    if file_id not in db:
        flash('File not found', 'error')
        return redirect(url_for('index'))
    
    file_info = db[file_id]
    filename = file_info['filename']
    original_name = file_info['original_name']
    
    try:
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            filename, 
            as_attachment=True,
            download_name=original_name
        )
    except FileNotFoundError:
        flash('File not found on disk', 'error')
        return redirect(url_for('index'))

@app.route('/delete/<file_id>', methods=['POST'])
def delete(file_id):
    """Delete file by ID"""
    db = load_database()
    
    if file_id not in db:
        flash('File not found', 'error')
        return redirect(url_for('index'))
    
    file_info = db[file_id]
    filename = file_info['filename']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Delete file from disk
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        flash(f'Error deleting file: {str(e)}', 'error')
        return redirect(url_for('index'))
    
    # Remove from database
    del db[file_id]
    save_database(db)
    
    flash('File deleted successfully', 'success')
    return redirect(url_for('index'))

@app.route('/api/stats')
def api_stats():
    """API endpoint for site statistics"""
    db = load_database()
    
    total_files = len(db)
    total_size = sum(file_info['file_size'] for file_info in db.values())
    
    file_types = {}
    for file_info in db.values():
        ext = file_info['original_name'].rsplit('.', 1)[-1].lower()
        file_types[ext] = file_types.get(ext, 0) + 1
    
    return jsonify({
        'total_files': total_files,
        'total_size_mb': round(total_size, 2),
        'file_types': file_types
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)

import os
import uuid
from flask import Flask, request, render_template, send_file, jsonify, abort
from werkzeug.utils import secure_filename
from datetime import datetime
import json

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB max file size
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3', 'zip', 'rar', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# File metadata storage (in production, use a database)
METADATA_FILE = 'file_metadata.json'

def load_metadata():
    """Load file metadata from JSON file"""
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_metadata(metadata):
    """Save file metadata to JSON file"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size_mb(filepath):
    """Get file size in MB"""
    return round(os.path.getsize(filepath) / (1024 * 1024), 2)

@app.route('/')
def index():
    """Main page showing uploaded files"""
    metadata = load_metadata()
    files = []
    
    for file_id, info in metadata.items():
        filepath = os.path.join(UPLOAD_FOLDER, info['stored_filename'])
        if os.path.exists(filepath):
            files.append({
                'id': file_id,
                'original_name': info['original_name'],
                'upload_date': info['upload_date'],
                'size_mb': info['size_mb']
            })
    
    # Sort by upload date (newest first)
    files.sort(key=lambda x: x['upload_date'], reverse=True)
    
    return render_template('index.html', files=files)

@app.route('/upload')
def upload_page():
    """Upload page"""
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        stored_filename = f"{file_id}.{file_extension}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
        
        # Save file
        file.save(filepath)
        
        # Store metadata
        metadata = load_metadata()
        metadata[file_id] = {
            'original_name': original_filename,
            'stored_filename': stored_filename,
            'upload_date': datetime.now().isoformat(),
            'size_mb': get_file_size_mb(filepath)
        }
        save_metadata(metadata)
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': original_filename
        })
        
    except Exception as e:
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/download/<file_id>')
def download_file(file_id):
    """Download file by ID"""
    metadata = load_metadata()
    
    if file_id not in metadata:
        abort(404)
    
    file_info = metadata[file_id]
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file_info['stored_filename'])
    
    if not os.path.exists(filepath):
        abort(404)
    
    return send_file(filepath, 
                     as_attachment=True, 
                     download_name=file_info['original_name'])

@app.route('/search')
def search_files():
    """Search files by name"""
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
    
    metadata = load_metadata()
    results = []
    
    for file_id, info in metadata.items():
        if query in info['original_name'].lower():
            filepath = os.path.join(UPLOAD_FOLDER, info['stored_filename'])
            if os.path.exists(filepath):
                results.append({
                    'id': file_id,
                    'original_name': info['original_name'],
                    'upload_date': info['upload_date'],
                    'size_mb': info['size_mb']
                })
    
    return jsonify(results)

if __name__ == '__main__':
    # For Tor compatibility, bind to all interfaces
    app.run(host='0.0.0.0', port=5000, debug=False)

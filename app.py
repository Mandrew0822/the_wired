import os
import uuid
from datetime import datetime
from flask import Flask, request, render_template, send_from_directory, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import mimetypes

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# File metadata storage (in production, use a database)
files_metadata = {}

def get_file_size_string(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            original_filename = secure_filename(file.filename)
            file_extension = os.path.splitext(original_filename)[1]
            stored_filename = f"{file_id}{file_extension}"
            
            # Save file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
            file.save(file_path)
            
            # Store metadata
            file_size = os.path.getsize(file_path)
            files_metadata[file_id] = {
                'original_name': original_filename,
                'stored_name': stored_filename,
                'upload_time': datetime.now().isoformat(),
                'size': file_size,
                'size_string': get_file_size_string(file_size),
                'mime_type': mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
            }
            
            return jsonify({
                'success': True, 
                'file_id': file_id,
                'filename': original_filename,
                'size': get_file_size_string(file_size)
            })
    
    return render_template('upload.html')

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
    
    results = []
    for file_id, metadata in files_metadata.items():
        if query in metadata['original_name'].lower():
            results.append({
                'id': file_id,
                'name': metadata['original_name'],
                'size': metadata['size_string'],
                'upload_time': metadata['upload_time'][:10],  # Just the date
                'mime_type': metadata['mime_type']
            })
    
    return jsonify(results[:50])  # Limit to 50 results

@app.route('/download/<file_id>')
def download(file_id):
    if file_id not in files_metadata:
        return "File not found", 404
    
    metadata = files_metadata[file_id]
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        metadata['stored_name'],
        as_attachment=True,
        download_name=metadata['original_name']
    )

@app.route('/files')
def list_files():
    """API endpoint to list all files"""
    results = []
    for file_id, metadata in files_metadata.items():
        results.append({
            'id': file_id,
            'name': metadata['original_name'],
            'size': metadata['size_string'],
            'upload_time': metadata['upload_time'][:10],
            'mime_type': metadata['mime_type']
        })
    
    # Sort by upload time, newest first
    results.sort(key=lambda x: x['upload_time'], reverse=True)
    return jsonify(results[:100])  # Limit to 100 most recent files

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

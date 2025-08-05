import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
import mimetypes

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Configuration
UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 512 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip', 'mp3', 'mp4', 'avi'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_info(filename):
    """Get file information including size and upload date"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        stat = os.stat(filepath)
        return {
            'name': filename,
            'size': stat.st_size,
            'upload_date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'size_mb': round(stat.st_size / (1024 * 1024), 2)
        }
    return None

def search_files(query):
    """Search for files by name"""
    files = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if query.lower() in filename.lower():
                file_info = get_file_info(filename)
                if file_info:
                    files.append(file_info)
    return files

@app.route('/')
def index():
    # Get all files for display
    files = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_info = get_file_info(filename)
            if file_info:
                files.append(file_info)
    
    # Sort by upload date (newest first)
    files.sort(key=lambda x: x['upload_date'], reverse=True)
    
    return render_template('index.html', files=files)

@app.route('/upload')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Secure the filename and add timestamp to avoid conflicts
        original_filename = secure_filename(file.filename)
        name, ext = os.path.splitext(original_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}{ext}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        flash(f'File "{original_filename}" uploaded successfully!')
        return redirect(url_for('index'))
    else:
        flash('File type not allowed. Allowed types: ' + ', '.join(ALLOWED_EXTENSIONS))
        return redirect(request.url)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    files = []
    
    if query:
        files = search_files(query)
    
    return jsonify({'files': files, 'query': query})

@app.route('/download/<filename>')
def download_file(filename):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            flash('File not found')
            return redirect(url_for('index'))
    except Exception as e:
        flash('Error downloading file')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

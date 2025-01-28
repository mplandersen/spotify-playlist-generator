# app.py
from flask import Flask, render_template, request, flash, redirect, url_for
import os
from spotify_playlist_generator import SpotifyPlaylistGenerator
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for flashing messages

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['file']
        playlist_name = request.form.get('playlist_name', 'My Generated Playlist')
        
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Save the uploaded file
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Generate playlist
                generator = SpotifyPlaylistGenerator()
                results = generator.process_csv_and_create_playlist(
                    playlist_name=playlist_name,
                    csv_path=filepath
                )
                
                # Clean up the uploaded file
                os.remove(filepath)
                
                return render_template(
                    'index.html',
                    results=results,
                    playlist_url=results.get('playlist_url'),
                    total_tracks_found=results.get('total_tracks_found', 0),
                    failed_tracks=results.get('failed_tracks', [])
                )
                
            except Exception as e:
                flash(f'Error: {str(e)}')
                return redirect(request.url)
                
        else:
            flash('Invalid file type. Please upload a CSV file.')
            return redirect(request.url)
            
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
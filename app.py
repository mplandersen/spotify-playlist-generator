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
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['file']
        playlist_name = request.form.get('playlist_name', 'My Generated Playlist')
        min_rating = float(request.form.get('min_rating', 0))
        min_year = request.form.get('min_year')
        max_year = request.form.get('max_year')
        
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(filepath)
                generator = SpotifyPlaylistGenerator()
                results = generator.process_csv_and_create_playlist(
                    playlist_name=playlist_name,
                    csv_path=filepath,
                    min_rating=min_rating,
                    min_year=min_year,
                    max_year=max_year
                )
                
                os.remove(filepath)
                
                return render_template(
                    'index.html',
                    results=results
                )
                
            except Exception as e:
                flash(f'Error: {str(e)}')
                return redirect(request.url)
                
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
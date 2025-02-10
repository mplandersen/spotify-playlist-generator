from flask import Flask, render_template, request, flash, redirect, url_for
from flask_socketio import SocketIO, emit
import os
from spotify_playlist_generator import SpotifyPlaylistGenerator
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
socketio = SocketIO(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_update(message):
    """Send a progress update through SocketIO."""
    socketio.emit('processing_update', {'message': message})

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handle the main page and form submission."""
    if request.method == 'POST':
        send_update("Starting playlist generation...")
        
        # Check if a file was actually uploaded
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        # Get and validate form data
        playlist_name = request.form.get('playlist_name', 'My Generated Playlist')
        send_update(f"Creating playlist: {playlist_name}")
        
        try:
            # Parse and validate numeric inputs with proper error handling
            min_rating = float(request.form.get('min_rating', 0))
            min_year = int(request.form.get('min_year')) if request.form.get('min_year') else None
            max_year = int(request.form.get('max_year')) if request.form.get('max_year') else None
            
            if file and allowed_file(file.filename):
                # Save uploaded file securely
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                send_update("Processing CSV file...")
                
                # Initialize playlist generator and process the file
                generator = SpotifyPlaylistGenerator()
                results = generator.process_csv_and_create_playlist(
                    playlist_name=playlist_name,
                    csv_path=filepath,
                    min_rating=min_rating,
                    min_year=min_year,
                    max_year=max_year
                )
                
                # Clean up the uploaded file
                os.remove(filepath)
                
                # Send final update and render results
                send_update("Playlist generation complete!")
                return render_template('index.html', results=results)
            
            else:
                flash('Invalid file type. Please upload a CSV file.')
                return redirect(request.url)
                
        except ValueError as ve:
            # Handle validation errors for numeric inputs
            flash(f'Invalid input: {str(ve)}')
            return redirect(request.url)
            
        except Exception as e:
            # Handle any other errors that might occur during processing
            flash(f'An error occurred: {str(e)}')
            return redirect(request.url)
    
    # GET request - show the main form
    return render_template('index.html')

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file size too large errors"""
    flash('The file is too large. Please try a smaller file.')
    return redirect(url_for('index')), 413

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors"""
    flash('An internal server error occurred. Please try again later.')
    return redirect(url_for('index')), 500

if __name__ == '__main__':
    # Run the application with SocketIO instead of the standard Flask server
    socketio.run(app, debug=True)
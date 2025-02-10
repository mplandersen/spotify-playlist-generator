from collections import Counter
from datetime import datetime
import csv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

class SpotifyPlaylistGenerator:
    def __init__(self):
        """Initialize Spotify client with proper authentication."""
        load_dotenv()  # Load environment variables from .env file
        
        # Set up Spotify authentication
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
            scope='playlist-modify-public'
        ))
        
        # Get the authenticated user's ID
        self.user_id = self.sp.current_user()['id']

    def create_playlist(self, name):
        """Create a new Spotify playlist and return its ID."""
        playlist = self.sp.user_playlist_create(
            user=self.user_id,
            name=name,
            public=True,
            description='Generated from RateYourMusic ratings'
        )
        return playlist['id']

    def search_album(self, artist, album_name):
        """Search for an album on Spotify and return the first result."""
        query = f"artist:{artist} album:{album_name}"
        results = self.sp.search(q=query, type='album', limit=1)
        return results

    def calculate_statistics(self, track_data, ratings):
        """Calculate statistics about the generated playlist.
        
        Args:
            track_data: List of dictionaries containing track information
            ratings: List of numerical ratings
            
        Returns:
            Dictionary containing various statistics about the playlist
        """
        stats = {}
        
        # Most added artists
        artist_counts = Counter(track['artist'] for track in track_data)
        stats['top_artists'] = artist_counts.most_common(5)
        
        # Tracks by decade
        decades = Counter()
        for track in track_data:
            if track.get('year'):
                decade = (int(track['year']) // 10) * 10
                decades[decade] = decades.get(decade, 0) + 1
        stats['decades'] = sorted(decades.items())
        
        # Average rating
        if ratings:
            stats['avg_rating'] = sum(ratings) / len(ratings)
        
        return stats

    def process_csv_and_create_playlist(self, playlist_name, csv_path, min_rating=0, min_year=None, max_year=None):
        """Process the CSV file and create a Spotify playlist.
        
        Args:
            playlist_name: Name for the new playlist
            csv_path: Path to the CSV file
            min_rating: Minimum rating threshold (0-10)
            min_year: Earliest release year to include (optional)
            max_year: Latest release year to include (optional)
            
        Returns:
            Dictionary containing results and statistics
        """
        track_ids = []
        failed_albums = []
        processed_albums = 0
        track_data = []
        ratings = []
        
        try:
            # Create the playlist first
            playlist_id = self.create_playlist(playlist_name)
            
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    processed_albums += 1
                    
                    try:
                        # Extract and validate rating
                        rating = float(row.get('Rating', 0))
                        if rating < min_rating:
                            continue
                        
                        # Extract and validate year
                        release_date = row.get('Release_Date', '')
                        try:
                            year = int(release_date.split('/')[-1]) if release_date else None
                        except (ValueError, IndexError):
                            year = None
                            
                        if (min_year and (not year or year < min_year)) or \
                           (max_year and (not year or year > max_year)):
                            continue
                        
                        # Get artist and album name
                        artist = row.get('Last Name', '').strip()
                        album_name = row.get('Title', '').strip()
                        
                        if not artist or not album_name:
                            failed_albums.append(f"{album_name} by {artist} (Missing data)")
                            continue
                        
                        # Search for album on Spotify
                        results = self.search_album(artist, album_name)
                        
                        if results['albums']['items']:
                            album_id = results['albums']['items'][0]['id']
                            album_tracks = self.sp.album_tracks(album_id)
                            new_track_ids = [track['id'] for track in album_tracks['items']]
                            
                            # Store track metadata for statistics
                            for track in album_tracks['items']:
                                track_data.append({
                                    'artist': artist,
                                    'year': year,
                                    'album': album_name
                                })
                            ratings.append(rating)
                            
                            # Add tracks to playlist in batches of 100 (Spotify's limit)
                            if new_track_ids:
                                track_ids.extend(new_track_ids)
                                for i in range(0, len(new_track_ids), 100):
                                    batch = new_track_ids[i:i + 100]
                                    self.sp.playlist_add_items(playlist_id, batch)
                        else:
                            failed_albums.append(f"{album_name} by {artist} (Not found on Spotify)")
                            
                    except Exception as e:
                        failed_albums.append(f"{album_name} by {artist} (Error: {str(e)})")
                        continue
            
            # Calculate statistics
            statistics = self.calculate_statistics(track_data, ratings)
            
            return {
                'playlist_url': f"https://open.spotify.com/playlist/{playlist_id}",
                'total_albums_processed': processed_albums,
                'total_tracks_added': len(track_ids),
                'failed_albums': failed_albums,
                'statistics': statistics
            }
            
        except Exception as e:
            print(f"Fatal error in playlist generation: {str(e)}")
            raise
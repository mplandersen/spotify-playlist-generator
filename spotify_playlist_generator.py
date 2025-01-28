import spotipy
from spotipy.oauth2 import SpotifyOAuth
import csv
import os
from dotenv import load_dotenv

class SpotifyPlaylistGenerator:
    def __init__(self):
        """
        Initialize Spotify client with proper authentication.
        Requires environment variables for Spotify API credentials.
        """
        load_dotenv()  # Load environment variables
        
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=os.getenv('SPOTIFY_CLIENT_ID'),
                client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
                redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
                scope='playlist-modify-public playlist-modify-private'
            )
        )
        
        # Get authenticated user's ID
        self.user_id = self.sp.current_user()['id']

    def search_track(self, song_name, artist):
        """
        Search for a track on Spotify.
        
        :param song_name: Name of the song
        :param artist: Name of the artist
        :return: Spotify track ID if found, None otherwise
        """
        query = f"track:{song_name} artist:{artist}"
        results = self.sp.search(q=query, type='track', limit=1)
        
        if results['tracks']['items']:
            return results['tracks']['items'][0]['id']
        return None

    def create_playlist(self, playlist_name, description=""):
        """
        Create a new Spotify playlist.
        
        :param playlist_name: Name for the new playlist
        :param description: Optional description for the playlist
        :return: Playlist ID
        """
        playlist = self.sp.user_playlist_create(
            user=self.user_id,
            name=playlist_name,
            public=False,
            description=description
        )
        return playlist['id']

    def process_csv_and_create_playlist(self, playlist_name, csv_path, min_rating=0, min_year=None, max_year=None):
        """
        Create playlist from albums that meet rating and year criteria.
        
        :param playlist_name: Name for the new playlist
        :param csv_path: Path to CSV file
        :param min_rating: Minimum rating to include (1-10)
        :param min_year: Earliest year to include
        :param max_year: Latest year to include
        :return: Dictionary with results
        """
        track_ids = []
        failed_albums = []
        
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Check if album meets criteria
                rating = float(row['Rating']) if row['Rating'] else 0
                year = row['Release_Date']
                
                # Skip if doesn't meet rating/year criteria
                if rating < min_rating:
                    continue
                if min_year and year < min_year:
                    continue
                if max_year and year > max_year:
                    continue
                    
                # Get artist name (either localized or original)
                artist = row['Last Name localized'] if row['Last Name localized'] else row['Last Name']
                album_name = row['Title']
                
                try:
                    # Search for album instead of track
                    results = self.sp.search(f"album:{album_name} artist:{artist}", type='album', limit=1)
                    
                    if results['albums']['items']:
                        album_id = results['albums']['items'][0]['id']
                        # Get all tracks from the album
                        album_tracks = self.sp.album_tracks(album_id)
                        track_ids.extend([track['id'] for track in album_tracks['items']])
                    else:
                        failed_albums.append({
                            'album': album_name,
                            'artist': artist,
                            'rating': rating,
                            'year': year
                        })
                except Exception as e:
                    print(f"Error processing {album_name}: {str(e)}")
                    failed_albums.append({
                        'album': album_name,
                        'artist': artist,
                        'rating': rating,
                        'year': year,
                        'error': str(e)
                    })

        return {
            'total_albums_found': len(track_ids),
            'failed_albums': failed_albums,
            'track_ids': track_ids
        }

def main():
    try:
        # Initialize the playlist generator
        generator = SpotifyPlaylistGenerator()
        
        # Define your CSV path and playlist name
        csv_path = "data/rym/example.csv"
        playlist_name = "My Generated Playlist"
        
        # Process CSV and create playlist
        results = generator.process_csv_and_create_playlist(playlist_name, csv_path)
        
        # Print results
        if results['playlist_url']:
            print(f"\nPlaylist created successfully!")
            print(f"Playlist URL: {results['playlist_url']}")
            print(f"Successfully added {results['total_tracks_found']} tracks")
        else:
            print("No tracks were found to create a playlist")
            
        if results['failed_tracks']:
            print(f"\nFailed to find {results['total_tracks_failed']} tracks:")
            for track in results['failed_tracks']:
                print(f"- {track['song']} by {track['artist']}")
                
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
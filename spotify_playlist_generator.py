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

    def process_csv_and_create_playlist(self, playlist_name, csv_path):
        """
        Process the CSV file and create a new Spotify playlist.
        
        :param csv_path: Path to the CSV file
        :param playlist_name: Name for the new playlist
        :return: None
        """
        track_ids = []
        failed_tracks = []
        
        # Read CSV and search for tracks
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                song_name = row['Track_Name']  # Adjust column name as needed
                artist = row['Artist_Name']   # Adjust column name as needed
                
                track_id = self.search_track(song_name, artist)
                
                if track_id:
                    track_ids.append(track_id)
                else:
                    failed_tracks.append({
                        'song': song_name,
                        'artist': artist
                    })
        
        # Create playlist if tracks were found
        if track_ids:
            playlist_id = self.create_playlist(
                playlist_name,
                f"Playlist generated from {csv_path}"
            )
            
            # Add tracks to playlist (Spotify has a 100 track limit per request)
            for i in range(0, len(track_ids), 100):
                batch = track_ids[i:i + 100]
                self.sp.playlist_add_items(playlist_id, batch)
            
            playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
        else:
            playlist_url = None
        
        return {
            'playlist_url': playlist_url,
            'total_tracks_found': len(track_ids),
            'total_tracks_failed': len(failed_tracks),
            'failed_tracks': failed_tracks
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
import spotipy
import spotipy.util as util
import spotipy.oauth2 as oauth2

class Spotify:
    def __init__(self, credentials):
        self.username = credentials['username']
        self.client_id = credentials['client_id']
        self.client_secret = credentials['client_secret']
        self.redirect_uri = credentials['redirect_uri']


    def setup_read(self):
        auth = oauth2.SpotifyClientCredentials(
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        token = auth.get_access_token()
        spotify = spotipy.Spotify(auth=token)
        return spotify

    def setup_write(self):
        scope = 'playlist-modify-public'
        token = util.prompt_for_user_token(self.username, scope, client_id=self.client_id,
                                           client_secret=self.client_secret,
                                           redirect_uri=self.redirect_uri)
        spotify = spotipy.Spotify(auth=token)
        return spotify

from bs4 import BeautifulSoup
import configparser
import requests
import re
import spotipy
import spotipy.util as util
import spotipy.oauth2 as oauth2

# TODO
# do not create new playlist if playlist name exists
# add tracks to existing playlist instead of creating new one
# probably just need spotify_post instead of both spotify and spotify_post
# are there playlists separated by DJ? That's probably better than by day
# check to see if "first hit" is accurate enough. Can try to match album to search hits better (I think it doesn't work right now)
# run script every 24 hours
# refactor some of this garbage

def main(n):
    # web scraping
    print("scraping kalx")

    # spotify interaction
    print("getting spotify")
    spotify, spotify_post, username = set_up_spotify()

    existing_playlist_names = get_playlist_names(spotify, username)
    count = 0

    while count < n:
        text = get_webpage_text(count)
        soup = BeautifulSoup(text, 'html.parser')
        songs_by_playlist = parse_playlists('table', 'sticky-enabled', soup)
        create_playlists(songs_by_playlist, existing_playlist_names, spotify_post, username)
        count += 1

    print('finished!')


def get_webpage_text(count):
    base_url = 'https://www.kalx.berkeley.edu/playlists'
    if not count:
        url = 'https://www.kalx.berkeley.edu/playlists'
    else:
        url = base_url + '?page={}'.format(count)

    resp = requests.get(url, verify=False)
    return resp.text


def parse_playlists(tag, html_class, soup):
    containers = soup.find_all(tag, class_ = html_class)
    all_song_rows = {}
    for container in containers:
        if not container.caption:
            continue
        title = get_playlist_name(container.caption.text)
        all_song_rows[title] = []
        trs = container.find_all('tr')
        for tr in trs:
            song_row = tr.find('td', class_='views-field-nothing')
            if not song_row:
                continue

            song_data = process_song_row(song_row)
            if not song_data:
                continue

            all_song_rows[title].append(song_data)

    return all_song_rows

def get_playlist_name(text):
    return 'KALX: {}'.format(text)

def process_song_row(row):
    song_data = row.text.strip(' \t\n\r').split('-')
    no_quotes = [ re.sub('"', '', s) for s in song_data ]
    stripped = [ s.strip() for s in no_quotes ]
    data = [ re.sub(' ', '+', s) for s in stripped ]

    if not any(re.match('^[a-zA-Z0-9]+$', x) for x in data):
        return None

    if len(data) < 3:
        album =  ''
    else:
        album = data[2]

    return { 'artist': data[0], 'song': data[1], 'album': album }


def set_up_spotify():
    config = configparser.ConfigParser()
    config.read('config.cfg')
    client_id = config.get('SPOTIFY', 'CLIENT_ID')
    client_secret = config.get('SPOTIFY', 'CLIENT_SECRET')
    redirect_uri = config.get('SPOTIFY', 'REDIRECT_URI')
    username = config.get('SPOTIFY', 'USERNAME')
    auth = oauth2.SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    )
    token = auth.get_access_token()
    spotify = spotipy.Spotify(auth=token)
    print('spotify created')

    scope = 'playlist-modify-public'
    token = util.prompt_for_user_token(username, scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
    spotify_post = spotipy.Spotify(auth=token)
    return spotify, spotify_post, username

def get_playlist_names(spotify, username):
    names = []

    playlists = spotify.user_playlists(username)
    for playlist in playlists['items']:
        names.append(playlist['name'])

    return names

def create_playlists(songs_by_playlist, existing_playlist_names, spotify_post, username):
    for playlist_name in songs_by_playlist:
        if playlist_name in existing_playlist_names:
            continue

        create_new_playlist(playlist_name, spotify_post, username)
        playlist_id = create_new_playlist(playlist_name, spotify_post, username)
        track_ids = get_track_ids(songs_by_playlist[playlist_name], spotify_post)
        spotify_post.user_playlist_add_tracks(username, playlist_id, track_ids)



def create_new_playlist(name, spotify, username):
    playlist = spotify.user_playlist_create(username, name, public=True)
    return playlist['id']

def get_track_ids(songs, spotify):
    all_results = []
    for song in songs:

        # .search() defaults to searching for track
        # adding album to the query seems to make it return nothing
        q = "{0} artist:{1}".format(song['song'], song['artist'])

        res = spotify.search(q=q)
        track_id = extract_track_id(res, song['album'])
        if track_id:
            all_results.append(track_id)

    return all_results


def extract_track_id(res, album):
    try:
        items = res['tracks']['items']
        track_id = items[0]['id']
        # check if there's a better match with the album name
        # spaced_album = re.sub('+', ' ', album)
        # for item in items:
        #     if item['name'] in spaced_album:
        #         track_id = item['id']


    except:
        return None

    return track_id


main(10)

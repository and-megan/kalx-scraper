from bs4 import BeautifulSoup
import configparser
import requests
import re

from services.spotify import Spotify


# TODO
# do not create new playlist if playlist name exists
# add tracks to existing playlist instead of creating new one
# probably just need spotify_post instead of both spotify and spotify_post
# are there playlists separated by DJ? That's probably better than by day
# check to see if "first hit" is accurate enough. Can try to match album to search hits better (I think it doesn't work right now)
# run script every 24 hours
# refactor some of this garbage

def main(n):
    # spotify interaction
    print("setting up spotify")

    creds = parse_config()
    spotify_service = Spotify(creds)
    spotify_read = spotify_service.setup_read()
    spotify_post = spotify_service.setup_write()

    print("getting existing spotify playlist names")
    existing_playlists = get_existing_playlist_data(spotify_read, spotify_service.username)

    count = 0
    # web scraping
    print("scraping kalx")
    while count < n:
        text = get_webpage_text(count)
        soup = BeautifulSoup(text, 'html.parser')
        songs_by_playlist = parse_html_playlists('table', 'sticky-enabled', soup)
        send_html_playlists_to_spotify(songs_by_playlist, existing_playlists, spotify_post, spotify_read, spotify_service.username)
        count += 1

    print('finished!')


def get_webpage_text(count):
    base_url = 'https://www.kalx.berkeley.edu/playlists'
    if not count:
        url = base_url
    else:
        url = base_url + '?page={}'.format(count)

    resp = requests.get(url, verify=False)
    return resp.text


def parse_html_playlists(tag, html_class, soup):
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


def get_existing_playlist_data(spotify, username):
    res = {}
    playlists = spotify.user_playlists(username)
    for playlist in playlists['items']:
        res[playlist['name']] = playlist['id']

    return res


def send_html_playlists_to_spotify(songs_by_playlist, existing_playlists, spotify_post, spotify_read, username):
    for playlist_name in songs_by_playlist:
        playlist_exists = False
        track_ids = get_track_ids(songs_by_playlist[playlist_name], spotify_post)

        if playlist_name in existing_playlists.keys():
            print('add tracks to existing playlist')
            playlist_id = existing_playlists[playlist_name]
            playlist_exists=True
        else:
            print('creating new playlist')
            playlist_id = create_new_playlist(playlist_name, spotify_post, username)

    add_tracks_to_playlist(track_ids, playlist_id, spotify_post, spotify_read, username, playlist_exists)


def add_tracks_to_playlist(track_ids, playlist_id, spotify_post, spotify_read, username, playlist_exists):
    if playlist_exists:
        track_ids = filter_out_duplicate_tracks(username, playlist_id, track_ids, spotify_read)

    try:
        spotify_post.user_playlist_add_tracks(username, playlist_id, track_ids)
    except Exception as e:
        print(e)


def filter_out_duplicate_tracks(username, playlist_id, track_ids, spotify_read):
    unique_track_ids = []
    existing_track_ids = []
    existing_tracks = spotify_read.user_playlist_tracks(username, playlist_id=playlist_id)
    for track_data in existing_tracks['items']:
        existing_track_ids.append(track_data['track']['id'])

    for track_id in track_ids:
        if track_id not in existing_track_ids:
            unique_track_ids.append(track_id)

    return unique_track_ids


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


def parse_config():
    config = configparser.ConfigParser()
    config.read('config.cfg')

    return {
        'client_id': config.get('SPOTIFY', 'CLIENT_ID'),
        'client_secret': config.get('SPOTIFY', 'CLIENT_SECRET'),
        'redirect_uri': config.get('SPOTIFY', 'REDIRECT_URI'),
        'username': config.get('SPOTIFY', 'USERNAME')
    }

main(15)


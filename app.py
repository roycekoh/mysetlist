import io
import yt_dlp as youtube_dl
import subprocess
from flask import Flask, request, render_template, redirect, session, jsonify, url_for, send_from_directory
import requests
from pydub import AudioSegment
import asyncio
from shazamio import Shazam
from collections import defaultdict
from urllib.parse import urlencode
from user_agents import generate_user_agent
import random
import os
import aiohttp
from micawber import bootstrap_basic, parse_html
from micawber.providers import Provider
import time
import jwt
import smtplib
from email.mime.text import MIMEText
from mailjet_rest import Client
from flask import request, jsonify

cache = {}
CACHE_TTL = 20000

current_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a secret key for sessions

# Spotify API credentials
SPOTIFY_CLIENT_ID = 'c3b25478cbf04a39955946a84f58c5d3'
SPOTIFY_CLIENT_SECRET = '21505c5c0fc64f67b80d575e169630dc'
SPOTIFY_REDIRECT_URI = 'http://localhost:5000/callback/spotify'

MAILJET_API_KEY = 'a25bd9e808edd3fe7c148bf27935f070'
MAILJET_API_SECRET = 'de8a152bbfe6827f3d7e36c1eced263f'
FROM_EMAIL = 'roycekoh10@gmail.com'
TO_EMAIL = 'rsk224@cornell.edu'

# Spotify API endpoints
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_BASE_URL = 'https://api.spotify.com/v1/'

# Apple Music API credentials (placeholder - replace with actual credentials)
APPLE_TEAM_ID = 'YOUR_APPLE_TEAM_ID'
APPLE_KEY_ID = 'YOUR_APPLE_KEY_ID'
APPLE_PRIVATE_KEY = '''YOUR_APPLE_PRIVATE_KEY'''
APPLE_REDIRECT_URI = 'http://localhost:5000/callback/apple'

providers = bootstrap_basic()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login/<service>')
def login(service):
    if service == 'spotify':
        scope = 'playlist-modify-public playlist-modify-private'
        params = {
            'client_id': SPOTIFY_CLIENT_ID,
            'response_type': 'code',
            'scope': scope,
            'redirect_uri': SPOTIFY_REDIRECT_URI,
            'show_dialog': True
        }
        auth_url = f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"
        return redirect(auth_url)
    elif service == 'apple':
        # Generate a JWT token for Apple Music
        token = generate_apple_music_token()
        session['apple_music_token'] = token
        return redirect(APPLE_REDIRECT_URI)
    else:
        return jsonify({"error": "Invalid service"})

@app.route('/callback/spotify')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})

    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': SPOTIFY_REDIRECT_URI,
            'client_id': SPOTIFY_CLIENT_ID,
            'client_secret': SPOTIFY_CLIENT_SECRET
        }

        response = requests.post(SPOTIFY_TOKEN_URL, data=req_body)
        token_info = response.json()

        session['spotify_token'] = token_info['access_token']
        session['spotify_refresh_token'] = token_info['refresh_token']
        session['spotify_expires_at'] = time.time() + token_info['expires_in']
    return redirect('/')

@app.route('/current_user')
def get_current_user():
    spotify_logged_in = 'spotify_token' in session
    apple_logged_in = 'apple_music_token' in session

    if spotify_logged_in:
        headers = {'Authorization': f"Bearer {session['spotify_token']}"}
        response = requests.get(SPOTIFY_API_BASE_URL + 'me', headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            return jsonify({
                "service": "spotify",
                "display_name": user_data['display_name'],
                "logged_in": True
            })
    
    if apple_logged_in:
        # Apple Music doesn't have a user profile API, so we'll just return a generic response
        return jsonify({
            "service": "apple",
            "display_name": "Apple Music User",
            "logged_in": True
        })

    return jsonify({"error": "Not logged in", "logged_in": False})

@app.route('/embed', methods=['POST'])
def embed_video():
    url = request.json['url']
    try:
        embedded = providers.request(url)
        return jsonify({'html': embedded['html']})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/analyze', methods=['POST'])
async def analyze_video():
    youtube_url = request.json['youtube_url']
    
    if youtube_url in cache:
        cached_result, cache_time = cache[youtube_url]
        if time.time() - cache_time < CACHE_TTL:
            print("Serving from cache.")
            return jsonify(cached_result)
        else:
            print("Cache expired. Recomputing...")

    print("Received YouTube URL, starting audio download...")
    audio_buffer = download_audio(youtube_url)
    print("Starting analysis...")
    songs_data = await recognize_songs_in_concert(audio_buffer)
    print("Analysis complete.")
    
    songs_response = []
    for song in songs_data:
        songs_response.append({
            "title": song['title'],
            "artist": song['artist'],
            "albumArt": song.get('albumArt', 'https://via.placeholder.com/50'),
            "spotifyLink": f"https://open.spotify.com/search/{song['title']} {song['artist']}",
            "appleMusicLink": f"https://music.apple.com/search?term={song['title']} {song['artist']}"
        })
    
    cache[youtube_url] = (songs_response, time.time())

    return jsonify(songs_response)

def download_audio(youtube_url):
    print("Downloading audio...")
    ydl_opts = {
        'quality': 'worst',
        'outtmpl': '-',
        'quiet': True,
        'noplaylist': True
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=False)
        audio_url = info_dict['url']

        buffer = io.BytesIO()
        command = [
            'ffmpeg',
            '-i', audio_url,
            '-vn',
            '-acodec', 'libmp3lame',
            '-b:a', '64k',
            '-f', 'mp3',
            '-'
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        buffer.write(stdout)
        buffer.seek(0)
        print("Audio download and conversion complete.")

    return buffer

async def recognize_segment(shazam, segment_buffer, segment_number, total_segments, headers, large_segment_number):
    try:
        print(f"Starting recognition for segment {segment_number + 1} of {total_segments} for large segment {large_segment_number + 1}")
        async with aiohttp.ClientSession(headers=headers) as session:
            shazam.http_client.session = session
            result = await shazam.recognize(segment_buffer.read())
            print(f"Finished recognition for segment {segment_number + 1} of {total_segments} for large segment {large_segment_number + 1}.")
        return result
    except Exception as e:
        print(f"Error recognizing segment {segment_number + 1}: {e}")
        return None

async def process_large_segment(shazam, large_segment, segment_duration, min_threshold, large_segment_number, total_large_segments, headers):
    print(f"Processing large segment {large_segment_number + 1} of {total_large_segments}...")
    recognized_songs = defaultdict(lambda: {"count": 0, "song_info": None})
    total_duration = len(large_segment)
    
    total_segments = (total_duration + segment_duration - 1) // segment_duration
    for segment_number, start_time in enumerate(range(0, total_duration, segment_duration)):
        segment = large_segment[start_time:start_time + segment_duration]
        segment_buffer = io.BytesIO()
        segment.export(segment_buffer, format="mp3")
        segment_buffer.seek(0)

        result = await recognize_segment(shazam, segment_buffer, segment_number, total_segments, headers, large_segment_number)
        if result and isinstance(result, dict) and 'track' in result:
            song_key = (result['track']['title'], result['track']['subtitle'])
            recognized_songs[song_key]["count"] += 1
            if recognized_songs[song_key]["song_info"] is None:
                recognized_songs[song_key]["song_info"] = {
                    "title": result['track']['title'],
                    "artist": result['track']['subtitle'],
                    "albumArt": result['track']['images'].get('coverart', None)
                }

    print(f"Finished processing large segment {large_segment_number + 1} of {total_large_segments}.")
    return recognized_songs

async def recognize_songs_in_concert(buffer, large_segment_duration=300000, segment_duration=30000, min_threshold=3):
    headers = {"User-Agent": generate_user_agent()}
    
    shazam = Shazam()

    print("Converting MP3 buffer to audio segments...")
    audio = AudioSegment.from_mp3(buffer)
    total_duration = len(audio)
    recognized_songs = defaultdict(lambda: {"count": 0, "song_info": None})

    total_large_segments = (total_duration + large_segment_duration - 1) // large_segment_duration

    tasks = []
    for large_segment_number, start_time in enumerate(range(0, total_duration, large_segment_duration)):
        large_segment = audio[start_time:start_time + large_segment_duration]
        
        print(f"Scheduling processing for large segment {large_segment_number + 1} of {total_large_segments}...")
        tasks.append(process_large_segment(
            shazam, large_segment, segment_duration, min_threshold, large_segment_number, total_large_segments, headers
        ))
    
    results = await asyncio.gather(*tasks)
    
    for large_segment_results in results:
        for song_key, song_info in large_segment_results.items():
            recognized_songs[song_key]["count"] += song_info["count"]
            if recognized_songs[song_key]["song_info"] is None:
                recognized_songs[song_key]["song_info"] = song_info["song_info"]

    filtered_songs = [info["song_info"] for key, info in recognized_songs.items() if info["count"] >= min_threshold]

    print("Finished processing all segments in parallel.")
    return filtered_songs

@app.route('/save_playlist', methods=['POST'])
def save_playlist():
    data = request.json
    playlist_name = data['title']
    tracks = data['tracks']
    service = data['service']

    if service == 'spotify':
        return save_spotify_playlist(playlist_name, tracks)
    elif service == 'apple':
        return save_apple_music_playlist(playlist_name, tracks)
    else:
        return jsonify({"error": "Invalid service", "success": False})

def save_spotify_playlist(playlist_name, tracks):
    if 'spotify_token' not in session:
        return jsonify({"error": "Not logged in to Spotify", "success": False})

    headers = {'Authorization': f"Bearer {session['spotify_token']}"}
    
    user_response = requests.get(SPOTIFY_API_BASE_URL + 'me', headers=headers)
    if user_response.status_code != 200:
        return jsonify({"error": "Failed to get user info", "success": False})
    
    user_id = user_response.json()['id']

    create_playlist_response = requests.post(
        f"{SPOTIFY_API_BASE_URL}users/{user_id}/playlists",
        headers=headers,
        json={"name": playlist_name, "public": False}
    )
    if create_playlist_response.status_code != 201:
        return jsonify({"error": "Failed to create playlist", "success": False})
    
    playlist_id = create_playlist_response.json()['id']

    track_uris = []
    for track in tracks:
        query = f"track:{track['title']} artist:{track['artist']}"
        search_response = requests.get(
            f"{SPOTIFY_API_BASE_URL}search",
            headers=headers,
            params={"q": query, "type": "track", "limit": 1}
        )
        if search_response.status_code == 200 and search_response.json()['tracks']['items']:
            track_uris.append(search_response.json()['tracks']['items'][0]['uri'])

    if track_uris:
        add_tracks_response = requests.post(
            f"{SPOTIFY_API_BASE_URL}playlists/{playlist_id}/tracks",
            headers=headers,
            json={"uris": track_uris}
        )
        if add_tracks_response.status_code != 201:
            return jsonify({"error": "Failed to add tracks to playlist", "success": False})

    return jsonify({"success": True})

def save_apple_music_playlist(playlist_name, tracks):
    if 'apple_music_token' not in session:
        return jsonify({"error": "Not logged in to Apple Music", "success": False})

    # Apple Music API implementation goes here
    # This is a placeholder as Apple Music API requires a developer account and more setup
    return jsonify({"success": True, "message": "Apple Music playlist saving is not implemented yet"})

def generate_apple_music_token():
    # Generate a JWT token for Apple Music API
    # This is a placeholder and needs to be implemented with actual Apple Music developer credentials
    token = jwt.encode(
        {
            'iss': APPLE_TEAM_ID,
            'iat': int(time.time()),
            'exp': int(time.time()) + 15777000,  # 6 months
        },
        APPLE_PRIVATE_KEY,
        algorithm='ES256',
        headers={
            'kid': APPLE_KEY_ID
        }
    )
    return token

def get_video_title(youtube_url):
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,  # We don't need to download the video
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            return info_dict.get('title', 'Unknown Title')
    except Exception as e:
        print(f"Error retrieving video title: {e}")
        return "Unknown Title"

@app.route('/get_video_title', methods=['POST'])
def get_video_title_route():
    youtube_url = request.json['youtube_url']
    video_title = get_video_title(youtube_url)
    return jsonify({"title": video_title})

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        # Handle form submission
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # You can add code here to save the feedback or send it via email
        # For now, let's just print it to the console
        print(f"Feedback received from {name} ({email}): {message}")

        return redirect(url_for('feedback_thank_you'))

    return render_template('feedback.html')

@app.route('/feedback/thank-you')
def feedback_thank_you():
    return render_template('thank_you.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    feedback = request.json.get('feedback')
    if not feedback:
        return jsonify({"error": "No feedback provided"}), 400

    mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version='v3.1')
    data = {
        'Messages': [
            {
                "From": {
                    "Email": FROM_EMAIL,
                    "Name": "Setlist.io"
                },
                "To": [
                    {
                        "Email": TO_EMAIL,
                        "Name": "Feedback"
                    }
                ],
                "Subject": "New Feedback from Setlist.io",
                "TextPart": f"You have received new feedback:\n{feedback}",
                "HTMLPart": f"<p>You have received new feedback:</p><p>{feedback}</p>"
            }
        ]
    }

    result = mailjet.send.create(data=data)
    if result.status_code == 200:
        return jsonify({"message": "Feedback sent successfully!"}), 200
    else:
        print(f"Mailjet API returned status {result.status_code}: {result.json()}")
        return jsonify({"error": "Failed to send feedback"}), 500



if __name__ == '__main__':
    app.run(debug=True)
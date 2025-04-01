# import note to self - use flask-cache to try to clear cache

# import statements
from flask import Flask, redirect, url_for, session, request, send_from_directory, render_template
from collections import Counter
import os, requests
import random

# define the app
app = Flask(__name__)

app.secret_key = 'my_secret_key'

# spotify client info
spotify_client_id = '12e6f309d1ff49a7b4e3e6299fb7d7f3'
spotify_client_secret = '60ba3bea49e342b0b77545e0c518da1b'
spotify_redirect_uri = 'http://localhost:5000/callback'

# index/home page
@app.route('/')
def index():

  # checks to see if the user is logged in, if they are, it gets their profile information
  if 'spotify_token' in session:

    # requests user information
    access_token = session['spotify_token']
    headers = {'Authorization': 'Bearer ' + access_token}
    response = requests.get('https://api.spotify.com/v1/me', headers=headers)
    user_data = response.json()

    user_info_response = requests.get('https://api.spotify.com/v1/me', headers={'Authorization': 'Bearer ' + access_token})
    playlists_response = requests.get('https://api.spotify.com/v1/me/playlists', headers={'Authorization': 'Bearer ' + access_token})

    if user_info_response.status_code == 200:
      user_data = user_info_response.json()

      username = user_data.get('display_name', 'User')
      profile_picture_url = user_data['images'][0]['url'] if user_data['images'] else None

    if playlists_response.status_code == 200:
      playlists_data = playlists_response.json()
      playlists = playlists_data.get('items', [])

    # render the template with username
    return render_template('user.html', username=username, profile_picture_url=profile_picture_url, playlists=playlists)

  # if they aren't logged in, go to the login page
  else:
    return render_template('index.html', login_url='url_for(\'login\')')

# login page that redirects to the login page
@app.route('/login')
def login():
  payload = {
      'client_id': spotify_client_id,
      'response_type': 'code',
      'redirect_uri': spotify_redirect_uri,
      'scope':
      'user-read-private user-read-email ugc-image-upload user-top-read',  # set the scope to be able to read the user's private info
  }

  # base url used for spotify auth redirect
  auth_url = 'https://accounts.spotify.com/authorize'

  # adds specific parameters to the authorization url to direct to app's specific redirect page
  return redirect(auth_url + '?' +
                  '&'.join([f'{k}={v}' for k, v in payload.items()]))


# this takes the callback from spotify after the user logs in. redirects user back to the home page after spotify sends access token
@app.route('/callback')
def callback():
  code = request.args.get('code')

  # prepare payload for token exchange
  payload = {
      'grant_type': 'authorization_code',
      'code': code,
      'redirect_uri': spotify_redirect_uri,
      'client_id': spotify_client_id,
      'client_secret': spotify_client_secret
  }

  # make POST request to exchange authorization code for access token
  response = requests.post('https://accounts.spotify.com/api/token',
                           data=payload)

  # if token exchange successful
  if response.status_code == 200:
      # break down the data
      token_data = response.json()
      access_token = token_data['access_token']

      # set defaults so it doesnt break
      username = "USERNAME"
      playlists = []
      top_artists = []

      # store access token in session or database
      session['spotify_token'] = access_token

      # get user data from Spotify API
      user_info_response = requests.get('https://api.spotify.com/v1/me', headers={'Authorization': 'Bearer ' + access_token})
      playlists_response = requests.get('https://api.spotify.com/v1/me/playlists', headers={'Authorization': 'Bearer ' + access_token})
      top_artists_response = requests.get('https://api.spotify.com/v1/me/top/artists',  headers={'Authorization': 'Bearer ' + access_token})
      top_tracks_response = requests.get('https://api.spotify.com/v1/me/top/tracks', headers={'Authorization': 'Bearer ' + access_token})
      
      user_data = user_info_response.json()

      username = user_data.get('display_name', 'User')
      profile_picture_url = user_data['images'][0]['url'] if user_data['images'] else None

      # get playlists data from Spotify API
      playlists_data = playlists_response.json()
      playlists = playlists_data.get('items', [])
      
      # snapshot data
      if top_artists_response.status_code == 200:
            top_artists_data = top_artists_response.json()
            top5_artists = [(artist['name'], artist.get('images', [{}])[0].get('url', '')) for artist in top_artists_data.get('items', [])][:5]

      if top_tracks_response.status_code == 200:
            top_tracks_data = top_tracks_response.json()
            top_tracks = [(track['name'], track['artists'][0]['name']) for track in top_tracks_data.get('items', [])][:5]

      # test for top artists, because if it is blank, it will break code
      if top_artists_response.status_code == 200:
          top_artists_data = top_artists_response.json()

          top_artists = [(artist['name'], artist.get('images', [{}])[0].get('url', '')) for artist in top_artists_data.get('items', [])]

          # will be used when  click on artist feature is implemented, for now, useless
          artist_uri = [artist['uri'] for artist in top_artists_data.get('items', [])]
      else:
          print("Error fetching top artists:", top_artists_response.text)
          top_artists = []

      # get top genres
      top_genres = get_top_genres(access_token)

      # recommend songs based on top genres
      recommended_tracks = recommend_songs(access_token, top_genres)

      # render the template with all the data
      return render_template('user.html', username=username, profile_picture_url=profile_picture_url, playlists=playlists, top_artists=top_artists, artist_uri=artist_uri, top_genres=top_genres, recommended_tracks=recommended_tracks, top_tracks=top_tracks, top5_artists=top5_artists)
  else:
      # token exchange failed, handle error
      return 'Token exchange failed'

# logs the user out
@app.route('/logout')
def logout():
    # Clear the entire session
    session.clear()

    # Redirect to the index page (assuming 'index.html' is your index page)
    response = redirect(url_for('index'))
    
    # Clear session-related cookies
    response.set_cookie('session', '', expires=0)

    return response


# fixes the favicon 404 error, found on:
# https://stackoverflow.com/questions/48863061/favicon-ico-results-in-404-error-in-flask-app by user gtalarico
@app.route('/favicon.ico')
def favicon():
  return send_from_directory(os.path.join(app.root_path, 'static'),
                             'favicon.ico',
                             mimetype='image/vnd.microsoft.icon')

# runs the app
if __name__ == '__main__':
   app.run(debug=True)


## functions
def get_top_genres(access_token):
    # get the user's top tracks
    top_tracks_response = requests.get('https://api.spotify.com/v1/me/top/tracks', headers={'Authorization': 'Bearer ' + access_token})

    if top_tracks_response.status_code == 200:
        top_tracks_data = top_tracks_response.json()
        top_tracks = top_tracks_data.get('items', [])

        # get artists from top tracks
        top_artists_ids = [track['artists'][0]['id'] for track in top_tracks]

        # get artists' genres
        top_artists_genres = []
        for artist_id in top_artists_ids:
            artist_response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}', headers={'Authorization': 'Bearer ' + access_token})
            if artist_response.status_code == 200:
                artist_data = artist_response.json()
                top_artists_genres.extend(artist_data.get('genres', []))

        # count the genres
        top_genres_count = Counter(top_artists_genres)

        # get the top 5 genres
        top_genres = top_genres_count.most_common(5)

        # return the top genres
        return top_genres
    
    # print an error and return a blank array to prevent crashes
    else:
        print("Error fetching top tracks:", top_tracks_response.text)
        return []
    

def recommend_songs(access_token, top_genres):
    recommended_tracks = []
    recommendation_count = 0
    recommended_track_ids = set()  # keep track of recommended track IDs to avoid duplicates

    for genre, _ in top_genres:
        # search for tracks in the current genre
        search_response = requests.get(f'https://api.spotify.com/v1/search?q=genre:"{genre}"&type=track&limit=10', headers={'Authorization': 'Bearer ' + access_token})
        
        if search_response.status_code == 200:
            search_results = search_response.json().get('tracks', {}).get('items', [])
            
            # get track information
            for track in search_results:
                track_id = track.get('id')
                # check if this track has already been recommended
                if track_id in recommended_track_ids:
                    continue  # skip if this track has already been recommended
                else:
                    recommended_track_ids.add(track_id) # adds it if not a repeat

                # get the information on a track
                track_name = track.get('name')
                artist_name = track.get('artists')[0].get('name')
                track_url = track.get('external_urls', {}).get('spotify')

                # get track image
                if track.get('album'):
                    images = track['album'].get('images', [])
                    if images:
                        image_url = images[0].get('url')
                    else:
                        image_url = 'https://via.placeholder.com/150'  # placeholder if no image available
                else:
                    image_url = 'https://via.placeholder.com/150'  # placeholder if no album information available

                

                # adds track to list
                recommended_tracks.append({'track_name': track_name, 'artist_name': artist_name, 'track_url': track_url, 'image_url': image_url})
                recommendation_count += 1

                # break the loop if 24 recommendations have been collected
                if recommendation_count == 24:
                    break
        
        # break the loop if 24 recommendations have been collected
        if recommendation_count == 24:
            break
    
    # shuffles the order of the tracks each time so that at least when it gives me the same tracks, it still looks appealing
    random.shuffle(recommended_tracks)
    
    return recommended_tracks
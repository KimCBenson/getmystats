# import note to self - use flask-cache to try to clear cache

# import statements
from flask import Flask, redirect, url_for, session, request, send_from_directory, render_template
import os, requests

# define the app
app = Flask(__name__)

app.secret_key = 'my_secret_key'

# spotify client info
spotify_client_id = '12e6f309d1ff49a7b4e3e6299fb7d7f3'
spotify_client_secret = 'SECRET GOES HERE'
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
      token_data = response.json()
      access_token = token_data['access_token']

      # store access token in session or database
      session['spotify_token'] = access_token

      # get user data from Spotify API
      user_info_response = requests.get('https://api.spotify.com/v1/me', headers={'Authorization': 'Bearer ' + access_token})
      playlists_response = requests.get('https://api.spotify.com/v1/me/playlists', headers={'Authorization': 'Bearer ' + access_token})
      top_artists_response = requests.get('https://api.spotify.com/v1/me/top/artists',  headers={'Authorization': 'Bearer ' + access_token})
      
      user_data = user_info_response.json()

      username = user_data.get('display_name', 'User')
      profile_picture_url = user_data['images'][0]['url'] if user_data['images'] else None

      # get playlists data from Spotify API
      playlists_data = playlists_response.json()
      playlists = playlists_data.get('items', [])

      # test for top artists, because if it is blank, it will break code
      if top_artists_response.status_code == 200:
          top_artists_data = top_artists_response.json()

          top_artists = [(artist['name'], artist['images'][0]['url']) for artist in top_artists_data.get('items', [])]

          top_artists = [(artist['name'], artist.get('images', [{}])[0].get('url', '')) for artist in top_artists_data.get('items', [])]

          # will be used when  click on artist feature is implemented, for now, useless
          artist_uri = [artist['uri'] for artist in top_artists_data.get('items', [])]
      else:
          print("Error fetching top artists:", top_artists_response.text)
          top_artists = []

      # render the template with all the data
      return render_template('user.html', username=username, profile_picture_url=profile_picture_url, playlists=playlists, top_artists=top_artists, artist_uri=artist_uri)
  else:
      # token exchange failed, handle error
      return 'Token exchange failed'

# logs the user out
@app.route('/logout')
def logout():
  session.pop('spotify_token', None)  # clears out the token
  return render_template('index.html', login_url='url_for(\'login\')')

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

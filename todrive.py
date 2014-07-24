#!/usr/bin/python

import httplib2
import json
import os
import pprint
import sys

from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from oauth2client.client import Credentials


# Check https://developers.google.com/drive/scopes for all available scopes
OAUTH_SCOPE = ['https://www.googleapis.com/auth/drive']

# Redirect URI for installed apps
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

CLIENTSECRETS_LOCATION = '/home/pi/.geekhosting.json'
CREDENTIALS_STORE = '/home/pi/.credentials'

class GetCredentialsException(Exception):
  """Error raised when an error occurred while retrieving credentials.

  Attributes:
    authorization_url: Authorization URL to redirect the user to in order to
                       request offline access.
  """

  def __init__(self, authorization_url):
    """Construct a GetCredentialsException."""
    self.authorization_url = authorization_url


class CodeExchangeException(GetCredentialsException):
  """Error raised when a code exchange has failed."""


class NoRefreshTokenException(GetCredentialsException):
  """Error raised when no refresh token has been found."""


class NoUserIdException(Exception):
  """Error raised when no user ID could be retrieved."""


def get_stored_credentials():
  """Retrieved stored credentials for the provided user ID.

  Args:
    user_id: User's ID.
  Returns:
    Stored oauth2client.client.OAuth2Credentials if found, None otherwise.
  Raises:
    NotImplemented: This function has not been implemented.
  """
  # TODO: Implement this function to work with your database.
  #       To instantiate an OAuth2Credentials instance from a Json
  #       representation, use the oauth2client.client.Credentials.new_from_json
  #       class method.
  fl = file(CREDENTIALS_STORE, 'r')
  credentials = Credentials.new_from_json(fl.read())
  fl.close()
  return credentials


def store_credentials(credentials):
  """Store OAuth 2.0 credentials in the application's database.

  This function stores the provided OAuth 2.0 credentials using the user ID as
  key.

  Args:
    user_id: User's ID.
    credentials: OAuth 2.0 credentials to store.
  Raises:
    NotImplemented: This function has not been implemented.
  """
  # TODO: Implement this function to work with your database.
  #       To retrieve a Json representation of the credentials instance, call the
  #       credentials.to_json() method.
  fl = file(CREDENTIALS_STORE, 'w')
  credentials = fl.write(credentials.to_json())
  fl.close()


def exchange_code(authorization_code):
  """Exchange an authorization code for OAuth 2.0 credentials.

  Args:
    authorization_code: Authorization code to exchange for OAuth 2.0
                        credentials.
  Returns:
    oauth2client.client.OAuth2Credentials instance.
  Raises:
    CodeExchangeException: an error occurred.
  """
  flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(OAUTH_SCOPE))
  flow.redirect_uri = REDIRECT_URI
  try:
    credentials = flow.step2_exchange(authorization_code)
    return credentials
  except FlowExchangeError, error:
    logging.error('An error occurred: %s', error)
    raise CodeExchangeException(None)


def get_user_info(credentials):
  """Send a request to the UserInfo API to retrieve the user's information.

  Args:
    credentials: oauth2client.client.OAuth2Credentials instance to authorize the
                 request.
  Returns:
    User information as a dict.
  """
  user_info_service = build(
      serviceName='oauth2', version='v2',
      http=credentials.authorize(httplib2.Http()))
  user_info = None
  try:
    user_info = user_info_service.userinfo().get().execute()
  except errors.HttpError, e:
    logging.error('An error occurred: %s', e)
  if user_info and user_info.get('id'):
    return user_info
  else:
    raise NoUserIdException()


def get_authorization_url():
  """Retrieve the authorization URL.

  Args:
    email_address: User's e-mail address.
    state: State for the authorization URL.
  Returns:
    Authorization URL to redirect the user to.
  """
  flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(OAUTH_SCOPE))
  flow.params['access_type'] = 'offline'
  #flow.params['approval_prompt'] = 'force'
  #flow.params['user_id'] = email_address
  #flow.params['state'] = state
  return flow.step1_get_authorize_url(REDIRECT_URI)


def get_credentials(authorization_code):
  """Retrieve credentials using the provided authorization code.

  This function exchanges the authorization code for an access token and queries
  the UserInfo API to retrieve the user's e-mail address.
  If a refresh token has been retrieved along with an access token, it is stored
  in the application database using the user's e-mail address as key.
  If no refresh token has been retrieved, the function checks in the application
  database for one and returns it if found or raises a NoRefreshTokenException
  with the authorization URL to redirect the user to.

  Args:
    authorization_code: Authorization code to use to retrieve an access token.
    state: State to set to the authorization URL in case of error.
  Returns:
    oauth2client.client.OAuth2Credentials instance containing an access and
    refresh token.
  Raises:
    CodeExchangeError: Could not exchange the authorization code.
    NoRefreshTokenException: No refresh token could be retrieved from the
                             available sources.
  """
  email_address = ''
  try:
    credentials = exchange_code(authorization_code)
    user_info = get_user_info(credentials)
    email_address = user_info.get('email')
    user_id = user_info.get('id')
    if credentials.refresh_token is not None:
      store_credentials(credentials)
      return credentials
    else:
      credentials = get_stored_credentials(user_id)
      if credentials and credentials.refresh_token is not None:
        return credentials
  except CodeExchangeException, error:
    logging.error('An error occurred during code exchange.')
    # Drive apps should try to retrieve the user and credentials for the current
    # session.
    # If none is available, redirect the user to the authorization URL.
    #error.authorization_url = get_authorization_url(email_address, state)
    error.authorization_url = get_authorization_url()
    raise error
  except NoUserIdException:
    logging.error('No user ID could be retrieved.')
  # No refresh token has been retrieved.
  #authorization_url = get_authorization_url(email_address, state)
  authorization_url = get_authorization_url()
  raise NoRefreshTokenException(authorization_url)

def upload_file_to_drive(credentials, fname, parent_folders=[]):

  # Create an httplib2.Http object and authorize it with our credentials
  http = httplib2.Http()
  http = credentials.authorize(http)
  drive_service = build('drive', 'v2', http=http)

  # Insert a file
  media_body = MediaFileUpload(fname, mimetype='image/jpeg', resumable=True)
  body = {
    'title': os.path.basename(fname),
    'mimeType': 'image/jpeg',
    'parents': parent_folders 
  }

  return drive_service.files().insert(body=body, media_body=media_body).execute()

if __name__ == '__main__':

  parent_folders = [{"kind": "drive#parentReference", "id": "0B8uz0hIQ6YENbERzcHlYY1ZpMGc"}]
  filename = sys.argv[1] 
  try:
    credentials = get_stored_credentials()
  except IOError:
    auth_url = get_authorization_url()
    print "Auth the app: {}".format(auth_url)
    code = raw_input('Enter verification code: ').strip()
    credentials = exchange_code(code)
    store_credentials(credentials)

  pprint.pprint(upload_file_to_drive(credentials, filename, parent_folders))
  

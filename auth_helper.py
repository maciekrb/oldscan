
import os
import stat
import argparse
import yaml
from datetime import (
  datetime,
  timedelta
)
import hashlib
from oauth2client.client import (
  OAuth2WebServerFlow,
  OAuth2Credentials
)
from oauth2client.multistore_file import get_credential_storage
from oauth2client import tools
from evernote.api.client import EvernoteClient


CONFIG_FILE = os.environ['HOME'] + '/.oldscan.yaml'
CONFIG_TPL = {
  'google_drive': {
    'client_id': 'YourClientID',
    'client_secret': 'YourClientSecret'
  },
  'evernote': {
    'client_id': 'YourClientID',
    'client_secret': 'YourClientSecret'
  }
}
CREDENTIALS_FILE = os.environ['HOME'] + '/.oldscan.tokens'
SCOPES = {
  'google_drive': ['https://www.googleapis.com/auth/drive'],
  'evernote': ['evernote.basic']
}


def resolve_service(service):
  if service not in SCOPES.keys():
    print "Invalid service: {}, try EVERNOTE or GOOGLE_DRIVE"
    return

  try:
    with open(CONFIG_FILE, 'r') as fl:
      st = oct(os.stat(CONFIG_FILE)[stat.ST_MODE])[-3:]
      if st != '600':
        print "Group / Other readable {}, must be 0600".format(CONFIG_FILE)
        return

      conf = yaml.safe_load(fl)

  except IOError:
    with open(CONFIG_FILE, 'w') as fl:
      yaml.dump(CONFIG_TPL, fl, default_flow_style=False)

    os.chmod(CONFIG_FILE, 0600)
    print "You must edit the {} file adding your API client ID and Key".format(CONFIG_FILE)
    return

  storage = get_credential_storage(
    CREDENTIALS_FILE,
    conf[service]['client_id'],
    hashlib.md5(''.join(SCOPES[service])).hexdigest(),
    SCOPES[service]
  )
  return (
    conf[service]['client_id'],
    conf[service]['client_secret'],
    SCOPES[service],
    storage
  )

def get_credentials(service, sandbox=True):
  """
  Get a valid oAuth Token from an oAuth provider

  Args:
    - service: either evernote or google_drive are supported at this time

  Returns:
    - Credentials object
  """
  srv = service.lower()
  srv_param = resolve_service(srv)
  if srv_param is None:
    return

  client_id, client_secret, scope, storage = srv_param
  if srv == 'evernote':
    return evernote_auth(client_id, client_secret, storage, True)
  else:
    return google_auth(client_id, client_secret, scope, storage)


def evernote_auth(client_id, client_secret, storage, sandbox=False):
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    host = 'localhost'
    port = 9343
    client = EvernoteClient(
      consumer_key=client_id,
      consumer_secret=client_secret,
      sandbox=sandbox
    )
    request_token = client.get_request_token('http://{}:{}/'.format(host, port))
    authorize_url = client.get_authorize_url(request_token)
    print 'Go to the following link in your browser:'
    print
    print '    ' + authorize_url
    print
    http = tools.ClientRedirectServer((host, port), tools.ClientRedirectHandler)
    http.handle_request()
    if 'oauth_verifier' not in http.query_params:
      print "Bad Evernote Oauth, no verifier:{}".format(http.query_params)
      return

    access_token = client.get_access_token(
      request_token['oauth_token'],
      request_token['oauth_token_secret'],
      http.query_params['oauth_verifier']
    )
    token_uri = 'https://{}evernote.com/oauth'.format('sandbox.' if sandbox else '')
    credentials = OAuth2Credentials(
      access_token,
      client_id,
      client_secret,
      refresh_token=request_token['oauth_token'], # not really
      token_expiry=datetime.now() - timedelta(days=-365),
      token_uri=token_uri,
      user_agent='evernote.basic'
    )
    storage.put(credentials)
  return credentials


def google_auth(client_id, client_secret, scope, storage):
  """
  Google based or OAuth2wWebServerFlow compatible services
  """
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    flow = OAuth2WebServerFlow(
      client_id,
      client_secret,
      scope,
    )
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    flags, unknown = parser.parse_known_args(['--noauth_local_webserver'])
    credentials = tools.run_flow(flow, storage, flags)

  return credentials

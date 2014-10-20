#!/usr/bin/env python

import httplib2
import os
import pprint

from apiclient.discovery import build
from apiclient.http import MediaFileUpload


MIME_TYPES = {
  '.jpg': 'image/jpeg',
  '.pdf': 'application/pdf'
}


def upload_file_to_drive(credentials, title, fname, parent_folders=[]):

  # Create an httplib2.Http object and authorize it with our credentials
  http = httplib2.Http()
  http = credentials.authorize(http)
  drive_service = build('drive', 'v2', http=http)

  name, ext = os.path.splitext(fname)
  mimetype = MIME_TYPES[ext]

  # Insert a file
  media_body = MediaFileUpload(fname, mimetype=mimetype, resumable=True)
  body = {
    'title': title,
    'mimeType': mimetype,
    'parents': parent_folders
  }

  return drive_service.files().insert(body=body, media_body=media_body).execute()


def main(credentials, folder_name, title, filename):
  #@TODO make this dynamic
  parent_folders = [{
    "kind": "drive#parentReference",
    "id": "0B8uz0hIQ6YENbERzcHlYY1ZpMGc"
  }]
  pprint.pprint(upload_file_to_drive(credentials, title, filename, parent_folders))

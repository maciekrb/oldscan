
import hashlib
from evernote.api.client import EvernoteClient
import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as Errors


class Notebook:
  def __init__(self, name):
    self.name = name

  @classmethod
  def get_or_create(cls, client, name):
    notebook = cls.searchByName(client, name)
    if notebook is None:
      note_store = client.get_note_store()
      notebook = note_store.createNotebook(name)

    return notebook

  @classmethod
  def searchByName(cls, client, name):
    note_store = client.get_note_store()
    notebooks = note_store.listNotebooks()
    needle = name.lower().replace(' ', '')
    if notebooks:
      for nb in notebooks:
        nbname = nb.name.lower().replace(' ', '')
        if nbname == needle:
          return nb


class Note:
  def __init__(self, title, body=None, attachment=None):
    self.title = title
    self.body = body
    self.resources = list()
    self.embed_resources = list()
    if attachment:
      self.add_resource(attachment[0], attachment[1])

  def add_resource(self, attch_name, attch_body, embed=True):

    mime_type = 'application/pdf'
    md5_hash = hashlib.md5(attch_body).hexdigest()

    data = Types.Data()
    data.size = len(attch_body)
    data.bodyHash = md5_hash
    data.body = attch_body

    resource = Types.Resource()
    resource.mime = mime_type
    resource.data = data
    resource.attributes = Types.ResourceAttributes(fileName=attch_name)

    self.resources.append(resource)

    if embed:
      self.embed_resources.append(self._get_resource_enml(resource))

    return resource

  def _get_resource_enml(self, resource):
    return u'<en-media type="{type}" hash="{hash}"/>'.format(
      type=resource.mime,
      hash=resource.data.bodyHash
    )

  def _get_body(self):
    """ Builds note ENML body """

    bodyWrap = (
      u"<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
      u"<!DOCTYPE en-note SYSTEM \"http://xml.evernote.com/pub/enml2.dtd\">"
      u"<en-note>{body}</en-note>"
    )
    att_enml = "\n".join(self.embed_resources)

    return bodyWrap.format(body=att_enml)

  def save(self, client, notebook, title):
    """
    Creates a note and saves the note to Evernote
    """
    note = Types.Note()
    note.title = title
    note.notebookGuid = notebook.guid
    note.resources = self.resources
    note.content = self._get_body()

    try:
      note_store = client.get_note_store()
      return note_store.createNote(note)

    except Errors.EDAMUserException as e:
      print "EDAMUserException: {}".format(e)

    except Errors.EDAMNotFoundException as e:
      print "EDAMNotFoundException: {}".format(e)


def main(token, notebook_name, title, attachment=None, sandbox=True):

  client = EvernoteClient(token=token, sandbox=sandbox)
  notebook = Notebook.searchByName(client, notebook_name)
  if notebook is None:
    print "Notebook \"{}\" does not exist".format(notebook_name)
    return

  note = Note(title, attachment=attachment)
  new_note = note.save(client, notebook, title)
  print u"Note was succesfully created: {}".format(new_note.guid)

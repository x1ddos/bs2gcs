# encoding: utf-8
import logging
import json

from google.appengine.api import images as images_api
from google.appengine.ext import blobstore as bs
from google.appengine.ext import ndb

import webapp2
from webapp2_extras import jinja2


class Image(ndb.Model):
  """For the demo purposes this entity has both Blobstored- and GCS-stored
  data references.

  Initially, you'd only have blob_key which references Blobstored data.
  While migrating, you'd want to add a GCS-hosted data (gs_key).
  When all the data is migrated, you have safely delete blob_key property.
  """
  blob_key = ndb.BlobKeyProperty()
  gs_key = ndb.StringProperty()
  url = ndb.StringProperty()
  updated = ndb.DateTimeProperty(auto_now=True)


def homepage(req):
  """Renders landing page"""
  return _render_html('_base.html')


def upload(req):
  """Renders images upload page"""
  images = Image.query().order(-Image.updated).fetch(999)
  return _render_html('upload.html', images=images)


def get_upload_url(req):
  """Creates a new upload URL and spits it out as a JSON reponse.

  For the demo purposes this method creates upload URL which points to 
  Blobstore. Part of the migration process would be to change it to something
  like:

    bs.create_upload_url('/upload_success', gs_bucket_name='my-gcs-bucket')

  so that all new uploads go directly to GCS bucket.

  More on blobstore function:
  https://developers.google.com/appengine/docs/python/blobstore/functions
  """
  url = bs.create_upload_url('/upload_success')
  return _render_json({'url': url})


def on_upload_success(req):
  """Internal callback when images have been uploaded (by a browser).

  Responds with a JSON array where each item is an Image object containing
  url, blob_key, gs_key and updated attributes.
  """
  images = []
  for key, value in req.params.items():
    try:
      blob = bs.parse_blob_info(value)
      url = images_api.get_serving_url(blob.key(), secure_url=True)
      image = Image(blob_key=blob.key(), url=url)
      image.put()
      images.append({
        'url': image.url,
        'blob_key': str(image.blob_key),
        'gs_key': image.gs_key,
        'updated': image.updated.isoformat()
      })
    except StandardError, e:
      logging.error(e)
  return _render_json(images)


def _render_html(template, **kwargs):
  """Renders an HTML template using Jinja2.

  Responds with text/html.
  """
  resp = webapp2.Response()
  resp.write(jinja2.get_jinja2().render_template(template, **kwargs))
  return resp


def _render_json(obj):
  """Writes obj as a JSON response using standard json.dumps method.

  Responds with application/json.
  """
  resp = webapp2.Response()
  resp.headers['Content-Type'] = 'application/json'
  json.dump(obj, resp)
  return resp


# Main app
app = webapp2.WSGIApplication([
  ('/', homepage),
  ('/upload', upload),
  ('/get_upload_url', get_upload_url),
  ('/upload_success', on_upload_success)
], debug=True)

"""Blobstore to GCS migration functions."""
from mapreduce import operation as op

from google.appengine.api import images as images_api
from google.appengine.ext import blobstore
import cloudstorage as gcs


BUCKET = 'bs2gcs'


def migrate(image):
	"""Copies blobs stored in Blobstore over to a GCS bucket.

	Args:
		image: main.Image instance representing a single entity in the Datastore.

	This does not delete migrated (old) blobs so it is safe to run the job
	multiple times.
	"""
	if image.blob_key and not image.gs_key:
		blob_info = blobstore.get(image.blob_key)
		if not blob_info:
			image.blob_key = None
		else:
			gs_key = '/'.join(['', BUCKET, blob_info.filename])
			try:
				gcs.stat(gs_key)
			except gcs.NotFoundError:
				reader = blobstore.BlobReader(blob_info)
				with gcs.open(gs_key, 'w', content_type=blob_info.content_type) as f:
					while True:
						data = reader.read(1024**2)
						if not data:
							break
						f.write(data)
			blob_gs_key = blobstore.create_gs_key('/gs'+gs_key)
			image.url = images_api.get_serving_url(blob_gs_key, secure_url=True)
			image.gs_key = gs_key
		yield op.db.Put(image)
		if image.gs_key:
			yield op.counters.Increment('Migrated')


def cleanup(image):
	"""Removes migrated blobs from the Blobstore."""
	if image.blob_key and image.gs_key:
		blobstore.delete(image.blob_key)
		image.blob_key = None
		yield op.db.Put(image)
		yield op.counters.Increment('Deleted blobs')

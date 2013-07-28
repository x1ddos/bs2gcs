# Blobstore to GCS migration

This is a very simple app that shows how to migrate data from Blobstore over
to Google Cloud Storage using App Engine MapReduce, for python27 runtime.

Migration can be run while serving live traffic. It is also safe to run it
multiple times.

## The process

Let's say I have an Image entity that looks like this:

```python
class Image(ndb.Model):
  blob_key = ndb.BlobKeyProperty()
  url = ndb.StringProperty()
  updated = ndb.DateTimeProperty(auto_now=True)
```

where `blob_key` is referencing data stored in Blobstore.

The first thing we want to do is, before writing any map/reduce jobs,
change our app code so that new uploads would go straight to
Google Cloud Storage and not to Blostore anymore. We could also change the
way our Image.url (image serving URL) is being generated: just 
point it to GCS stored file and be done with it! But it's up to you.

Anyway, what I want to do next is to add a new property to `Image` entity
which would hold a reference to GCS-hosted object. Let's call it `gs_key`:

```python
class Image(ndb.Model):
  blob_key = ndb.BlobKeyProperty()
  gs_key = ndb.StringProperty()
  url = ndb.StringProperty()
  updated = ndb.DateTimeProperty(auto_now=True)
```

So, one way to do it is to simply read each Blobstored object and copy it
over to GCS. Here's the code from this sample:

```python
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
```

Once blobs are migrated we would run another job to delete old data which is
still stored in the Blobstore:

```python
def cleanup(image):
  """Removes migrated blobs from the Blobstore."""
  if image.blob_key and image.gs_key:
    blobstore.delete(image.blob_key)
    image.blob_key = None
    yield op.db.Put(image)
    yield op.counters.Increment('Deleted blobs')
```

If you have lots and lots of data stored in the Blobstore, at some point during
the migration process you'll basically end up paying twice for the stored data:
Blobstore + GCS. So, in this case you'll probably want to change the strategy
so that each blob gets removed from the Blobstore right away upon being
successfully migrated to GCS.


## Links

  * [App Engine data processing docs][1]
  * [App Engine GCS client][2]
  * [MapReduce Made Easy video][3]
  * [MapReduce API Talk at Google I/O 2011][4]
  * [Pipeline API Talk at Google I/O 2011][5]
  * [App Engine MapReduce project][7]
  * [App Engine Pipeline project][8]
  * [Pipeline API mailing list][6]


[1]: https://developers.google.com/appengine/docs/python/dataprocessing/
[2]: https://developers.google.com/appengine/docs/python/googlecloudstorageclient/
[3]: http://www.youtube.com/watch?v=3OMH63DDqvc
[4]: http://www.youtube.com/watch?v=EIxelKcyCC0
[5]: http://www.youtube.com/watch?v=Rsfy_TYA2ZY
[6]: http://groups.google.com/group/app-engine-pipeline-api
[7]: https://code.google.com/p/appengine-mapreduce/
[8]: https://code.google.com/p/appengine-pipeline/
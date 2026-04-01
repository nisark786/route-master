from django.conf import settings

from storages.backends.s3 import S3Storage


class MediaS3Storage(S3Storage):
    location = settings.AWS_S3_MEDIA_PREFIX.strip("/")
    file_overwrite = False
    default_acl = None

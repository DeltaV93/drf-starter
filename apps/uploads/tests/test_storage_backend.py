"""Which storage backend is in use, and its defaults.

The S3 branch is only reachable when a bucket is configured, which means a
mistake in it fails for the first real deployment and for nobody before that.
An earlier version referred to AWS_SES_REGION_NAME, defined further down the
settings file -- a NameError that no test run would ever have hit.
"""

import importlib
import sys

import pytest

SETTINGS_MODULES = ('clearpath.settings.base', 'clearpath.settings.testing')


@pytest.fixture
def load_settings(monkeypatch):
    originals = {name: sys.modules.get(name) for name in SETTINGS_MODULES}

    def _load(env):
        for key in (
            'AWS_STORAGE_BUCKET_NAME',
            'AWS_S3_REGION_NAME',
            'AWS_SES_REGION_NAME',
            'AWS_S3_ENDPOINT_URL',
        ):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        for name in SETTINGS_MODULES:
            sys.modules.pop(name, None)
        return importlib.import_module('clearpath.settings.base')

    yield _load

    for name in SETTINGS_MODULES:
        sys.modules.pop(name, None)
    for name, module in originals.items():
        if module is not None:
            sys.modules[name] = module


def test_the_filesystem_backend_is_the_default(load_settings):
    base = load_settings({})

    assert 'FileSystemStorage' in base.STORAGES['default']['BACKEND']


def test_a_bucket_swaps_in_s3(load_settings):
    base = load_settings({'AWS_STORAGE_BUCKET_NAME': 'my-bucket'})

    assert base.STORAGES['default']['BACKEND'] == 'storages.backends.s3.S3Storage'


def test_the_bucket_is_private_and_urls_are_signed(load_settings):
    """A public bucket turns every key into a permanent public URL once it leaks."""
    base = load_settings({'AWS_STORAGE_BUCKET_NAME': 'my-bucket'})

    assert base.AWS_DEFAULT_ACL is None
    assert base.AWS_QUERYSTRING_AUTH is True


def test_uploads_never_overwrite_each_other(load_settings):
    base = load_settings({'AWS_STORAGE_BUCKET_NAME': 'my-bucket'})

    assert base.AWS_S3_FILE_OVERWRITE is False


def test_the_region_falls_back_without_raising(load_settings):
    """The regression: this branch used a name defined later in the file."""
    base = load_settings({'AWS_STORAGE_BUCKET_NAME': 'my-bucket'})

    assert base.AWS_S3_REGION_NAME == 'us-east-1'


def test_the_ses_region_is_reused_when_no_s3_region_is_given(load_settings):
    base = load_settings(
        {'AWS_STORAGE_BUCKET_NAME': 'my-bucket', 'AWS_SES_REGION_NAME': 'eu-west-2'}
    )

    assert base.AWS_S3_REGION_NAME == 'eu-west-2'


def test_an_explicit_s3_region_wins(load_settings):
    base = load_settings(
        {
            'AWS_STORAGE_BUCKET_NAME': 'my-bucket',
            'AWS_SES_REGION_NAME': 'eu-west-2',
            'AWS_S3_REGION_NAME': 'ap-southeast-1',
        }
    )

    assert base.AWS_S3_REGION_NAME == 'ap-southeast-1'

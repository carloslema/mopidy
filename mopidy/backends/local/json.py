from __future__ import absolute_import, unicode_literals

import gzip
import json
import logging
import os
import tempfile

import mopidy
from mopidy import models
from mopidy.backends import local
from mopidy.backends.local import search

logger = logging.getLogger('mopidy.backends.local.json')


# TODO: move to load and dump in models?
def load_library(json_file):
    try:
        with gzip.open(json_file, 'rb') as fp:
            return json.load(fp, object_hook=models.model_json_decoder)
    except (IOError, ValueError) as e:
        logger.warning('Loading JSON local library failed: %s', e)
        return {}


def write_library(json_file, data):
    data['version'] = mopidy.__version__
    directory, basename = os.path.split(json_file)

    # TODO: cleanup directory/basename.* files.
    tmp = tempfile.NamedTemporaryFile(
        prefix=basename + '.', dir=directory, delete=False)

    try:
        with gzip.GzipFile(fileobj=tmp, mode='wb') as fp:
            json.dump(data, fp, cls=models.ModelJSONEncoder,
                      indent=2, separators=(',', ': '))
        os.rename(tmp.name, json_file)
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)


class JsonLibrary(local.Library):
    name = b'json'

    def __init__(self, config):
        self._tracks = {}
        self._media_dir = config['local']['media_dir']
        self._json_file = os.path.join(
            config['local']['data_dir'], b'library.json.gz')

    def load(self):
        library = load_library(self._json_file)
        self._tracks = dict((t.uri, t) for t in library.get('tracks', []))
        return len(self._tracks)

    def add(self, track):
        self._tracks[track.uri] = track

    def remove(self, uri):
        self._tracks.pop(uri, None)

    def commit(self):
        write_library(self._json_file, {'tracks': self._tracks.values()})

    def lookup(self, uri):
        try:
            return [self._tracks[uri]]
        except KeyError:
            logger.debug('Failed to lookup %r', uri)
            return []

    def search(self, query=None, uris=None, exact=False):
        tracks = self._tracks.values()
        if exact:
            return search.find_exact(tracks, query=query, uris=uris)
        else:
            return search.search(tracks, query=query, uris=uris)

from __future__ import absolute_import, unicode_literals

import io

import pygst
pygst.require('0.10')
import gst  # noqa

from mopidy.compat import configparser

try:
    import xml.etree.cElementTree as elementtree
except ImportError:
    import xml.etree.ElementTree as elementtree


# TODO: make detect_FOO_header reusable in general mopidy code.
# i.e. give it just a "peek" like function.
def detect_m3u_header(typefind):
    return typefind.peek(0, 7).upper() == b'#EXTM3U'


def detect_pls_header(typefind):
    return typefind.peek(0, 10).lower() == b'[playlist]'


def detect_xspf_header(typefind):
    data = typefind.peek(0, 150)
    if b'xspf' not in data.lower():
        return False

    try:
        data = io.BytesIO(data)
        for event, element in elementtree.iterparse(data, events=(b'start',)):
            return element.tag.lower() == '{http://xspf.org/ns/0/}playlist'
    except elementtree.ParseError:
        pass
    return False


def detect_asx_header(typefind):
    data = typefind.peek(0, 50)
    if b'asx' not in data.lower():
        return False

    try:
        data = io.BytesIO(data)
        for event, element in elementtree.iterparse(data, events=(b'start',)):
            return element.tag.lower() == 'asx'
    except elementtree.ParseError:
        pass
    return False


def parse_m3u(data):
    # TODO: convert non URIs to file URIs.
    found_header = False
    for line in data.readlines():
        if found_header or line.startswith(b'#EXTM3U'):
            found_header = True
        else:
            continue
        if not line.startswith(b'#') and line.strip():
            yield line.strip()


def parse_pls(data):
    # TODO: convert non URIs to file URIs.
    try:
        cp = configparser.RawConfigParser()
        cp.readfp(data)
    except configparser.Error:
        return

    for section in cp.sections():
        if section.lower() != 'playlist':
            continue
        for i in range(cp.getint(section, 'numberofentries')):
            yield cp.get(section, 'file%d' % (i + 1))


def parse_xspf(data):
    try:
        # Last element will be root.
        for event, element in elementtree.iterparse(data):
            element.tag = element.tag.lower()  # normalize
    except elementtree.ParseError:
        return

    ns = 'http://xspf.org/ns/0/'
    for track in element.iterfind('{%s}tracklist/{%s}track' % (ns, ns)):
        yield track.findtext('{%s}location' % ns)


def parse_asx(data):
    try:
        # Last element will be root.
        for event, element in elementtree.iterparse(data):
            element.tag = element.tag.lower()  # normalize
    except elementtree.ParseError:
        return

    for ref in element.findall('entry/ref[@href]'):
        yield ref.get('href', '').strip()

    for entry in element.findall('entry[@href]'):
        yield entry.get('href', '').strip()

# -*- coding: utf-8 -*-
"""
oar.rest_api.views.resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Proxy to Perl Rest API

"""
import sys
import base64

from http import client as httplib
from urllib import parse as urlencode
from urllib import parse as urlparse


from flask import request, Response, url_for, abort
from werkzeug.datastructures import Headers

from oar.lib.utils import JSONEncoder
from oar.lib.utils import json, reraise
from oar.lib import get_logger

logger = get_logger("oar.rest-api.proxy", forward_stderr=True)


def iterform(multidict):
    for key in multidict.keys():
        for value in multidict.getlist(key):
            yield (key.encode("utf8"), value.encode("utf8"))


def proxy_request(path, proxy_host, proxy_port, proxy_prefix, proxy_auth):
    request_headers = {}
    for h in ["Cookie", "Referer", "X-Csrf-Token"]:
        if h in request.headers:
            request_headers[h] = request.headers[h]

    proxy_path = path
    if request.query_string:
        proxy_path = "%s?%s" % (path, request.query_string)

    if proxy_prefix:
        proxy_path = "/%s/%s" % (proxy_prefix.strip('/'), proxy_path)
    else:
        proxy_path = "/%s" + path

    logger.info("Forward request to : '%s@%s:%s%s" %
                (proxy_auth,proxy_host, proxy_port, proxy_path))
    request_headers["Authorization"] = 'Basic %s' % base64.b64encode(proxy_auth)
    request_headers["Content-Type"] = 'application/json'
    if request.method == "POST" or request.method == "PUT":
        form_data = json.dumps(request.json)
        request_headers["Content-Length"] = len(form_data)
    else:
        form_data = None

    conn = httplib.HTTPConnection(proxy_host, proxy_port)
    conn.request(request.method,
                 proxy_path,
                 body=form_data,
                 headers=request_headers)
    resp = conn.getresponse()

    # Clean up response headers for forwarding
    d = {}
    response_headers = Headers()
    for key, value in resp.getheaders():
        logger.debug(" | %s: %s" % (key, value))
        d[key.lower()] = value
        if key in ["content-length", "connection", "content-type", "transfer-encoding","connection"]:
            continue

        if key == "set-cookie":
            cookies = value.split(",")
            [response_headers.add(key, c) for c in cookies]
        else:
            response_headers.add(key, value)

    # If this is a redirect, munge the Location URL
    if "location" in response_headers:
        redirect = response_headers["location"]
        parsed = urlparse(request.url)
        redirect_parsed = urlparse(redirect)

        redirect_host = redirect_parsed.netloc
        if not redirect_host:
            redirect_host = "%s:%d" % (proxy_host, proxy_port)

        redirect_path = redirect_parsed.path
        if redirect_parsed.query:
            redirect_path += "?" + redirect_parsed.query

        munged_path = url_for("proxy_old_api",
                              path=redirect_path[1:])

        url = "%s://%s%s" % (parsed.scheme, parsed.netloc, munged_path)
        response_headers["location"] = url

    contents = resp.read()

    # Restructing Contents.
    if d["content-type"].find("application/json") >= 0:
        kwargs = {'ensure_ascii': False,
                  'cls': JSONEncoder,
                  'indent': 4,
                  'separators': (',', ': ')}
        contents = json.dumps(json.loads(contents), **kwargs)
        root_prefix = "/%s/%s" % (proxy_prefix.strip('/'), path)
        contents = contents.replace(root_prefix, "")

    flask_response = Response(response=contents,
                              status=resp.status,
                              headers=response_headers,
                              content_type=resp.getheader('content-type'))
    return flask_response


def register_proxy(app, **kwargs):
    methods = ["GET", "POST", "PUT", "DELETE"]

    proxy_host = kwargs.get('proxy_host')
    proxy_port = kwargs.get('proxy_port')
    proxy_prefix = kwargs.get('proxy_prefix')
    proxy_auth = kwargs.get('proxy_auth')

    @app.route('/', defaults={'path': ''}, methods=methods)
    @app.route('/p/<path:path>', methods=methods)
    @app.route('/<path:path>', methods=methods)
    def proxy_old_api(path):
        try:
            return proxy_request(path, proxy_host, proxy_port, proxy_prefix, proxy_auth)
        except IOError as e:
            msg = ("502 Bad Gateway. %s ('%s:%d')" % (e, proxy_host,
                                                      proxy_port))
            try:
                abort(502)
            except:
                exc_type, exc_value, tb = sys.exc_info()
                exc_value.data = msg
                reraise(exc_type, exc_value, tb.tb_next)

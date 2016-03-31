# Author: Hiroshi Ichikawa <http://gimite.net/>
# The license of this source is "New BSD Licence"

import logging
import os
import random
import urlparse

import jinja2
import webapp2
from google.appengine.ext import ndb


AUTH_CODE_LENGTH = 16

AUTH_CODE_SOURCE = (
    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890')

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


def get_secure_schema():
    if os.environ['APPLICATION_ID'].startswith('dev~'):
        # Dev app server doesn't support HTTPS.
        return 'http'
    else:
        return 'https'


class Config(ndb.Model):
    auth_code = ndb.StringProperty()


class File(ndb.Model):
    path = ndb.StringProperty()
    content_type = ndb.StringProperty()
    body = ndb.BlobProperty()


class MainPage(webapp2.RequestHandler):

    def get(self):
        file = ndb.Key(File, self.request.path).get()
        if file:
            self.response.headers['Content-Type'] = file.content_type.encode('utf-8')
            self.response.write(file.body)
        elif self.request.path == '/':
            self.redirect('/admin')
        else:
            self.__output_error(404, 'Not found.\n')

    def put(self):
        if not self.__authorize_for_writes():
            return

        file = File.get_or_insert(self.request.path)
        file.path = self.request.path
        file.content_type = self.request.headers['Content-Type']
        file.body = self.request.body
        file.put()

        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Uploaded.\n')

    def post(self):
        self.put()

    def delete(self):
        if not self.__authorize_for_writes():
            return

        ndb.Key(File, self.request.path).delete()
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Deleted.\n')

    def __output_error(self, status, message):
        self.response.set_status(status)
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write(message)

    def __authorize_for_writes(self):
        u = urlparse.urlsplit(self.request.url)
        auth_codes = urlparse.parse_qs(u.query).get('auth_code')
        config = ndb.Key(Config, '*').get()

        if u.scheme != get_secure_schema():
            self.__output_error(400, 'HTTPS required.\n')
            return False

        if not config:
            self.__output_error(
                    401,
                    'Auth code has not been generated. Access %s://%s/admin to generate one.\n'
                        % (get_secure_schema(), u.netloc))
            return False

        if not auth_codes:
            self.__output_error(401, 'URL parameter "auth_code" is required.\n')
            return False

        if auth_codes[0] != config.auth_code:
            self.__output_error(401, "Auth code doesn't match.\n")
            return False

        return True


class AdminPage(webapp2.RequestHandler):

    def get(self):
        u = urlparse.urlsplit(self.request.url)
        if u.scheme != get_secure_schema():
            self.redirect('%s://%s/admin' % (get_secure_schema(), u.netloc))
            return

        config = Config.get_or_insert('*')
        if not config.auth_code:
            r = random.SystemRandom()
            config.auth_code = ''.join(
                    r.choice(AUTH_CODE_SOURCE) for i in range(AUTH_CODE_LENGTH))
            config.put()

        template_values = {
            'auth_code': config.auth_code,
            'base_url': '%s://%s/' % (get_secure_schema(), u.netloc),
            'uploaded_path': self.request.get('uploaded_path'),
            'deleted_path': self.request.get('deleted_path'),
        }
        template = JINJA_ENVIRONMENT.get_template('admin.html')
        self.response.write(template.render(template_values))        


class AdminUploadPage(webapp2.RequestHandler):

    def post(self):
        path = self.request.get('path')

        if not path or not path.startswith('/'):
            self.__output_error(400, 'The path must start with "/".')
            return

        if self.request.get('upload'):
            if not self.request.POST['body']:
                self.__output_error(400, 'A file is not specified.')
                return

            file = File.get_or_insert(path)
            file.path = path
            file.content_type = self.request.get('content_type') or self.request.POST['body'].type
            file.body = self.request.get('body')
            file.put()

            self.redirect('/admin?uploaded_path=%s' % path)

        elif self.request.get('delete'):
            ndb.Key(File, path).delete()

            self.redirect('/admin?deleted_path=%s' % path)

    def __output_error(self, status, message):
        self.response.set_status(status)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.write(message)


app = webapp2.WSGIApplication([
    (r'/admin', AdminPage),
    (r'/admin/upload', AdminUploadPage),
    (r'.*', MainPage),
], debug=True)

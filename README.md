This is an uploader which runs on Google AppEngine with a simple REST API.

You can upload any contents to any paths by a simple HTTP PUT request.

## How to use

- Create a new AppEngine project at https://console.cloud.google.com/
- Upload the app by:
```
$ appcfg.py -A $APP_ID update .
```
- Access https://$APP_ID.appspot.com/admin with the admin account to get the auth code.
- Upload a file by e.g.:
```
$ curl -X PUT -H 'content-type: text/html' -d 'Hello world!' "https://$APP_ID.appspot.com/hello?auth_code=$AUTH_CODE"
```
- You can access the file at https://$APP_ID.appspot.com/hello

## Restriction

Currently you can only upload files smaller than 1MB. I need to use BlobStore to accept larger files...

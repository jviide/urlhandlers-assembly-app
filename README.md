# urlhandlers-assembly-app [![CircleCI](https://circleci.com/gh/ouspg/urlhandlers-assembly-app.svg?style=shield)](https://circleci.com/gh/ouspg/urlhandlers-assembly-app)

## Prerequisites

Download and install the [Google App Engine SDK for Python](https://cloud.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python), also handily available through Homebrew:

```sh
$ brew install app-engine-python
```

## Development

Launch the development server in the repository root:

```sh
$ dev_appserver.py .
```

This starts the local development server on `localhost:8080`.

## Deployment

To deploy the app to Google Cloud Platform project `my-project` run the following command:

```sh
$ appcfg.py -A my-project -V v1 update .
```

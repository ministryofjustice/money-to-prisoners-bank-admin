# Bank Admin

SSCL staff facing site for [Prisoner Money suite of apps](https://github.com/ministryofjustice/money-to-prisoners).

## Requirements

- Unix-like platform with Python 3.8+ and NodeJS 10 (e.g. via [nvm](https://github.com/nvm-sh/nvm#nvmrc))

## Running locally

It's recommended that you use a python virtual environment to isolate each application.

The simplest way to do this is using:

```shell script
python3 -m venv venv    # creates a virtual environment for dependencies; only needed the first time
. venv/bin/activate     # activates the virtual environment; needed every time you use this app
```

Some build tasks expect the active virtual environment to be at `/venv/`, but should generally work regardless of
its location.

You can copy `mtp_bank_admin/settings/local.py.sample` to `local.py` to overlay local settings that won't be committed,
but it’s not required for a standard setup.

In order to run the application locally, it is necessary to have the API running.
Please refer to the [money-to-prisoners-api](https://github.com/ministryofjustice/money-to-prisoners-api/) repository.

Once the API has started locally, run

```shell script
./run.py serve
# or
./run.py start
```

This will build everything and run the local server at [http://localhost:8002/](http://localhost:8002/).
The former also starts browser-sync at [http://localhost:3002/](http://localhost:3002/).

You should be able to login using following credentials: `refund-bank-admin` or `disbursement-bank-admin`

All build/development actions can be listed with `./run.py --verbosity 2 help`.

### Alternative: Docker

In order to run a server that's exactly similar to the production machines,
you need to have [Docker](https://www.docker.com/products/developer-tools) installed. Run

```shell script
./run.py local_docker
```

and you should be able to connect to the local server.

## Developing

[![CircleCI](https://circleci.com/gh/ministryofjustice/money-to-prisoners-bank-admin.svg?style=svg)](https://circleci.com/gh/ministryofjustice/money-to-prisoners-bank-admin)

With the `./run.py` command, you can run a browser-sync server, and get the assets
to automatically recompile when changes are made, run `./run.py serve` instead of
`./run.py start`. The server is then available at the URL indicated.

```shell script
./run.py test
```

Runs all the application tests.

You can connect a local version of [money-to-prisoners-common](https://github.com/ministryofjustice/money-to-prisoners-common/)
for development by pre-pending the following task to the run script.

```shell script
python_dependencies --common-path [path]
```

### Translating

Update translation files with `./run.py make_messages` – you need to do this every time any translatable text is updated.

Pull updates from Transifex with `./run.py translations --pull`.
You'll need to update translation files afterwards and manually check that the merges occurred correctly.

Push latest English to Transifex with `./run.py translations --push`.
NB: you should pull updates before pushing to merge correctly.

## Deploying

This is handled by [money-to-prisoners-deploy](https://github.com/ministryofjustice/money-to-prisoners-deploy/).

## Additional Bespoke Packages

There are several dependencies of the ``money-to-prisoners-bank-admin`` python library which are maintained by this team, so they may require code-changes when the dependencies (e.g. Django) of the ``money-to-prisoners-bank-admin`` python library are incremented.

* django-form-error-reporting: https://github.com/ministryofjustice/django-form-error-reporting
* django-moj-irat: https://github.com/ministryofjustice/django-moj-irat
* mt940-writer: https://github.com/ministryofjustice/mt940-writer

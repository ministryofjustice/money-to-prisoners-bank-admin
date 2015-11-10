
# Money to Prisoners Bank Admin

Bank admin front-end for Money To Prisoners

## Dependencies
### Docker
To run this project locally you need to have [Docker](http://docs.docker.com/installation/mac/) and [Docker Compose](https://docs.docker.com/compose/install/) installed.

### Other Repositories

Alongside this repository you'll need the [API server](https://github.com/ministryofjustice/money-to-prisoners-api) and if you're planning to deploy then you'll need the [deployment repository](https://github.com/ministryofjustice/money-to-prisoners-deploy) (private repository).

## Working with the code

### Run the tests

#### Unit tests

In a terminal `cd` into the directory you checked this project out into, then:

```
$ make test
```

To run a specific test, or set of tests, run:

```
$ make test TEST=[testname]
```

#### Integration/functional tests

Feature tests are run using a combination of [Cucumber.js](https://github.com/cucumber/cucumber-js) and [WebdriverIO](http://webdriver.io/api.html).

Feature files are in `test/features/` and step definitions live in `test/features/steps/`. The WebdriverIO [testrunner](http://webdriver.io/guide/testrunner/gettingstarted.html) is used to run the tests using a [standalone selenium server](https://www.npmjs.com/package/selenium-standalone).

Config for the testrunner lives in `test/`.

To run the tests against all currently selected browsers (Chrome, Firefox, PhantomJS), first run the application, then:
```
$ export WDIO_BASEURL=http://localhost:8000
```
Or whatever URL your application is running at, then:
```
$ npm test
```

To run the tests headlessly, run:
```
$ npm run test-headless
```

You can also [tag](https://github.com/cucumber/cucumber/wiki/Tags) scenarios with `@wip` and run the following command to only run those scenarios:
```
$ npm run test-wip
```


### Validate code style

#### Python

In a terminal `cd` into the directory you checked this project out into, then:

```
$ make lint
```

To check for a [specific class of style violation](http://flake8.readthedocs.org/en/latest/warnings.html), run:

```
$ make lint LINT_OPTS="--select [lint-rules]"
```

#### JavaScript

To lint javascript files using [JSHint](http://jshint.com/), run:
```
$ gulp lint
```

### Run a development Server

In a terminal `cd` into the directory you checked this project out into, then

```
$ make run
```

Wait while Docker does its stuff.

You should be able to point your browser at [http://localhost:8002](http://localhost:8002) if you're using *boot2docker* then it'll be at the IP of the boot2docker virtual machine. You can find it by typing `boot2docker ip` in a terminal. Then visit http://**boot2docker ip**:8002/

### Log in to the application

Make sure you have a version of the [API](https://github.com/ministryofjustice/money-to-prisoners-api) server running on port 8000.

You should be able to log into the bank admin app using following credentials:

- *bank_admin / bank_admin* for ADI downloads
- *refund_bank_admin / refund_bank_admin* for refund downloads

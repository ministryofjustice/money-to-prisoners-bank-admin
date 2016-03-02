# Money to Prisoners Bank Admin

The Bank Admin UI for the Money to Prisoners Project


## Running locally


In order to run the application locally, it is necessary to have the API running.
Please refer to the [money-to-prisoners-api](https://github.com/ministryofjustice/money-to-prisoners-api/) repository.

Once the API is running locally, run

```
make start
```

This will build everything (which will initially take a while) and run
the local server at [http://localhost:8001](http://localhost:8001).

### Alternative: Docker

In order to run a server that's exactly similar to the production machines,
you need to have [Docker](https://www.docker.com/docker-toolbox) installed. Run

```
make docker
```

and you should eventually be able to connect to the local server.

### Log in to the application

You should be able to log into the cash book app using following credentials:

- *bank-admin / bank-admin*

## Developing

With the `run.sh` command, you can run a browser-sync server, and get the assets
to automatically recompile when changes are made, run `make serve` instead of
`make start`. The server is then available at the URL indicated.

If you've used the second method method above, you can use `gulp serve`
but you'll also need to keep the server at port 8000 running.

```
make test
```

Runs all the application tests.


## Deploying

This is handled by MOJ Digital's CI server. Request access and head there. Consult the dev
runbook if necessary.

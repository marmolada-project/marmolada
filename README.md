# Marmolada

## Local Deployment in Containers

In order to build and run Marmolada from the checked out source code, you need the Podman CLI and
you might want Podman Desktop for managing and monitoring the images, containers and the health of
the container cluster (“pod”).

Both the CLI and Podman Desktop are available from the [Podman Project](https://podman.io/).

The `containers/` directory contains files needed to build and run Marmolada as local containers.
Beware: these are for development only and use guessable passwords, don’t use unchanged for
production deployments.

In the following, run commands from the top level directory of the source worktree.

Run only one of these steps at a time, e.g. the service pod will degrade if running any of the other
`podman-compose` commands. If you want to rebuild the images or migrate database schemas, shut the
service pod down first.

### Building the images

The containers use a common base image which is built first, therefore `podman-compose` has to build
them sequentially:

```
$ podman-compose --parallel 1 -f containers/compose-build-images.yaml build
```

### Setting up the Database

If the database is empty, install the database schema like this:

```
$ podman-compose -f containers/compose-db-setup.yaml up --abort-on-container-exit
```

### Database Schema Migration

To upgrade the database schema to the current version, run this:

```
$ podman-compose -f containers/compose-db-migration.yaml up --abort-on-container-exit
```

### Running the Marmolada Service Pod

The following command runs the services comprising Marmolada: a PostgreSQL database, a Redis
key/value store, the web API and tasks backends.

```
podman-compose -f containers/compose-run.yaml up
```

After a short while, you should be able to access the API service here:

Root: http://localhost:8080
API docs: http://localhost:8080/docs

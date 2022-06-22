# SPRI Explore Tool

## Usage

This tool is hosted at http://radarfilm.studio/

You can browse the film freely without an account. To see some thing and do
anything, you'll need an account with write permissions. Ask Thomas for help
creating one.

If you're interested in working with the SPRI data, that's probably all you need
to know. If you want to work on developing this tool, keep reading.

## Architecture

This tool is designed to facilitate the exploration, metadata tagging, and
processing of SPRI film data. The tool itself is a Python app using the Flask
microframework.

The scanned film images are stored in a publicly-available S3 bucket. This tool
manages a database that maps these images to metadata describing each image's
flight, order number, and other parameters.

Heroku apps are built out of a formation of individual small dynos. We have two
types of dynos here: web and worker. The web dynos are responsible for serving
all requests to the website. The worker dynos offload long-running image processing
(specifically stitching images togehter) to avoid slowing down the web dynos.

Both dynos are deployed using (nearly identical) Docker containers specified by
the `Dockerfile.web` and `Dockerfile.worker` files.

Interaction between the web and worker dynos uses Redis Queue.

## Testing locally

### Heroku and Docker

You'll need to install the Heroku CLI tool: https://devcenter.heroku.com/articles/heroku-cli

You'll also need to install Docker: https://docs.docker.com/engine/install/

### Database setup

You should run a local postgres database for testing.

To install:

```
sudo apt install postgresql-12 postgresql-contrib-12
```

On newer versions of Ubuntu, PostgreSQL 12 may not still be available. As of writing, however, it's still supported and you can get it from the [official PostgreSQL repositories](https://www.postgresql.org/download/linux/ubuntu/). To check what versions you have running, you can use this command: `pg_lsclusters`


It's also handy to have a tool to explore your local database setup. I like Adminer:

```
sudo apt install adminer
sudo a2enconf adminer
```

You'll need to set a password for the `postgres` user (or create a new account and set a password for that one).

To login to the psql shell: `sudo -u postgres psql`
To change the password for a user: `ALTER USER postgres PASSWORD 'newpasswordhere';` (The semicolon is important!)
To quit the shell: `\q`

Then you'll need to edit your `pg_hba.conf` file (which you'll find in `/etc/postgresql/12/main`, possibly with a different verison instead of 12, though note that the current production server runs PostgreSQL 12 and so, for compatibility with pulling backups, it's recommended you stick with 12 for now).

Find this line:

```local   all             postgres                                peer```

and change `peer` to `md5`.

Now you can test if you're able to login by going to `localhost/adminer`.

If that worked, you may want to pull the production database down so you can test on a local snapshot of it. See the "Pulling the production database to your local dev environment" section of the [production database docs](production_database_backup_restore.md) page.

#### Other local postgresql help

Access psql prompt: `sudo -i -u postgres`
May need to change in `pg_hba.conf`: `peer` to `md5` for user `postgres`

### Redis

You'll also need a local Redis server running. See: https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-redis-on-ubuntu-18-04

```sudo apt install redis-server```

### Environment variables

Create a `.env` file in the project base directory (where this file is).
The form of this file should be:

```shell script
SECRET_KEY=<somerandomstringofcharactershere>
ANTARCTICA_FLIGHT_POSITIONING_DIR=./antarctica_original_positioning/
GREENLAND_FLIGHT_POSITIONING_DIR=./greenland_positioning/
ANTARCTICA_FILM_IMAGES_DIR=https://sprifilm.s3-us-west-2.amazonaws.com/
ANTARCTICA_FILM_IMAGES_TIFF_DIR=https://storage.googleapis.com/spri_film_stitched/
GREENLAND_FILM_IMAGES_DIR=https://dtufilm.s3-us-west-2.amazonaws.com/
FILM_IMAGES_DIR=https://sprifilm.s3-us-west-2.amazonaws.com/
ENABLE_TIFF=0
TMP_OUTPUTS_DIR=tmp/
DATABASE_URL=postgresql+psycopg2://postgres:<local postgres password>@localhost:5432/spri_explore
PYBRAKE_PROJECT_ID=
PYBRAKE_KEY=
PORT=7879
```

You will need to replace `<somerandomstringofcharactershere>` with some string of random characters. (For local testing, it really doesn't matter what you put here.) You will also need to replace `<local postgres password>` with the password you setup in the "Database setup" section. You may also need to change the username, database name, and or port here.

### Setting up a `conda` environment

It's recommended to set your default conda channel to `conda-forge` (but probably not strictly required).

One of the pip-only packages (pybrake) also requires gcc. If you're on Ubuntu, you can do `sudo apt install build-essential`.

`conda env create -f environment.yml --name spri_explore`

`conda activate spri_explore`

If you need to add any packages, try to add them from the `conda-forge` or
`pyviz` channels if possible. A few packages are only available through `pip`.
These have an annoying habit of breaking things, but you can do a `pip install`
within the `conda` environment if needed.

If you update the environment at all (install or upgrade any package), you'll
need to save your changes:

`conda env export --no-build > environment.yml`

You should probably immediately attempt to re-build the docker image after doing
this to make sure you didn't break anything.

### Running locally

Running a debug server locally should be as simple as:

`python wsgi.py`

This is the best route for development, because changes you make to the code
will auto-reload in real time.

### Build and run the docker image

From the project base directory, build the docker image with:

```
docker build -t spri-explore:latest -f Dockerfile.web --tag spri-explore-web .
docker build -t spri-explore:latest -f Dockerfile.worker --tag spri-explore-worker .
```

Then run it:

```
docker run -it --network="host" --env-file .env spri-explore-web:latest
docker run -it --network="host" --env-file .env spri-explore-worker:latest
```

You should now be able to open http://localhost:7879/ and see the app in your
browser. (Or replace `7879` with whatever port you defined in your `.env` file.)

## Deploying to Heroku

See https://devcenter.heroku.com/articles/container-registry-and-runtime for reference.

Please build and test your docker image locally. If it doesn't run locally, it's
highly unlikely to run on Heroku.

To push your docker containers to Heroku:

`heroku container:push --recursive --app=spri-explore`

This will upload and build the docker containers. Once complete, you can release it, which will make it active on the web:

`heroku container:release web worker --app=spri-explore`

## Heroku postgresql database

The production database is hosted by Heroku. To backup or restore from it, see the [production database docs](production_database_backup_restore.md) page.

## User administration

For instructions on adding/changing user permissions, see [here](adding_user_permissions.md).

## Other random notes

pybrake 1.0 release breaks things - no idea why

## Feature TODO list

* Add cookie to remember map tile preference
# SPRI Explore Tool

## Usage

This tool is hosted at https://spri-explore.herokuapp.com/

You can browse the film freely without an account. To see some thing and do
anything, you'll need an account with write permissions. Ask Thomas for help
creating one.

If you're interested in working with the SPRI data, that's probably all you need
to know. If you want to work on developing this tool, keep reading.

## Architecture

This tool is designed to facilitate the exploration, metadata tagging, and
processing of SPRI film data. The tool itself it a Python app using the Flask
microframework.

The scanned film images are stored in a publicly-available S3 bucket. This tool
manages a database that maps these images to metadata describing each image's
flight, order number, and other parameters.

This tool is currently deployed in a docker container to Heroku.

## Testing locally

### Database setup

TODO

### Environment variables

Create a `.env` file in the project base directory (where this file is).
The form of this file should be:

```shell script
SECRET_KEY=somerandomstringofcharactershere
FLIGHT_POSITIONING_DIR=./original_positioning/
FILM_IMAGES_DIR=https://sprifilm.s3-us-west-2.amazonaws.com/
ENABLE_TIFF=0
TMP_OUTPUTS_DIR=tmp/
DATABASE_URL=postgresql+psycopg2://postgres:flaskexploredev@localhost:5432/spri_explore
PORT=7879
```

### Setting up a `conda` environment

`conda env create -f environment.yml --name spri_explore`

`conda activate spri_explore`

If you need to add any packages, try to add them from the `conda-forge` or
`pyviz` channels if possible. A few packages are only available through `pip`.
These have an annoying habit of breaking things, but you can do a `pip install`
within the `conda` environment if needed.

If you update the environment at all (install or upgrade any package), you'll
need to save your changes:

`conda env export > environment.yml`

You should probably immediately attempt to re-build the docker image after doing
this to make sure you didn't break anything.

### Running locally

Running a debug server locally should be as simple as:

`python wsgi.py`

This is the best route for development, because changes you make to the code
will auto-reload in real time.

### Build and run the docker image

From the project base directory, build the docker image with:

`docker build -t spri-explore:latest .`

Then run it:

`docker run -it --network="host" --env-file .env spri-explore:latest`

You should now be able to open http://localhost:7879/ and see the app in your
browser. (Or replace `7879` with whatever port you defined in your `.env` file.)

## Deploying to Heroku

See https://devcenter.heroku.com/articles/container-registry-and-runtime for reference.

Please build and test your docker image locally. If it doesn't run locally, it's
highly unlikely to run on Heroku.

TODO

## Database backup and restore

TODO


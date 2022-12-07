## Database backup and restore

To capture a backup on Heroku and then download it:

`heroku pg:backups:capture --app spri-explore`
`heroku pg:backups:download b004 --app spri-explore`

(Repalce `b004` with whatever the id of the backup is.)

This creates a local file `latest.dump` with a backup of the production database.

## Pulling the production database to your local dev environment

Pulling the production database to a local database can be done this way:

`PGUSER=postgres PGPASSWORD=<postgres password> heroku pg:pull HEROKU_POSTGRESQL_BRONZE <local db> --app spri-explore`

## Pushing your local databse to production

Pushing a local database to production works like this: **(DANGER! This will overwrite the production database. You should not do this unless you're manually restoring a backup.)**

(You should set maintenace mode before proceeding.)

First, delete the current online database: `heroku pg:reset --app spri-explore`

Then push your local version to production: `heroku pg:push postgresql://postgres:<postgres password>@localhost:5432/<local db> DATABASE_URL --app spri-explore`
## Setting up postgresql

See https://blog.theodo.com/2017/03/developping-a-flask-web-app-with-a-postresql-database-making-all-the-possible-errors/

`sudo apt install postgresql postgresql-contrib libpq-dev pgloader`
`conda install -c conda-forge psycopg2`

Enter postgres command line with:

`sudo -i -u postgres psql`

Then setup a password for the default user and add a database:

`ALTER USER postgres WITH ENCRYPTED PASSWORD 'password';`
`CREATE DATABASE my_database;`

Grab the latest sqllite `explore.db` and **rename it to `.sqlite`**. This step is very important.

Use pgloader to transfer everything from the sqlite database to the new one:

`sudo -i -u postgres pgloader --verbose /full/path/to/explore.sqlite postgresql:///spri_explore`


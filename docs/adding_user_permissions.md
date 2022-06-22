**These steps require that you have access to our project through your Heroku account. This is intended for administrators of the tool only.**

There are additional permissions that can be granted to users, most importantly the `write_permission` to enable users to make changes to film metadata.

To add or update permissions for a user:

1. Login to Heroku
2. Under "Installed add-ons", click on Heroku Postgres
3. Click settings, then click "View Credentials"
4. Go to Adminer and use the credentials from the previous page to login (be sure to change the database type to "postgresql"
5. Click on the table "flasklogin-users"
6. Click "select data"
7. Find the user you want to edit and press the edit button
8. Check (or uncheck) the "write_permission" and "view_greenland" checkboxes and click save
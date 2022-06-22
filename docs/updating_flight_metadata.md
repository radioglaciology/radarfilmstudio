## Flight metadata

Flight metadata currently doesn't have an online interface for updating it. Flight metadata consists of a mapping between CBD numbers and the following fields:

* Latitude
* Longitude
* Thickness (if available - note that even where available picks may be unreliable)
* Surface (if available - note that even where available picks may be unreliable)

As of now, thickness and surface are derived from OCR of scanned hand or type-written manual surface and bed picking. This picking is generally unreliable and should not be trusted without validation.

All of this information is stored per-flight in `.csv` files with the following columns: `CBD,LAT,LON,THK,SRF`

These files are stored in the `antarctica_original_positioning` and `greenland_positioning` folders for the relevant ice sheets.

To update, you can simply replace (or directly update) the data in any of the CSV files, taking care to keep the format the same.

You should test your changes locally first (see the "Testing locally" section of the [main readme file](readme.md)). If they look good, add and commit your changes, push the changes to GitHub, and finally build and push new Docker containers to GitHub to deploy them.

(If you don't have permission to do this last step, just go as far as pushing your changes to GitHub and ask Thomas to do the rest.)
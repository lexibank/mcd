# Releasing MCD

Since the sources of the data at https://www.trussel2.com/MCD/ and https://doi.org/10.1353/ol.2003.0014 
will not change anymore, new versions of this dataset merely represent bug fixes, additional third-party data (like links
to Concepticon) or updates in linked catalogs such as new Glottolog releases.

1. Recreate the CLDF data:
   ```shell
   cldfbench lexibank.makecldf lexibank_mcd.py --glottolog-version v5.0
   ```
2. Make sure the result is valid:
   ```shell
   pytest
   ```
3. Recreate the map:
   ```shell
   cldfbench cldfviz.map --output map.svg --format svg cldf/cldf-metadata.json --no-legend --pacific-centered --height 10 --width 15 --extent '"-40",50,20,-25' --language-labels --with-ocean
   ```
4. Recreate the CLDF README and Zenodo metadata:
   ```shell
   cldfbench cldfreadme lexibank_mcd.py
   cldfbench zenodo lexibank_mcd.py
   ```
5. Recreate the SQLite db:
   ```shell
   rm -f mcd.sqlite
   cldf createdb cldf/ mcd.sqlite
   ```
6. Commit, tag, push.

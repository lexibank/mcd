# Releasing MCD

Since the sources of the data at https://www.trussel2.com/MCD/ and https://doi.org/10.1353/ol.2003.0014 
will not change anymore, new versions of this dataset merely represent bug fixes, additional third-party data (like links
to Concepticon) or updates in linked catalogs such as new Glottolog releases.

1. Recreate the CLDF data:
   ```shell
   cldfbench lexibank.makecldf lexibank_mcd.py --glottolog-version v5.1 --dev
   ```
2. Make sure the result is valid:
   ```shell
   cldf validate cldf --with-cldf-markdown
   ```
3. Recreate the map:
   ```shell
   cldfbench cldfviz.map --output etc/map.svg --format svg cldf/cldf-metadata.json --language-properties Group --pacific-centered --height 10 --width 15 --extent '"-40",50,20,-25' --language-labels --with-ocean --language-filters '{"Is_Proto":"False"}'
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
6. Recreate the ERD
   ```shell
   cldferd cldf --db mcd.sqlite --format compact.svg --output etc/erd.svg
   ```
7. Commit, tag, push.

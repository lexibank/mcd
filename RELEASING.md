# Releasing MCD

Since the source of the data at https://www.trussel2.com/MCD/ is not expected to change anymore,
new versions of this dataset merely represent bug fixes, additional third-party data (like links
to Concepticon) or updates in linked catalogs such as new Glottolog releases.

1. Recreate the CLDF data:
   ```shell
   cldfbench lexibank.makecldf lexibank_mcd.py --glottolog-version v4.7
   ```
2. Recreate the map:
   ```shell
   cldfbench cldfviz.map --output map.png --format png cldf/cldf-metadata.json --no-legend --pacific-centered --height 10 --width 15 --extent '"-40",50,20,-25' --language-labels --with-ocean
   ```
3. Recreate the CLDF README:
   ```shell
   cldfbench cldfreadme lexibank_mcd.py
   ```
4. Commit, tag, push.
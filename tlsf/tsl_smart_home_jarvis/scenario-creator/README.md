# README Scenario Creator

The *scenario creator* allows to easily combine new scenarios and generate specifications.
How to create new scenarios is described in the following, but also in the file `scenarios/template.tsl`.

## Usage
The file `scenarios/template.tsl` allows to create new combinations of assumptions sets and requirement sets. This can be done as follows:
1. Copy the file, but do not change directory.
2. Uncomment the wanted assumptions and requirements in the copy.
3. Use 'tslresolve' from tsltools to create a single TSL file
   without imports.
4. Use 'tsl2tlsf' to generate a TLSF file.

Note that step 3 and 4 can be merged by using
>"tslresolve INPUT.tsl | tsl2tlsf > OUTPUT.tlsf"

We provide an example showing each of these steps. See *example* files in *scenarios* subfolder.

Remarks:
- The assumptions need to realize an individual requirement; file can be found inside of these (as comment). However, these cannot be used anymore as we changed the import structure for these files.
- Some of the user requirements (mainly the 'All*.tsl' files) are a combination of other requirements.

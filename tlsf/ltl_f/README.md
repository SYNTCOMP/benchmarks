These are the benchmarks from the paper
https://www.ijcai.org/proceedings/2021/0255.pdf.
The paper studies LTLf synthesis under assumptions, and they compare their specialized synthesis approach to Strix.
Hence they convert LTLf+assumptions to standard LTL.
There are two benchmarks:

- finding nemo
- workstation supply

I took their original scripts and slightly modified them to produce TLSF.
The main script is `generate_tlsf_benchmarks.py`.
It runs the original scripts (see folder `original_scripts`), then parses the results and produces the results.
The generated benchmarks are generated in `generated_TLSF` or something similar, see `--help` for details.
Note that the original scripts depend on SPOT's `ltlfilt` which they use to convert LTLf formulas into LTL formula.
It should be searchable in your `PATH`.

__NOTES__

- The correctness of these benchmarks is up to the original authors.
  (There might be a problem with correct handling of `alive` signal wrt safety guarantees, as I remember it.)

- The original scripts are from github repository: https://github.com/Shufang-Zhu/GFSynth

- The original scripts also generate auxiliary files, see `./original_scripts/finding_nemo` and `./original_scripts/workstation_supply`


ayrat

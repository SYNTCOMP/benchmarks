#!/usr/bin/env python3
import argparse
import os

from original_scripts import reduction_to_ltl


def convert_ltl_to_tlsf(ltl_property_string, in_vars, out_vars) -> str:
    title = 'finding_nemo'
    property = ltl_property_string.replace("||", "|").replace("&&", "&").replace("|", "||").replace("&", "&&")

    TLSF_template = """
    INFO {{
      TITLE:       "{title}"
      DESCRIPTION: "LTLf benchmark converted to LTL TLSF. Source: https://www.ijcai.org/proceedings/2021/0255.pdf"
      SEMANTICS:   Mealy
      TARGET:      Mealy
    }}

    MAIN {{
      INPUTS {{
      {inputs}
      }}
      
      OUTPUTS {{
      {outputs}
      }}
      
      GUARANTEES {{
      {property}
      }}
    }}
    """

    tlsf_text = TLSF_template.format(title=title,
                                     inputs="\n".join(i + ";" for i in in_vars),
                                     outputs="\n".join(o + ";" for o in out_vars),
                                     property=property + ";")
    return tlsf_text


if __name__ == '__main__':
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    TLSF_OUT_DIR = ROOT_DIR + "/generated_TLSF/"

    parser = argparse.ArgumentParser(description='Generate FindingNemo and WorkstationResupply benchmarks. '
                                                  'The benchmarks will be output to folder: ' + TLSF_OUT_DIR,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-n', '--n',
                        required=False, default=7,
                        dest='n',
                        type=int,
                        help='the parameter (the same for both benchmarks)')

    args = parser.parse_args()
    assert args.n > 0
    N = args.n

    print("running the original script to generate LTLf benchmarks...")
    os.chdir(ROOT_DIR + "/original_scripts")
    os.system("./generate_ltlf_benchmarks.sh " + str(N))
    os.chdir(ROOT_DIR)

    print("parsing the LTLf benchmarks and producing TLSF from it...")

    if not os.path.exists(TLSF_OUT_DIR):
        os.makedirs(TLSF_OUT_DIR)

    for benchmark_name in ["workstation_resupply", "finding_nemo"]:
        print(benchmark_name + "...")
        for i in range(1, N+1):
            # we know that the script generate_ltlf_benchmarks.sh uses this particular folder structure
            ltlf_benchmark = ROOT_DIR + "/original_scripts/" + benchmark_name + "/" + benchmark_name + "_" + str(i) + "/" + str(i)
            ltl, in_vars, out_vars = reduction_to_ltl.produce_strix_benchmark(ltlf_benchmark)
            tlsf_string = convert_ltl_to_tlsf(ltl, in_vars, out_vars)
            with open(f"{TLSF_OUT_DIR}/{benchmark_name}_pb_{i}_pe_.tlsf", "w") as f:
                print("writing to " + f.name)
                f.write(tlsf_string)

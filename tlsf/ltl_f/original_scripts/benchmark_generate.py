import os
import sys

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: " + sys.argv[0] + " <#benchmark-name> <#parameter>")
        print("#benchmark-name: finding_nemo, workstation_resupply, tcp_shake")
        print("#parameter: positive integer, defaulting to 1. Only compitable with finding_nemo and workstation_resupply")

    else:
        if len(sys.argv) == 2:
            cmd_syft = "python3 tcp_handshake.py"
            os.system(cmd_syft)
            cmd_strix = "python3 tcp_handshake.py --env-fst"
            os.system(cmd_strix)
        else:
            benchmark_name = sys.argv[1]
            n = int(sys.argv[2])
            for i in range(1, n + 1):
                cmd_syft = "python3 " + benchmark_name + ".py " + str(i)
                os.system(cmd_syft)
                cmd_strix = "python3 " + benchmark_name + ".py " + str(i) + " --env-fst"
                os.system(cmd_strix)

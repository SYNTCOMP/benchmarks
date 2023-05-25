def generate_spec(benchmark_name, env_vars, agn_vars,
                  safe_env, gr1_env, safe_agn, reach_agn):
    with open(benchmark_name + ".env_safety", "w") as f:
        f.write(safe_env + "\n")

    with open(benchmark_name + ".agn_safety", "w") as f:
        f.write(safe_agn + "\n")

    with open(benchmark_name + ".agn_reach", "w") as f:
        f.write(reach_agn + "\n")

    with open(benchmark_name + ".env_gr1", "w") as f:
        (lhs, rhs) = gr1_env

        for left_justice in lhs:
            f.write("--Env-Justice--\n")
            f.write(left_justice + "\n")
            f.write("--Justice-End--\n")

        for right_justice in rhs:
            f.write("--Agn-Justice--\n")
            f.write(right_justice + "\n")
            f.write("--Justice-End--\n")
            
        f.write("End\n")

    with open(benchmark_name + ".p", "w") as f:
        f.write(".inputs: " + " ".join(env_vars) + "\n")
        f.write(".outputs: " + " ".join(agn_vars) + "\n")


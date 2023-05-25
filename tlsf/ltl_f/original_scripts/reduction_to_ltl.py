import os
import sys
import math
import random


def read_env_gr1(filename):
	# print(filename)
	env_gr1_file = open(filename, "r")
	env_gr1_left = ""
	env_gr1_right = ""
	lines = env_gr1_file.readlines()
	i = 0
	while i < len(lines):
		line = lines[i]
		if "Env-Justice" in line:
			constraint = "(G(F(" + lines[i+1].strip("\n") + "))) && "
			env_gr1_left = env_gr1_left + constraint
			i = i + 2
		if "Agn-Justice" in line:
			constraint = "(G(F(" + lines[i + 1].strip("\n") + "))) && "
			env_gr1_right = env_gr1_right + constraint
			i = i + 2
		i = i + 1
	env_gr1_left = env_gr1_left.rstrip("&& ")
	env_gr1_right = env_gr1_right.rstrip("&& ")
	env_gr1_ltl = "((" + env_gr1_left + ") -> (" + env_gr1_right + "))"
	env_gr1_file.close()
	return env_gr1_ltl


def read_env_safety(filename):
	env_safety_file = open(filename, "r")
	env_safety = "(" + env_safety_file.read().strip("\n") + ")"
	return env_safety


def read_agn_reach(filename):
	agn_reach_file = open(filename, "r")
	agn_reach = "(" + agn_reach_file.read().strip("\n") + ")"
	return agn_reach


def read_agn_safety(filename):
	agn_safety_file = open(filename, "r")
	agn_safety = "(" + agn_safety_file.read().strip("\n") + ")"
	return agn_safety


def ltlf_to_ltl(ltlf_formula, benchmark_lication):
	ltlf_formula = ltlf_formula.replace("X", "X[!]")
	ltlf_formula = ltlf_formula.replace("N", "X")
	translate_cmd = "ltlfilt --from-ltlf -p -f \"" + ltlf_formula + "\" >"+benchmark_lication+".tmp"
	os.system(translate_cmd)
	t = open(benchmark_lication+".tmp", "r")
	ltl_formula = t.read().strip("\n")
	t.close()
	return ltl_formula


def agn_safety_to_ltl(agn_safety_ltlf, benchmark_lication):
	formula = agn_safety_ltlf[2:-2]
	if "workstation" in benchmark_lication:
		substrs = formula.split("&&")
		# print(substrs)
		formula = ""
		substrs[-1] = "(((!(resupply)) W pick_up_part) & G(resupply -> (X((!(resupply)) W pick_up_part))))"
		formula = "(" + " && ".join(substrs) + ")"
		ltl_formula = ltlf_to_ltl(formula, benchmark_lication)
	else:
		ltl_formula = ltlf_to_ltl(formula, benchmark_lication)
	return ltl_formula


def ltlfgr1_to_ltl(env_gr1_ltl, env_safety_ltlf, agn_reach_ltlf, agn_safety_ltlf, benchmark_lication):
	first_disjunct = "(!("+env_gr1_ltl+"))"
	second_disjunct = "(" + ltlf_to_ltl("(!("+env_safety_ltlf+"))", benchmark_lication) + ")"
	third_disjunct_conjunct_1 = "(" + ltlf_to_ltl(agn_reach_ltlf, benchmark_lication) + ")"
	third_disjunct_conjunct_2 = agn_safety_to_ltl(agn_safety_ltlf, benchmark_lication)
	ltl = "(" + first_disjunct + " || " + second_disjunct + " || (" +  third_disjunct_conjunct_1 + " && " + third_disjunct_conjunct_2 + "))"
	return ltl


def read_vars(line):
	vars_list= ""
	substrs = line.strip("\n").split(" ")
	i = 1
	while i < len(substrs):
		vars_list = vars_list + substrs[i] + ", "
		i = i + 1
	vars_list = vars_list.rstrip(", ")
	return vars_list


def read_part_file(filename):
	part_file = open(filename, "r")
	lines = part_file.readlines()
	assert (len(lines) >= 2)
	inputs = read_vars(lines[0])
	outputs = read_vars(lines[1]) + ", alive"
	return inputs, outputs


def produce_strix_benchmark(benchmark_location):
	env_gr1_file = benchmark_location + "_env_fst.env_gr1"
	env_safety_file = benchmark_location + "_env_fst.env_safety"
	agn_reach_file = benchmark_location + "_env_fst.agn_reach"
	agn_safety_file = benchmark_location + "_env_fst.agn_safety"
	part_file = benchmark_location + "_env_fst.p"

	env_gr1_ltl = read_env_gr1(env_gr1_file)
	# print(env_gr1_ltl)

	env_safety_ltlf = read_env_safety(env_safety_file)
	# print(env_safety_ltlf)

	agn_reach_ltlf = read_agn_reach(agn_reach_file)
	# print(agn_reach_ltlf)

	agn_safety_ltlf = read_agn_safety(agn_safety_file)
	# print(agn_safety_ltlf)

	in_vars_token, out_vars_token = read_part_file(part_file)
	in_vars = [i.strip() for i in in_vars_token.split(",")]
	out_vars = [o.strip() for o in out_vars_token.split(",")]

	ltl = ltlfgr1_to_ltl(env_gr1_ltl, env_safety_ltlf, agn_reach_ltlf, agn_safety_ltlf, benchmark_location)
	return ltl, in_vars, out_vars



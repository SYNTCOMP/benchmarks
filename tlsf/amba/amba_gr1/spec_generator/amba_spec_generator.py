#!/usr/bin/env python3

import argparse
import math
from config_paths import SS_COMPILER_EXEC
from shell_helper import execute_shell, assert_exec_strict


def buildStateString(state_name, op, num_states:int, value, padd_value, add_next):
    result = ""

    if not add_next:
        add_next = ""

    if not padd_value:
        padd_value = "0"

    # bin = reverse sprintf("%b", value)
    bin = "{:b}".format(value)[::-1]

    # for (my $j = 0; $j < $num_states; $j++) {
    for j in range(num_states):
        # if(!($result eq "")) {
        #     $result += $op
        # }
        if result != "":
            result += op

        # my $bin_val = $padd_value
        bin_val = padd_value

        # if($j < length($bin)) {
        #     $bin_val = substr($bin, $j, 1)
        # }
        if j < len(bin):
            bin_val = bin[j]

        # if ($bin_val eq "1") {
        #     $result += "$add_next(" . $state_name . $j . ")"
        # } else {
        #     $result += "$add_next(!" . $state_name . $j . ")"
        # }

        if bin_val == "1":
            result += add_next + "(" + state_name + str(j) + ")"
        else:
            result += add_next + "(!" + state_name + str(j) + ")"

    return result


def buildHMasterString(master_bits:int, value, _AND):
    return buildStateString("hmaster", _AND, master_bits, value, None, None)


def buildNegHMasterString(master_bits:int, value, _OR):
    bin = "{:b}".format(value)

    new_val = ""

    for j in range(len(bin)):
        if bin[j] == "0":
            new_val += "1"
        else:
            new_val += "0"

    # $bin = reverse $new_val
    bin = new_val[::-1]

    result = ""
    # for(my $j = 0; $j < master_bits; $j++) {
    for j in range(master_bits):
        if result != "":
            result += _OR

        bin_val = "1"
        if j < len(bin):
            bin_val = bin[j]

        if bin_val == "1":
            result += "(hmaster" + str(j) + ")"
        else:
            result += "(!hmaster" + str(j) + ")"

    return result


def generate(num_masters:int, tlsf:bool, gfgf:bool, fg:bool, fg_ind:bool, produce_ss:bool) -> str:
    assert num_masters>1
    if tlsf:
        _G="G"
        _F="F"
        _and=" && "
        _or=" || "
        nFormula=" ;"
        _X="X"
    else:
        # slugs format
        _G="G"
        _F="F"
        _and=" && "
        _or=" || "
        nFormula=""
        _X="X"

    # master_bits = ceil((log num_masters)/(log 2))
    master_bits = math.ceil((math.log(num_masters, 2)))

    if master_bits == 0:
        master_bits = 1

    env_initial = ""
    sys_initial = ""
    env_transitions = ""
    sys_transitions = ""
    env_fairness = ""
    env_spec = ""      # the GR1++ part
    sys_fairness = ""
    sys_spec = ""      # the GR1++ part
    input_vars = ""
    output_vars = ""

    ###############################################
    # ENV_INITIAL and INPUT_VARIABLES
    ###############################################

    env_initial += f"!hready{nFormula}\n"
    input_vars  += f"hready{nFormula}\n"

    for i in range(num_masters):
        env_initial += f"!hbusreq{i}{nFormula}\n"
        env_initial += f"!hlock{i}{nFormula}\n"
        input_vars += f"hbusreq{i}{nFormula}\n"
        input_vars += f"hlock{i}{nFormula}\n"

    env_initial += f"!hburst0{nFormula}\n"
    input_vars  += f"hburst0{nFormula}\n"
    env_initial += f"!hburst1{nFormula}\n"
    input_vars  += f"hburst1{nFormula}\n"

    ###############################################
    # ENV_TRANSITION
    ###############################################
    for i in range(num_masters):
        #    env_transitions += "#Assumption 3:\n"
        # we don't prefix with G
        #    env_transitions += "$G( hlock$i=1 ->hbusreq$i=1 ){nFormula}\n"
        env_transitions += f"( hlock{i} ->hbusreq{i} ){nFormula}\n"

    ###############################################
    # ENV_FAIRNESS
    ###############################################
    #env_fairness += "#Assumption 1: \n"
    #env_fairness += "$G($F(!stateA1_1)){nFormula}\n"
    if tlsf:
        env_fairness += f"G(F(!stateA1_1)){nFormula}\n"
    else:
        env_fairness += f"(!stateA1_1){nFormula}\n"       # slugs doesn't prefix with G(F(...))

    #env_fairness += "\n#Assumption 2:\n"
    #env_fairness += "$G($F(hready)){nFormula}\n"

    if gfgf:
        env_spec += f"G(F(req_ready)) -> G(F(hready)){nFormula}\n"   # the same format for TLSF and Slugs
    else:
        if tlsf:
            env_fairness += f"G(F(hready)){nFormula}\n"
        else:
            env_fairness += f"(hready){nFormula}\n"

    ###############################################
    # SYS_INITIAL + OUTPUT_VARIABLES
    ###############################################

    for i in range(master_bits):
        sys_initial += f"!hmaster{i}{nFormula}\n"
        output_vars += f"hmaster{i}{nFormula}\n"

    sys_initial += f"!hmastlock{nFormula}\n"
    output_vars += f"hmastlock{nFormula}\n"
    sys_initial += f"start{nFormula}\n"
    output_vars += f"start{nFormula}\n"
    sys_initial += f"decide{nFormula}\n"
    output_vars += f"decide{nFormula}\n"
    output_vars += f"locked{nFormula}\n"
    sys_initial += f"!locked{nFormula}\n"

    sys_initial += f"hgrant0{nFormula}\n"
    output_vars += f"hgrant0{nFormula}\n"
    for i in range(1, num_masters):
        sys_initial += f"!hgrant{i}{nFormula}\n"
        output_vars += f"hgrant{i}{nFormula}\n"

    #busreq = hbusreq[hmaster]
    sys_initial += f"!busreq{nFormula}\n"
    output_vars += f"busreq{nFormula}\n"

    #Assumption 1:
    sys_initial += f"!stateA1_0{nFormula}\n"
    output_vars += f"stateA1_0{nFormula}\n"
    sys_initial += f"!stateA1_1{nFormula}\n"
    output_vars += f"stateA1_1{nFormula}\n"


    #Guarantee 2:
    sys_initial += f"!stateG2{nFormula}\n"
    output_vars += f"stateG2{nFormula}\n"

    #Guarantee 3:
    sys_initial += f"!stateG3_0{nFormula}\n"
    output_vars += f"stateG3_0{nFormula}\n"
    sys_initial += f"!stateG3_1{nFormula}\n"
    output_vars += f"stateG3_1{nFormula}\n"
    sys_initial += f"!stateG3_2{nFormula}\n"
    output_vars += f"stateG3_2{nFormula}\n"

    #Guarantee 10:
    for i in range(1, num_masters):
        sys_initial += f"!stateG10_{i}{nFormula}\n"
        output_vars += f"stateG10_{i}{nFormula}\n"

    if gfgf:
        output_vars += f"req_ready{nFormula}\n"

    ###############################################
    # SYS_TRANSITION
    ###############################################

    # busreq = hbusreq[hmaster]
    for i in range(num_masters):
        hmaster = buildHMasterString(master_bits, i, _and)
        #    sys_transitions += "$G($hmaster -> (hbusreq$i=0 <->!busreq)){nFormula}\n"
        sys_transitions += f"{hmaster} -> (hbusreq{i} <->busreq){nFormula}\n"

    #Assumption 1:
    #sys_transitions += "#Assumption 1:\n"
    #state 00
    #sys_transitions += "$G(((!stateA1_1){_and}(!stateA1_0){_and}"
    sys_transitions += f"(((!stateA1_1){_and}(!stateA1_0){_and}"
    sys_transitions += f"((!hmastlock){_or}(hburst0){_or}(hburst1))) -> "
    sys_transitions += f" {_X}((!stateA1_1){_and}(!stateA1_0))){nFormula}\n"

    sys_transitions += f"(((!stateA1_1){_and}(!stateA1_0){_and}"
    sys_transitions += f" (hmastlock){_and}(!hburst0){_and}(!hburst1)) -> "
    sys_transitions += f" {_X}((stateA1_1){_and}(!stateA1_0))){nFormula}\n"

    #state 10
    #sys_transitions += "$G(((stateA1_1){_and}(!stateA1_0){_and}(busreq)) -> \n"
    sys_transitions += f"(((stateA1_1){_and}(!stateA1_0){_and}(busreq)) -> "
    sys_transitions += f" {_X}((stateA1_1){_and}(!stateA1_0))){nFormula}\n"

    #sys_transitions += "$G(((stateA1_1){_and}(!stateA1_0){_and}(!busreq){_and}"
    sys_transitions += f"(((stateA1_1){_and}(!stateA1_0){_and}(!busreq){_and}"
    sys_transitions += f"((!hmastlock){_or}(hburst0){_or}(hburst1))) -> "
    sys_transitions += f" {_X}((!stateA1_1){_and}(!stateA1_0))){nFormula}\n"

    #sys_transitions += "$G(((stateA1_1){_and}(!stateA1_0){_and}(!busreq){_and}"
    sys_transitions += f"(((stateA1_1){_and}(!stateA1_0){_and}(!busreq){_and}"
    sys_transitions += f" (hmastlock){_and}(!hburst0){_and}(!hburst1)) -> "
    sys_transitions += f" {_X}((!stateA1_1){_and}(stateA1_0))){nFormula}\n"

    #state 01
    #sys_transitions += "$G(((!stateA1_1){_and}(stateA1_0){_and}(busreq)) -> \n"
    sys_transitions += f"(((!stateA1_1){_and}(stateA1_0){_and}(busreq)) ->"
    sys_transitions += f" {_X}((stateA1_1){_and}(!stateA1_0))){nFormula}\n"

    #sys_transitions += "$G(((!stateA1_1){_and}(stateA1_0){_and}"
    sys_transitions += f"(((!stateA1_1){_and}(stateA1_0){_and}"
    sys_transitions += f" (hmastlock){_and}(!hburst0){_and}(!hburst1)) ->"
    sys_transitions += f" {_X}((stateA1_1){_and}(!stateA1_0))){nFormula}\n"

    #sys_transitions += "$G(((!stateA1_1){_and}(stateA1_0){_and}(!busreq){_and}"
    sys_transitions += f"(((!stateA1_1){_and}(stateA1_0){_and}(!busreq){_and}"
    sys_transitions += f"((!hmastlock){_or}(hburst0){_or}(hburst1))) ->"
    sys_transitions += f" {_X}((!stateA1_1){_and}(!stateA1_0))){nFormula}\n"

    #Guarantee 1:
    #sys_transitions += "\n#Guarantee 1:\n"
    #    sys_transitions += "$G((!hready) ->{_X}(!start)){nFormula}\n"
    sys_transitions += f"((!hready) ->{_X}(!start)){nFormula}\n"

    #Guarantee 2:
    #sys_transitions += "\n#Guarantee 2:\n"
    #sys_transitions += "$G(((!stateG2){_and}"
    sys_transitions += f"(((!stateG2){_and}"
    sys_transitions += f"((!hmastlock){_or}(!start){_or}"
    sys_transitions += f"(hburst0){_or}(hburst1))) ->"
    sys_transitions += f"{_X}(!stateG2)){nFormula}\n"

    #sys_transitions += "$G(((!stateG2){_and}"
    sys_transitions += f"(((!stateG2){_and}"
    sys_transitions += f" (hmastlock){_and}(start){_and}"
    sys_transitions += f"(!hburst0){_and}(!hburst1))  ->"
    sys_transitions += f"{_X}(stateG2)){nFormula}\n"

    #    sys_transitions += "$G(((stateG2){_and}(!start){_and}(busreq)) ->"
    sys_transitions += f"(((stateG2){_and}(!start){_and}(busreq)) ->"
    sys_transitions += f"{_X}(stateG2)){nFormula}\n"

    #    sys_transitions += "$G(((stateG2){_and}(start)) ->FALSE){nFormula}\n"
    sys_transitions += f"!(((stateG2){_and}(start))){nFormula}\n"

    #    sys_transitions += "$G(((stateG2){_and}(!start){_and}(!busreq)) ->"
    sys_transitions += f"(((stateG2){_and}(!start){_and}(!busreq)) ->"
    sys_transitions += f"{_X}(!stateG2)){nFormula}\n"

    #Guarantee 3:
    #sys_transitions += "\n#Guarantee 3:\n"
    #    sys_transitions += "$G(((!stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}"
    sys_transitions += f"(((!stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}"
    sys_transitions += f"  ((!hmastlock){_or}(!start){_or}((hburst0){_or}(!hburst1)))) ->"
    sys_transitions += f"  ({_X}(!stateG3_0){_and}{_X}(!stateG3_1){_and}{_X}(!stateG3_2))) {nFormula}\n"

    #    sys_transitions += "$G(((!stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}"
    sys_transitions += f"(((!stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}"
    sys_transitions += f"  ((hmastlock){_and}(start){_and}((!hburst0){_and}(hburst1)){_and}(!hready))) ->"
    sys_transitions += f"   ({_X}(stateG3_0){_and}{_X}(!stateG3_1){_and}{_X}(!stateG3_2))) {nFormula}\n"

    #    sys_transitions += "$G(((!stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}"
    sys_transitions += f"(((!stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}"
    sys_transitions += f"  ((hmastlock){_and}(start){_and}((!hburst0){_and}(hburst1)){_and}(hready))) ->"
    sys_transitions += f"   ({_X}(!stateG3_0){_and}{_X}(stateG3_1){_and}{_X}(!stateG3_2))) {nFormula}\n"
    sys_transitions += f" \n"

    #    sys_transitions += "$G(((stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(!hready))) ->"
    sys_transitions += f"(((stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(!hready))) ->"
    sys_transitions += f"   ({_X}(stateG3_0){_and}{_X}(!stateG3_1){_and}{_X}(!stateG3_2))) {nFormula}\n"

    #    sys_transitions += "$G(((stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(hready))) ->"
    sys_transitions += f"(((stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(hready))) ->"
    sys_transitions += f"   ({_X}(!stateG3_0){_and}{_X}(stateG3_1){_and}{_X}(!stateG3_2))) {nFormula}\n"
    sys_transitions += f"\n"

    #    sys_transitions += "$G(((stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}((start))) ->FALSE); \n"
    sys_transitions += f"!(((stateG3_0){_and}(!stateG3_1){_and}(!stateG3_2){_and}((start)))) {nFormula}\n"
    sys_transitions += f"\n"
    sys_transitions += f"\n"

    #    sys_transitions += "$G(((!stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(!hready))) ->"
    sys_transitions += f"(((!stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(!hready))) ->"
    sys_transitions += f"   ({_X}(!stateG3_0){_and}{_X}(stateG3_1){_and}{_X}(!stateG3_2))) {nFormula}\n"

    #    sys_transitions += "$G(((!stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(hready))) ->"
    sys_transitions += f"(((!stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(hready))) ->"
    sys_transitions += f"   ({_X}(stateG3_0){_and}{_X}(stateG3_1){_and}{_X}(!stateG3_2))) {nFormula}\n"

    #    sys_transitions += "$G(((!stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((start))) ->FALSE); \n"
    sys_transitions += f"!(((!stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((start)))) {nFormula}\n"
    sys_transitions += "\n"
    #    sys_transitions += "$G(((stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(!hready))) ->"

    sys_transitions += f"(((stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(!hready))) ->"
    sys_transitions += f"   ({_X}(stateG3_0){_and}{_X}(stateG3_1){_and}{_X}(!stateG3_2))) {nFormula}\n"

    #    sys_transitions += "$G(((stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(hready))) ->"
    sys_transitions += f"(((stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((!start){_and}(hready))) ->"
    sys_transitions += f"   ({_X}(!stateG3_0){_and}{_X}(!stateG3_1){_and}{_X}(stateG3_2))){nFormula}\n"

    #    sys_transitions += "$G(((stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((start))) ->FALSE); \n"
    sys_transitions += f"!(((stateG3_0){_and}(stateG3_1){_and}(!stateG3_2){_and}((start)))) {nFormula}\n"
    sys_transitions += "\n"
    #    sys_transitions += "$G(((!stateG3_0){_and}(!stateG3_1){_and}(stateG3_2){_and}((!start){_and}(!hready))) ->"
    sys_transitions += f"(((!stateG3_0){_and}(!stateG3_1){_and}(stateG3_2){_and}((!start){_and}(!hready))) ->"
    sys_transitions += f"   ({_X}(!stateG3_0){_and}{_X}(!stateG3_1){_and}{_X}(stateG3_2))) {nFormula}\n"

    #    sys_transitions += "$G(((!stateG3_0){_and}(!stateG3_1){_and}(stateG3_2){_and}((!start){_and}(hready))) ->"
    sys_transitions += f"(((!stateG3_0){_and}(!stateG3_1){_and}(stateG3_2){_and}((!start){_and}(hready))) ->"
    sys_transitions += f"   ({_X}(!stateG3_0){_and}{_X}(!stateG3_1){_and}{_X}(!stateG3_2))){nFormula}\n"
    sys_transitions += "\n"

    #    sys_transitions += "$G(((!stateG3_0){_and}(!stateG3_1){_and}(stateG3_2){_and}((start))) ->FALSE); \n"
    sys_transitions += f"!(((!stateG3_0){_and}(!stateG3_1){_and}(stateG3_2){_and}((start)))) {nFormula}\n"

    #Guarantee 4 and 5:
    #sys_transitions += "\n#Guarantee 4 and 5:\n"
    for i in range(num_masters):
        hmaster_X = buildStateString("hmaster", _and, master_bits, i, 0, _X)
        sys_transitions += f"((hready) -> ((hgrant{i}) <-> ({hmaster_X}))){nFormula}\n"
        # actually you don't need `hready` signal, so the version below instead of the above will do:
        #sys_transitions += "(((hgrant" + str(i) +  ") <-> (" . $hmaster_X . "))){nFormula}\n"

    #sys_transitions += "#  HMASTLOCK:\n"
    #sys_transitions += "$G((hready) -> (!locked <->{_X}(!hmastlock))){nFormula}\n"
    if fg:
        sys_spec += f"F(G((hready) -> (!locked <-> {_X}(!hmastlock)))){nFormula}\n"
    else:
        sys_transitions += f"((hready) -> (!locked <-> {_X}(!hmastlock))){nFormula}\n"

    # actually you don't need `hready` signal, so the version below instead of the above will do:
    #sys_transitions += "((!locked <->{_X}(!hmastlock))){nFormula}\n"

    #Guarantee 6.1:
    #FIXME: I would be sufficient to have one formula for each bit of hmaster
    #sys_transitions += "\n#Guarantee 6.1:\n"
    for i in range(num_masters):
        hmaster = buildHMasterString(master_bits, i, _and)
        hmaster_X = buildStateString("hmaster", _and, master_bits, i, 0, _X)
        #  sys_transitions += "#  Master {i}:\n"
        #      sys_transitions += "$G({_X}(!start) -> ((" . $hmaster . ") <-> (" . $hmaster_X . "))){nFormula}\n"
        sys_transitions += f"({_X}(!start) -> (({hmaster}) <-> ({hmaster_X}))){nFormula}\n"

    #Guarantee 6.2:
    #sys_transitions += "\n#Guarantee 6.2:\n"
    #    sys_transitions += "$G((({_X}(!start))) -> ((hmastlock) <->{_X}(hmastlock))){nFormula}\n"
    sys_transitions += f"((({_X}(!start))) -> ((hmastlock) <->{_X}(hmastlock))){nFormula}\n"

    #Guarantee 7:
    # G((decide=1 {_and} {_X}(hgrant$i)) -> (hlock$i=1 <->{_X}(locked)))
    #sys_transitions += "\n#Guarantee 7:\n"
    for i in range(num_masters):
        sys_transitions += f"((decide {_and} {_X}(hgrant{i})) -> (hlock{i} <-> {_X}(locked))){nFormula}\n"

    #Guarantee 8:
    #MW: Note, that this formula changes with respect to the number of grant signals
    #sys_transitions += "\n#Guarantee 8:\n"
    for i in range(num_masters):
        #        sys_transitions += "$G((decide=0) -> (((hgrant" + str(i) +  "=0)<-> {_X}(hgrant" + str(i) +  "=0)))){nFormula}\n"
        sys_transitions += f"((!decide) -> (((!hgrant{i}) <-> {_X}(!hgrant{i})))){nFormula}\n"
        #    sys_transitions += "$G((decide=0) -> (!locked <->{_X}(!locked))){nFormula}\n"

    sys_transitions += f"((!decide) -> (!locked <->{_X}(!locked))){nFormula}\n"

    #Guarantee 10:
    #sys_transitions += "\n#Guarantee 10:\n"
    for i in range(1, num_masters):
        #  sys_transitions += "#  Master {i}:\n"
        #      sys_transitions += "$G(((stateG10_{i}=0){_and}(((hgrant{i}=1){_or}(hbusreq{i}=1)))) -> {_X}(stateG10_{i}=0)){nFormula}\n"
        #      sys_transitions += "$G(((stateG10_{i}=0){_and}((hgrant{i}=0){_and}(hbusreq{i}=0))) -> {_X}(stateG10_{i}=1)){nFormula}\n"
        #      sys_transitions += "$G(((stateG10_{i}=1){_and}((hgrant{i}=0){_and}(hbusreq{i}=0))) -> {_X}(stateG10_{i}=1)){nFormula}\n"
        #      sys_transitions += "$G(((stateG10_{i}=1){_and}(((hgrant{i}=1)){_and}(hbusreq{i}=0))) -> FALSE){nFormula}\n"
        #      sys_transitions += "$G(((stateG10_{i}=1){_and}(hbusreq{i}=1)) -> {_X}(stateG10_{i}=0)){nFormula}\n"
        sys_transitions += f"(((!stateG10_{i}){_and}(((hgrant{i}){_or}(hbusreq{i})))) -> {_X}(!stateG10_{i})){nFormula}\n"
        sys_transitions += f"(((!stateG10_{i}){_and}((!hgrant{i}){_and}(!hbusreq{i}))) -> {_X}(stateG10_{i})){nFormula}\n"
        sys_transitions += f"(((stateG10_{i}){_and}((!hgrant{i}){_and}(!hbusreq{i}))) -> {_X}(stateG10_{i})){nFormula}\n"
        sys_transitions += f"!(((stateG10_{i}){_and}(((hgrant{i})){_and}(!hbusreq{i})))){nFormula}\n"
        sys_transitions += f"(((stateG10_{i}){_and}(hbusreq{i})) -> {_X}(!stateG10_{i})){nFormula}\n"

    norequest = ""
    for i in range(num_masters):
        norequest += f"!hbusreq{i}"
        if i < num_masters - 1:
            norequest += f" {_and} "
    #sys_transitions += "#default master\n"
    #    sys_transitions += "$G((decide=1 {_and} ".$norequest.") ->{_X}(hgrant0=1)){nFormula}\n"
    if fg_ind:
        sys_spec += f"F(G((decide {_and} {norequest}) -> {_X}(hgrant0))){nFormula}\n"
    else:
        sys_transitions += f"((decide {_and} {norequest}) -> {_X}(hgrant0)){nFormula}\n"

    ###############################################
    # SYS_FAIRNESS
    ###############################################
    #Guarantee 2:
    #sys_fairness += "\n#Guarantee 2:\n"
    ###sys_fairness += "#The next two fairness conditions are not necessary because\n"
    ###sys_fairness += "#they result from weakuntil-formulas and if the safety condition\n"
    ###sys_fairness += "#is violated the transition relation is empty (FALSE).\n"
    ###sys_fairness += "#$G($F(!stateG2)){nFormula}\n"

    #Guarantee 3:
    #sys_fairness += "\n#Guarantee 3:\n"
    ###sys_fairness += "#$G($F((!stateG3_0) {_and} (!stateG3_1) {_and} (!stateG3_2))){nFormula}\n"

    #Guarantee 9:
    #sys_fairness += "\n#Guarantee 9:\n"
    for i in range(num_masters):
        #  sys_fairness += "$G($F((" . buildHMasterString(master_bits, $i) . ") {_or} hbusreq" + str(i) +  "=0)){nFormula}\n"
        if tlsf:
            sys_fairness += "G(F((" + buildHMasterString(master_bits, i, _and) + f") {_or} !hbusreq{i})){nFormula}\n"
        else:
            sys_fairness += "(((" + buildHMasterString(master_bits, i, _and) + f") {_or} !hbusreq{i})){nFormula}\n"

    ############################################################################################################
    # PRINTING
    ############################################################################################################

    if tlsf:  # ################# PRINT TLSF ####################
        return \
"""INFO {
  TITLE:       "AMBA AHB Case Study"
  DESCRIPTION: "The spec inspired by spec from that GR1 journal paper."
  SEMANTICS:   Mealy,Strict
  TARGET:      Mealy
}

MAIN {

INPUTS {
""" + input_vars + """}

OUTPUTS {
""" + output_vars + """}

// env_init
INITIALLY {
""" + env_initial + """
}

// sys_init
PRESET {
""" + sys_initial + """
}

// env safety
REQUIRE {
""" + env_transitions + """
}

// sys safety
ASSERT {
""" + sys_transitions + """
}

// env GF
ASSUME {
""" + env_fairness + env_spec + """
}

// sys GF
GUARANTEE {
""" + sys_fairness + sys_spec + """
}

}"""
    else:  # ####################### PRINT SLUGS ####################
        # create tmp file
        # write SS there
        # translate into SSIn
        # add env/sys_spec
        # print
        import tempfile
        ss_file = tempfile.NamedTemporaryFile(mode='w')
        ss_file.write("[INPUT]\n")
        ss_file.write(input_vars)
        ss_file.write("\n")

        ss_file.write("[OUTPUT]\n")
        ss_file.write(output_vars)
        ss_file.write("\n")

        ss_file.write("###############################################\n")
        ss_file.write("# Environment specification\n")
        ss_file.write("###############################################\n")
        ss_file.write("[ENV_INIT]\n")
        ss_file.write(env_initial)
        ss_file.write("\n")
        ss_file.write("[ENV_TRANS]\n")
        ss_file.write(env_transitions)
        ss_file.write("\n")
        ss_file.write("[ENV_LIVENESS]\n")
        ss_file.write(env_fairness)
        ss_file.write("\n")

        ss_file.write("###############################################\n")
        ss_file.write("# System specification\n")
        ss_file.write("###############################################\n")
        ss_file.write("[SYS_INIT]\n")
        ss_file.write(sys_initial)
        ss_file.write("\n")
        ss_file.write("[SYS_TRANS]\n")
        ss_file.write(sys_transitions)
        ss_file.write("\n")
        ss_file.write("[SYS_LIVENESS]\n")
        ss_file.write(sys_fairness)
        ss_file.write("\n")
        ss_file.flush()

        if produce_ss:
            with open(ss_file.name, 'r') as readable_ss_file:
                result = readable_ss_file.read()
        else:  # convert to SlugsIN format
            rc, out, err = execute_shell(f"{SS_COMPILER_EXEC} {ss_file.name}")
            assert_exec_strict(rc, out, err)
            result = out

        if env_spec != "":
            result += "[ENV_SPEC]\n"
            result += env_spec
            result += "\n"
        if sys_spec != "":
            result += "[SYS_SPEC]\n"
            result += sys_spec
            result += "\n"
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate AMBA benchmarks in SlugsIN and TLSF formats. '
                                                 'By default, produces GR1 spec; '
                                                 'to produce GR1++ spec, run with flags.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('num_masters', metavar='num_masters', type=int,
                        help='the number of masters')

    parser.add_argument('-tlsf', '--tlsf',
                        required=False, default=False,
                        action='store_true',
                        dest='tlsf',
                        help='produce TLSF spec')

    parser.add_argument('-gfgf', '--gfgf',
                        required=False, default=False,
                        action='store_true',
                        dest='gfgf',
                        help='use GF->GF assumption (GR1++)')

    parser.add_argument('-fg', '--fg',
                        required=False, default=False,
                        action='store_true',
                        dest='fg',
                        help='use non-indexed FG guarantee (GR1++)')

    parser.add_argument('-fg-ind', '--fg-ind',
                        required=False, default=False,
                        action='store_true',
                        dest='fg_ind',
                        help='use indexed FG guarantee (GR1++)')

    parser.add_argument('-ss', '--ss',
                        required=False, default=False,
                        action='store_true',
                        dest='ss',
                        help='produce StructuredSlugs instead of default SlugsIN')

    args = parser.parse_args()

    if args.num_masters <= 1:
        print("the number of clients must be >1")
        exit(-1)

    num_masters = args.num_masters

    print(generate(num_masters, args.tlsf, args.gfgf, args.fg, args.fg_ind, args.ss))



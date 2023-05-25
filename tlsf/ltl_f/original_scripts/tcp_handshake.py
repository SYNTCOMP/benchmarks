import sys
import os

from formulas import *
from spec_generation import generate_spec

env_first = False

if len(sys.argv) > 1:
    if sys.argv[1] != "--env-fst":
        print("Ignoring invalid option: " + sys.argv[1])
    else:
        env_first = True
folder_name = "../tcp_handshake"
if not os.path.exists(folder_name):
  os.makedirs(folder_name)

syn = "syn"
syn_ack_pure = "syn_ack"
ack = "ack"

syn_ack = syn_ack_pure if not env_first else Next(syn_ack_pure)

def safe_env():
    return IfThen(Always(Not(syn)), Always(Not(syn_ack)))

def gr1_env():
    return ([syn], [syn_ack])

def safe_agn():
    return IfThen(Always(Not(syn_ack)), Always(Not(ack)))

def reach_agn():
    return Event(ack)

file_prefix = folder_name+"/tcp_handshake"

generate_spec(file_prefix if not env_first else file_prefix + "_env_fst",
              [syn_ack_pure],
              [syn, ack],
              safe_env(), gr1_env(),
              safe_agn(), reach_agn())

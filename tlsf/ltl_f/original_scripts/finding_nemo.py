import sys
import os

from formulas import *
from spec_generation import generate_spec

if len(sys.argv) < 2:
    print("Usage: " + sys.argv[0] + " <#hallway-sections>")
else:
    n = int(sys.argv[1])
    folder_name = "./finding_nemo/finding_nemo_"+str(n)
    if not os.path.exists(folder_name):
    	os.makedirs(folder_name)

    if n < 1:
        print("Argument must be a positive integer, defaulting to 1")
        n = 1

    env_first = False
    
    if len(sys.argv) > 2:
        if sys.argv[2] != "--env-fst":
            print("Ignoring invalid option: " + sys.argv[2])
        else:
            env_first = True

    hallways = range(n)
    rooms = range(2 * n)
    nemo_rooms = [2 * i + 1 for i in range(n)]

    hallway = lambda i: "hallway_" + str(i)
    room = lambda i: "room_" + str(i)
    regions = [hallway(i) for i in hallways] + [room(i) for i in rooms]
    sense_nemo_pure = "sense_nemo"
    nemo_leaving_pure = "nemo_leaving"
    camera_on = "camera_on"

    sense_nemo = sense_nemo_pure if not env_first else Next(sense_nemo_pure)
    nemo_leaving = (nemo_leaving_pure if not env_first
                    else Next(nemo_leaving_pure))

    trans = dict([(hallway(i), [room(2 * i),
                                room(2 * i + 1),
                                hallway((i - 1) % n),
                                hallway(i),
                                hallway((i + 1) % n)])
                  for i in hallways] +
                 [(room(i), [room(i), hallway(i // 2)])
                  for i in rooms])

    def one_region_at_a_time():
        return Always(BigAnd([IfThen(reg1,
                                     BigAnd([Not(reg2)
                                             for reg2 in regions
                                             if reg2 != reg1]))
                              for reg1 in regions]))
    
    def safe_env():
        safe_env_1 = Always(IfThen(BigAnd([Not(room(i))
                                           for i in nemo_rooms]),
                                   Not(sense_nemo)))

        safe_env_2 = Always(IfThen(And(sense_nemo,
                                       BigOr([And(region, Next(region))
                                              for region in regions])),
                                   Iff(Next(sense_nemo), Not(nemo_leaving))))
        
        safe_env_3 = Always(IfThen(BigAnd([Not(sense_nemo), Next(sense_nemo),
                                           BigOr([And(Next(region),
                                                      Next(Next(region)))
                                                  for region in regions])]),
                                   Next(Next(sense_nemo))))

        return IfThen(one_region_at_a_time(),
                      BigAnd([safe_env_1, safe_env_2, safe_env_3]))

    def gr1_env():
        return ([room(i) for i in nemo_rooms], [sense_nemo])

    def safe_agn():
        safe_agn_1 = one_region_at_a_time()

        safe_agn_2 = Always(BigAnd([IfThen(reg1,
                                           BigOr([WeakNext(reg2)
                                                  for reg2 in trans[reg1]]))
                                    for reg1 in regions]))

        safe_agn_3 = Always(IfThen(Not(sense_nemo), Not(camera_on)))

        return BigAnd([safe_agn_1, safe_agn_2, safe_agn_3])

    def reach_agn(k):
        if k == 1:
            return Event(And(sense_nemo, camera_on))
        else:
            return Event(And(And(sense_nemo, camera_on),
                             Next(reach_agn(k - 1))))

    file_prefix = folder_name+"/"+str(n)

    generate_spec(file_prefix if not env_first else file_prefix + "_env_fst",
                  [sense_nemo_pure, nemo_leaving_pure],
                  [camera_on] + regions,
                  safe_env(), gr1_env(),
                  safe_agn(), reach_agn(3))

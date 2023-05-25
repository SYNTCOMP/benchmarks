import sys
import os

from formulas import *
from spec_generation import generate_spec

if len(sys.argv) < 2:
    print("Usage: " + sys.argv[0] + " <#stations>")
else:
    n = int(sys.argv[1])
    folder_name = "./workstation_resupply/workstation_resupply_"+str(n)
    if not os.path.exists(folder_name):
    	os.makedirs(folder_name)
    
    env_first = False

    if len(sys.argv) > 2:
        if sys.argv[2] != "--env-fst":
            print("Ignoring invalid option: " + sys.argv[2])
        else:
            env_first = True

    stations = range(n)
    stockroom = "stockroom"
    station = lambda i: "station_" + str(i)
    outside = lambda r: "outside_" + r
    occupied_pure = lambda i: "occupied_" + str(i)

    occupied = (occupied_pure if not env_first
                else lambda i: Next(occupied_pure(i)))

    rooms = [stockroom] + [station(i) for i in stations]
    regions = rooms + list(map(outside, rooms))
    
    trans = dict([(room, [room, outside(room)]) for room in rooms] +
                 [(outside(room), [room] + [outside(room) for room in rooms])
                  for room in rooms])

    resupply = "resupply"
    pick_up_part = "pick_up_part"

    def one_region_at_a_time():
        return Always(BigAnd([IfThen(region1,
                                     BigAnd([Not(region2)
                                             for region2 in regions
                                             if region2 != region1]))
                              for region1 in regions]))
    
    def safe_env():
        return IfThen(one_region_at_a_time(),
                      BigAnd([Always(IfThen(And(Not(occupied(i)),
                                                Next(station(i))),
                                            Not(Next(occupied(i)))))
                              for i in stations]))

    def gr1_env():
        return ([TrueConst()], [Not(occupied(i)) for i in stations])

    def safe_agn():
        safe_agn_1 = one_region_at_a_time();

        safe_agn_2 = Always(BigAnd([IfThen(region1,
                                           BigOr([WeakNext(region2)
                                                  for region2
                                                  in trans[region1]]))
                                    for region1 in regions]))

        safe_agn_3 = Always(BigAnd([IfThen(occupied(i), Not(station(i)))
                                    for i in stations]))

        safe_agn_4 = Always(IfThen(pick_up_part, stockroom))

        safe_agn_5 = Always(IfThen(resupply,
                                   BigOr([station(i) for i in stations])))

        safe_agn_6 = IfThen(Event(And(Last(), resupply)),
                            Event(And(pick_up_part,
                                      Until(Not(resupply),
                                            And(Last(),
                                                resupply)))))

        return AgnSafety([safe_agn_1, safe_agn_2, safe_agn_3,
                       safe_agn_4, safe_agn_5, safe_agn_6])

    def reach_agn():
        return BigAnd([Event(And(resupply, station(i))) for i in stations])

    file_prefix = folder_name+"/"+str(n)

    generate_spec(file_prefix if not env_first else file_prefix + "_env_fst",
                  [occupied_pure(i) for i in stations],
                  rooms + [outside(room)
                           for room in rooms] + [pick_up_part, resupply],
                  safe_env(), gr1_env(),
                  safe_agn(), reach_agn())

# Helpers
from dataclasses import dataclass
from typing import List

@dataclass
class strwrap:
    str_: str
    def __lt__(self, other:"strwrap"):
        l = min(len(self.str_), len(other.str_))
        ss = self.str_[:l]
        oss = other.str_[:l]
        return ss < oss

def sortStrList(l:List[str]):
    """
    Sorts a list of string with respect to the order defined in strwrap
    :param l: Original list
    :return: a sorted copy of l
    """
    lp = [strwrap(m) for m in l]
    lp.sort()
    return [mw.str_ for mw in lp]

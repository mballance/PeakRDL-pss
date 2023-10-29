
from typing import IO

class Output(object):

    def __init__(self, fp : IO):
        self._fp = fp
        self._ind = ""

    def println(self, s=""):
        if s != "":
            self._fp.write(self.ind())
            self._fp.write(s)
        self._fp.write("\n")

    def write(self, s):
        self._fp.write(s)

    def inc_ind(self):
        self._ind += "    "
    
    def ind(self):
        return self._ind
    
    def dec_ind(self):
        if len(self._ind) > 4:
            self._ind = self._ind[4:]
        else:
            self._ind = ""
from enum import Enum, auto
from typing import Any, Optional, Union
from systemrdl.walker import RDLListener, RDLWalker, WalkerAction
from systemrdl.node import FieldNode, RegNode, RootNode, AddrmapNode, MemNode, RegfileNode

class Phase(Enum):
    Decl = auto()
    Inst = auto()
    Skip = auto()

class PssExporter(RDLListener):

    def export(self, 
               node : Union[RootNode,AddrmapNode], 
               path: str, 
               package: str,
               **kwargs: Any) -> None:

        top_node = node.top if isinstance(node, RootNode) else node

        # TODO: Decide whether exploding makes sense in PSS
        top_nodes = [top_node]

        self._fp = open(path, "w", encoding='utf-8')
        self._ind = ""
        self._depth = 0
        self._phase = []
        self._last_offset = 0
        self._pad_idx = 0
        self._name_offset_s = []
        self._declared = set()

        self.println("// Generated by PeakRDL-pss")

        if package != "":
            self.println("package %s {" % package)
            self.inc_ind()

        self.println("import std_pkg::*;")
        self.println("import addr_reg_pkg::*;")
        self.println()


        for node in top_nodes:
            self.root_node = node
            RDLWalker().walk(node, self)

        if package != "":
            self.dec_ind()
            self.println("}")

        self._fp.close()

    def enter_Addrmap(self, node: AddrmapNode) -> WalkerAction | None:

        if self.phase() == Phase.Decl:
            # Ensure that we have declared all sub-types
            for c in node.children():
                RDLWalker().walk(c, self)

            self.println()
            self.println("component %s : reg_group_c {" % node.type_name)
            self.inc_ind()
            self.push_phase(Phase.Inst, node)
            self._name_offset_s.append({})

            # Subsequent 
            return WalkerAction.Continue
        else:
            raise Exception("unexpectedly in Inst phase")
            return WalkerAction.SkipDescendants

    def exit_Addrmap(self, node: AddrmapNode) -> WalkerAction | None:

        if len(self._name_offset_s[-1]):
            have_array = False

            self.println()
            self.println("pure function bit[64] get_offset_of_instance(string name) {")
            self.inc_ind()
            for i,(name,(offset,dim,size)) in enumerate(self._name_offset_s[-1].items()):
                have_array |= (dim > 0)
                if i:
                    self.println("} else if (name == \"%s\") {" % name)
                else:
                    self.println("if (name == \"%s\") {" % name)
                self.inc_ind()
                self.println("return %d;" % offset)
                self.dec_ind()
            self.println("} else {")
            self.inc_ind()
            self.println("return 0;")
            self.dec_ind()
            self.println("}")
            self.dec_ind()
            self.println("}")

            self.println()
            self.println("pure function bit[64] get_offset_of_instance_array(string name, int index) {")
            self.inc_ind()
            if have_array:
                clause = 0
                for name,(offset,dim,size) in self._name_offset_s[-1].items():
                    if dim:
                        if clause:
                            self.println("} else if (name == \"%s\") {" % name)
                        else:
                            self.println("if (name == \"%s\") {" % name)
                        self.inc_ind()
                        self.println("return (index*%d);" % size)
                        self.dec_ind()
                        clause += 1
                self.println("} else {")
                self.inc_ind()
                self.println("return 0;")
                self.dec_ind()
                self.println("}")
            else:
                self.println("return 0;")
            self.dec_ind()
            self.println("}")


        self.dec_ind()
        self.println("}")
        self.pop_phase(node)
        self._name_offset_s.pop()
        return WalkerAction.Continue

    def enter_Regfile(self, node: RegfileNode) -> WalkerAction | None:

        if self.phase() == Phase.Decl:
            if node.type_name not in self._declared:
                self._declared.add(node.type_name)

                # Look for undeclared types
                for c in node.children():
                    RDLWalker().walk(c, self)

                self.println()
                self.println("component %s : reg_group_c {" % node.type_name)
                self.inc_ind()

                self.push_phase(Phase.Inst, node)
                self._name_offset_s.append({})

                # Now, continue by 
                return WalkerAction.Continue
            else:
                self.push_phase(Phase.Skip, node)
                return WalkerAction.SkipDescendants
        elif self.phase() == Phase.Inst:
            dim_s = ""
            if node.size > 1:
                dim_s = "[%d]" % node.size
            array_sz = node.array_dimensions[0] if node.is_array else 0
            array_str = node.array_stride if node.is_array else 0
            self._name_offset_s[-1][node.inst_name] = (node.raw_address_offset,array_sz,array_str)
            self.println("%s %s%s;" % (
                node.type_name, 
                node.inst_name,
                dim_s))
            return WalkerAction.SkipDescendants

    def exit_Regfile(self, node: RegfileNode) -> WalkerAction | None:
        pre_phase = self.pop_phase(node)

        if self.phase() is Phase.Decl and pre_phase is not Phase.Skip:
            if len(self._name_offset_s[-1]):
                have_array = False
                self.println()
                self.println("pure function bit[64] get_offset_of_instance(string name) {")
                self.inc_ind()
                for i,(name,(offset,dim,size)) in enumerate(self._name_offset_s[-1].items()):
                    have_array |= (dim > 0)
                    if i:
                        self.println("} else if (name == \"%s\") {" % name)
                    else:
                        self.println("if (name == \"%s\") {" % name)
                    self.inc_ind()
                    self.println("return %d;" % offset)
                    self.dec_ind()
                self.println("} else {")
                self.inc_ind()
                self.println("return 0;")
                self.dec_ind()
                self.println("}")
                self.dec_ind()
                self.println("}")

                self.println()
                self.println("pure function bit[64] get_offset_of_instance_array(string name, int index) {")
                self.inc_ind()
                if have_array:
                    clause = 0
                    for name,(offset,dim,size) in self._name_offset_s[-1].items():
                        if dim:
                            if clause:
                                self.println("} else if (name == \"%s\") {" % name)
                            else:
                                self.println("if (name == \"%s\") {" % name)
                            self.inc_ind()
                            self.println("return (index*%d);" % size)
                            self.dec_ind()
                            clause += 1
                    self.println("} else {")
                    self.inc_ind()
                    self.println("return 0;")
                    self.dec_ind()
                    self.println("}")
                else:
                    self.println("return 0;")
                self.dec_ind()
                self.println("}")

                self._name_offset_s.pop()
            self.dec_ind()
            self.println("} // end-regblock")
    
        return WalkerAction.Continue

    def enter_Reg(self, node: RegNode) -> WalkerAction | None:

        if self.phase() == Phase.Decl:
            if node.type_name not in self._declared:
                self._declared.add(node.type_name)

                # First, ensure we have declared all dependencies
                for c in node.children():
                    RDLWalker().walk(c, self)

                self.println()
                self.println("struct %s : packed_s<> {" % (node.type_name,))
                self.inc_ind()
                self._last_offset = 0
                self._pad_idx = 0

                # Stay in inst mode until we reach the end of the declaration
                self.push_phase(Phase.Inst, node)

                return WalkerAction.Continue
            else:
                # Ensure the 'exit' call knows that it is not closing a declaration
                self.push_phase(Phase.Skip, node)
                return WalkerAction.SkipDescendants
        elif self.phase() == Phase.Inst:
            array_sz = node.array_dimensions[0] if node.is_array else 0
            array_str = node.array_stride if node.is_array else 0
            self._name_offset_s[-1][node.inst_name] = (node.raw_address_offset,array_sz,array_str)
            self.println("reg_c<%s,READWRITE,%d> %s;" % (
                node.type_name, 
                node.size*8,
                node.inst_name))
        return WalkerAction.SkipDescendants
    
    def enter_Field(self, node: FieldNode) -> WalkerAction | None:
        if self.phase() == Phase.Inst:
            if node.lsb > self._last_offset:
                self.println("bit[%d] reserved%s;" % (
                    (node.lsb-self._last_offset),
                    (("%d" % self._pad_idx) if self._pad_idx > 0 else "")))
                self._field_idx = 0
                self._pad_idx += 1

            # TODO: Add padding if needed
            self.println("bit[%d] %s;" % (node.width, node.inst_name))
            self._last_offset = node.msb+1
        return WalkerAction.Continue
    
    def exit_Reg(self, node: RegNode) -> WalkerAction | None:

        pre_phase = self.pop_phase(node)

        if pre_phase is not Phase.Skip and self.phase() == Phase.Decl:
            self.dec_ind()
            self.println("}")
        return WalkerAction.Continue

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

    def push_phase(self, phase : Phase, node):
        self._phase.append((phase, node))

    def phase(self):
        return self._phase[-1][0] if len(self._phase) else Phase.Decl

    def pop_phase(self, node):
        ret = None
        if len(self._phase) == 0:
            raise Exception("Bad pop")
        
        if len(self._phase) and self._phase[-1][1] == node:
            ret = self._phase.pop()[0]
        return ret


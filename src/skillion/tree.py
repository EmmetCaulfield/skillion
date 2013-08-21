"""
    The basic hierarchy presented by 'perf' is comm->dso->symbol, representing
    commands, binary shared/kernel/executable objects or libraries (.so, .ko,
    etc.), and functions respectively.

    In Skillion, this hierarchy is represented by SkNodes, of which there are 4
    different subtypes (with their corresponding `perf` names):

        SkTree (no `perf` equivalent),
           SkCommandNode (comm),
              SkLibraryNode (dso), and
                 SkFunctionNode (symbol)

    The `SkNode` is an abstract base node, never directly instantiated. There is
    exactly one `SkRootNode`, and the hierarchical relationship is as shown
    above.
"""

import re
import os
import sys

from skillion.exceptions import SkError

class SkFormulaSyntaxError(SkError):
    pass

class SkColumnFormula(object):
    RE_CID = re.compile('([_A-Za-z][A-Za-z0-9]*)')

    def __init__(self, formula, dataKeys):
        super(SkColumnFormula, self).__init__()
        self._label      = None
        self._expression = None
        self._needkeys = []

        self._process(formula, dataKeys)

    def _process(self, formula, dataKeys):
        """Returns a copy of 'formula' with c-like identifiers replaced with dict elements"""
        bits = SkColumnFormula.RE_CID.split(formula)
        if bits[0] or bits[2]!='=':
            raise SkFormulaSyntaxError('Expected "<label>=..."')
        self._label = bits[1]
        token = list(bits[3:])
        for i in range(len(token)):
            if token[i] in dataKeys:
                self._needkeys.append( token[i] )
                token[i] = "self.getData('" + token[i] +"')"
        self._expression = ''.join(token)

    def label(self):
        return self._label

    def expression(self):
        return self._expression

    def keyList(self):
        return self._needkeys


class SkNode(object):
    """
    Every `SkNode` has a set of key-value pairs in `_data`. The keys are, in
    general, hardware event names from the database (perf.data via SQL), and the
    values are the corresponding counts.

    Since not every command/library/function necessarily has a value (count) for
    every key (hardware event name), and it is necessary to have a unique
    mapping from column numbers to keys, the mapping is stored in the root node.

    Although the "natural" names for the keys and positions would be "events"
    and "indexes", there are so many events and indexes flying around in PyQt4
    that I've elected to use the more general "key" when referring to hardware
    event names and "position" when referring to the corresponding array index.

    In some sense, there are two kinds of hardware event count, or column: the
    basic kind that come directly from the `perf` database, and the computed
    kind, which involves some kind of calculation based on other hardware event
    counts.

    """
    def __init__(self, name):
        super(SkNode, self).__init__()

        self._name     = name
        self._parent   = None
        self._children = []
        self._data      = {}
        self._timestamp = {}
        self._formulas  = {}
        self._parentHasSameLabel = False
        self._color = None
        self._ischecked = False

#    @classmethod:
#    def clone(cls):

    def name(self):
        return self._name

    def label(self):
        return self._name

    def type(self):
        return 'BASE'

    def getPath(self):
        if self._parent:
            return self._parent.getPath() +'/'+ self.label()
        else:
            return ''

    def appendChild(self, node):
        self._children.append(node)
        if node.label() == self.label():
            node._parentHasSameLabel = True
        node._parent = self

    def insertChild(self, pos, node):
        self._children.insert(pos,  node)

    def removeChild(self, pos):
        node = self._children.pop(pos)
        node._parent = None
        return node

    def getChild(self, pos):
        return self._children[pos]

    def parent(self):
        return self._parent

    def indexOf(self, child):
        return self._children.index(child)

    def childCount(self):
        return len(self._children)

    def isaKernelModule(self):
        return False

    def isaSystemLibrary(self):
        return False

    def isaRelocationStub(self):
        return False

    def isaReservedSymbol(self):
        return False

    def hasKey(self, key):
        return key in self._data or key in self._formulas

    def getData(self, key):
        if key not in self._data:
            # In any case, if we can compute a value, it's OK to cache it, since
            # the underlying data is entirely static.

            # First, check if we have a formula for computing the data:
            formula = self.getFormula(key)
            if formula is not None:
                # Make sure that we have data for all the keys needed by the formula:
                doEval = True
                for k in formula.keyList():
                    if k == key:
                        # Avoid recursion
                        doEval = False
                        break
                    if self.getData(k) is None:
                        # A value required by the formula expression is None
                        doEval = False
                        break
                if doEval:
                    self._data[key] = eval( formula.expression() )
                    return self._data[key]

            # If we get to here, we have no formula, or the formula didn't work out,
            # so we see if we can aggregate the values from children:
            total = 0
            for child in self._children:
                count = child.getData(key)
                if count is not None:
                    total += count
            if total!=0:
                self._data[key] = total
            else:
                self._data[key] = None

        return self._data[key]

    def setData(self, key, value):
        self._data[key] = value

    def getFormula(self, key):
        if key in self._formulas:
            return self._formulas[key]
        elif self._parent is not None:
            return self._parent.getFormula(key)
        return None

    def setFormula(self, key, formula):
        self._formulas[key] = formula
        if key not in self._keys:
            self._keys.append(key)


    def setTimestamp(self, key, value):
        self._timestamp[key] = value

    def getTimestamp(self, key):
        if key not in self._timestamp:
            minimum = sys.maxint
            for child in self._children:
                tmp = child.getTimestamp()
                if tmp is not None and tmp < minimum:
                    minimum = tmp
            if minimum != sys.maxint:
                self._timestamp[key] = minimum
            else:
                self._timestamp[key] = None

        return self._timestamp[key]


    # FIXME: Does this belong in the proxy model?
    def isChecked(self):
        return self._ischecked

    def setChecked(self, toggle):
        self._ischecked = bool(toggle)

    def getColor(self):
        return self._color

    def setColor(self, color):
        self._color = color

    def prettyPrint(self,  tabLevel=-1):
        s = ""
        tabLevel += 1
        while range(tabLevel):
            s += '    '
        s += "`---" + self._name + '    ' + str(self._data) + '\n'
        for node in self._children:
            s += node.prettyPrint(tabLevel)
        tabLevel -= 1
        return s

    @classmethod
    def testTree(cls):
        tree = cls("root")
        tree.appendChild( cls("root's first child") )
        tree.appendChild( cls("root's third child") )
        l2node = cls("open me (root's second child")
        tree.insertChild(1, l2node)
        l2node.appendChild( cls("first inner child") )
        l2node.appendChild( cls("second inner child") )
        return tree


class SkTree(SkNode):
    def __init__(self, name):
        super(SkTree, self).__init__(name)
        self._keys = []

    def type(self):
        return 'ROOT'

    def appendKey(self, key):
        self._keys.append(key)

    def getKeyList(self):
        return self._keys

    # Formerly getEventName
    def getKey(self, subscript):
        if subscript < len(self._keys):
            return self._keys[subscript]

    def getSubscript(self, key):
        pass

    def keyCount(self):
        return len(self._keys)

    def hasKeys(self):
        return bool(len(self._keys))


class SkCommandNode(SkNode):
    def __init__(self, name):
        super(SkCommandNode, self).__init__(name)

    def type(self):
        return 'Command'


class SkLibraryNode(SkNode):
    KO_RE = re.compile(r'\.ko$')
    SO_RE = re.compile(r'\.so(?:\.\d+){0,3}$')
    SYS_RE = re.compile(r'^/lib/')
    BIN_RE = re.compile(r'/(?:usr/(?:local/)?)?bin/')

    def __init__(self, name):
        super(SkLibraryNode, self).__init__(name)
        self._label = os.path.basename(name)
#        print("'%s'" % name)
        self._isaKo   = bool(SkLibraryNode.KO_RE.search(name))
        self._isaSo   = bool(SkLibraryNode.SO_RE.search(name))
        self._isSys   = bool(SkLibraryNode.SYS_RE.search(name))
        self._isBin   = bool(SkLibraryNode.BIN_RE.search(name))
        self._isKern  = name == '[kernel.kallsyms]'
        self._isaVdso = name == '[vdso]'

    def type(self):
        if self._isaKo:
            return 'Kernel module'
        if self._isaSo:
            if self._isSys:
                return 'System library'
            return 'Dynamic library'
        if self._isKern:
            return 'Linux kernel'
        if self._isaVdso:
            return 'Virtual DSO'
        if self._parentHasSameLabel:
            return 'Command binary'
        if self._isBin:
            return 'Binary executed'
        return 'Module'

    def label(self):
        return self._label

    def isaKernelModule(self):
        return self._isaKo

    def isaSystemLibrary(self):
        return self._isSys and self._isaSo


class SkFunctionNode(SkNode):
    PLT_RE  = re.compile(r'@plt$')
    ISRA_RE = re.compile(r'\.isra\.\d+$')
    RSVD_RE = re.compile(r'^_[A-Z_]')

    def __init__(self, name):
        if not name:
            name = '[unknown]'

        super(SkFunctionNode, self).__init__(name)

        self._isaPlt  = bool(SkFunctionNode.PLT_RE.search(name))
        self._isaIsra = bool(SkFunctionNode.ISRA_RE.search(name))
        self._isRsrvd = bool(SkFunctionNode.RSVD_RE.search(name))
        self._unknown = name == "[unknown]"


    def type(self):
        if self._isaPlt:
            return 'Relocation stub'
        if self._isaIsra:
            return 'GCC optimization'
        if self._unknown:
            return 'Any function in module'
        if self._isRsrvd:
            return 'Reserved symbol'

        return 'Function'


    def isaRelocationStub(self):
        return self._isaPlt

    def isaReservedSymbol(self):
        return self._isRsrvd


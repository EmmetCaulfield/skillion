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
        self._text = formula
        bits = SkColumnFormula.RE_CID.split(formula)
        if bits[0] or bits[2]!='=':
            raise SkFormulaSyntaxError('Expected "<label>=..."')
        self._label = bits[1]
        token = list(bits[3:])
        for i in range(len(token)):
            if token[i] in dataKeys:
                self._needkeys.append( token[i] )
                token[i] = "self.getData('" + token[i] +"',True)"
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

        self.name      = name
        self.label     = name
        self._parent   = None
        self._children = []
        self._data      = {}
        self._timestamp = {}
        self._formulas  = {}
        self._parentHasSameLabel = False
        self._color = None
        self._ischecked = False


    def getPath(self):
        if self._parent:
            return self._parent.getPath() +'/'+ self.label
        else:
            return ''

    def appendChild(self, node):
        self._children.append(node)
        if node.label == self.label:
            node._parentHasSameLabel = True
        node._parent = self


    def isJunior(self):
        return self._parentHasSameLabel


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

    def hasKey(self, key):
        return key in self._data or key in self._formulas

    def getData(self, key, calculationMode=False):
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
# This is now moot in calculation mode
#                    if self.getData(k, True) is None:
#                        # A value required by the formula expression is None
#                        doEval = False
#                        break
                if doEval:
                    value = eval( formula.expression() )
                    if value == 0:
                        value = None
                    self._data[key] = value
                    return value

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

        if calculationMode:
            if self._data[key] is None:
                return 0
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
        s += "`---" + self.name + '    ' + str(self._data) + '\n'
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


class SkLibraryNode(SkNode):

    def __init__(self, name):
        super(SkLibraryNode, self).__init__(name)
        self.label = os.path.basename(name)
#        print("'%s'" % name)


class SkFunctionNode(SkNode):
    def __init__(self, name):
        if not name:
            name = '[unknown]'

        super(SkFunctionNode, self).__init__(name)


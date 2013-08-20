#!/usr/bin/python

from PyQt4 import QtSql
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import uic
import sys
import os
import re
import math

"""
    The basic hierarchy presented by 'perf' is comm->dso->symbol, representing
    commands, binary shared/kernel/executable objects or libraries (.so, .ko,
    etc.), and functions respectively.

    In Skillion, this hierarchy is represented by SkNodes, of which there are 4
    different subtypes (with their corresponding `perf` names):

        SkRootNode,
           SkCommandNode (comm),
              SkLibraryNode (dso), and
                 SkFunctionNode (symbol)

    The `SkNode` is an abstract base node, never directly instantiated. There is
    exactly one `SkRootNode`, and the hierarchical relationship is as shown
    above.
"""

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
            raise SkSyntaxError('Expected "<label>=..."')
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
            mimimum = sys.maxint
            for child in self._children:
                tmp = child.getTimestamp()
                if tmp is not None and tmp < minimum:
                    minimum = tmp
            if mimimum != sys.maxint:
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
        for i in range(tabLevel):
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


class SkRootNode(SkNode):
    def __init__(self, name):
        super(SkRootNode, self).__init__(name)
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


class DatabaseError(Exception):
    pass


def _sqlGetList(db, tableName, columnName=None, whereEqual=None, distinct=True):
    qry = QtSql.QSqlQuery(db)
    qry.setForwardOnly(True)

    if columnName is None:
        cols = '*'
    elif isinstance(columnName, str):
        cols = '"' + columnName + '"'
    elif isinstance(columnName,  QtCore.QVariant):
        cols = '"' + str(columnName.toString()) + '"'
    else:
        cols = '"' + ('", "'.join( [str(elt.toString() if isinstance(elt, QtCore.QVariant) else elt) for elt in columnName])) + '"'

    stmt = "SELECT " +("DISTINCT " if distinct else " ")+ cols + ' FROM "%s"' % tableName

    if whereEqual is not None:
#        print( [type(v) for k,v in whereEqual.iteritems()] )
        stmt += ' WHERE ' + ' AND '.join([str(k)+(" IS NULL" if v is None else ("='"+str(v.toString() if isinstance(v, QtCore.QVariant) else v)+"'")) for k,v in whereEqual.iteritems()])

#    print stmt
    if not qry.exec_( stmt ):
        raise DatabaseError("SELECT failed:" + qry.lastError().text())
    numCols = qry.record().count()
    nodes = []
    while( qry.next() ):
        nodes.append( [ qry.value(i) for i in range(numCols) ] )
    return nodes


def _eventTree(db):
    root = SkRootNode('Skillion')
    for row in _sqlGetList(db,  'hierView', 'event'):
        for col in row:
            s = str(col.toString() if isinstance(col, QtCore.QVariant) else col)
            s = s.replace('-', '_')
            root.appendKey(s)

    comms = _sqlGetList(db, 'hierView', 'comm')
    for comm, in comms:
        commStr = str(comm.toString() if isinstance (comm, QtCore.QVariant) else comm)
        commNode = SkCommandNode(commStr)
        root.appendChild(commNode)
        dsos = _sqlGetList(db, 'hierView', 'dso', {'comm':commStr})
        for dso, in dsos:
            dsoStr = str(dso.toString() if isinstance (dso, QtCore.QVariant) else dso)
            dsoNode = SkLibraryNode(dsoStr)
            commNode.appendChild(dsoNode)
            syms = _sqlGetList(db, 'hierView', 'symbol', {'comm':commStr, 'dso':dsoStr})
            for sym, in syms:
                symStr = str(sym.toString() if isinstance (sym, QtCore.QVariant) else sym)
                if not symStr:
                    symStr = None
                symNode = SkFunctionNode(symStr)
                rawData = _sqlGetList(db, 'hierView', ['event', 'tally', 'tsc'], {'comm':commStr, 'dso':dsoStr, 'symbol':symStr}, False )
                for eventName, tally, tsc in rawData:
                    # QVariant has a bug in its toInt() method that necessitates going via QString
                    key = str(eventName.toString()).replace('-', '_')
                    symNode.setData(key, tally.toString().toULongLong()[0])
                    symNode.setTimestamp(key, tsc.toString().toULongLong()[0])
                dsoNode.appendChild(symNode)

    return root

# When subclassing QAbstractItemModel, at the very least you must implement index(), parent(), rowCount(), columnCount(), and data().
class EventTreeModel(QtCore.QAbstractItemModel):
    TREE_COLUMN = 0
    TYPE_COLUMN = 1
    PLOT_COLUMN = 2
    # Expandable tree + row type + check mark (for plotting)
    NONDATA_COLUMN_COUNT = 3

    def __init__(self, arg, parent=None):
        super(EventTreeModel, self).__init__(parent)

        if isinstance(arg, SkNode):
            self._root = arg
        elif isinstance(arg, QtSql.QSqlDatabase):
            self._root = _eventTree(arg)
        elif isinstance(arg, str):
            raise Exception("Not implemented yet")
        else:
            raise Exception("Type error calling constructor")


    def index(self, row, col, parent):
        childSkNode = self._getSkNode(parent).getChild(row)
        return self.createIndex(row, col, childSkNode) if childSkNode else QtCore.QModelIndex()


    def parent(self, index):
        skNode = self._getSkNode(index)
        parentSkNode = skNode.parent()

        # Return an empty QModelIndex if the parent is the root:
        if parentSkNode == self._root:
            return QtCore.QModelIndex()

        # Otherwise, the row is the index of the parent in its parent's array of children:
        return self.createIndex(parentSkNode.parent().indexOf(parentSkNode), 0, parentSkNode)


    def rowCount(self, parent):
        parentSkNode = parent.internalPointer() if parent.isValid() else self._root
        return parentSkNode.childCount()


    def columnCount(self, parent=None):
        return self._root.keyCount() + EventTreeModel.NONDATA_COLUMN_COUNT


    # FIXME: Does the checkbox stuff belong in the proxy model?
    def data(self, index, role):
        if not index.isValid():
            return None

        col = index.column()
        skNode = index.internalPointer()

        if role == QtCore.Qt.DisplayRole:
            if col == EventTreeModel.TREE_COLUMN:
                return skNode.label()
            if col == EventTreeModel.TYPE_COLUMN:
                return skNode.type()
            if col == EventTreeModel.PLOT_COLUMN:
                return None
            else:
                evtName = self._root.getKey(col-EventTreeModel.NONDATA_COLUMN_COUNT)
                return skNode.getData(evtName)

        if role == QtCore.Qt.TextAlignmentRole:
            if col == EventTreeModel.PLOT_COLUMN:
                return QtCore.Qt.AlignCenter
            if col >= EventTreeModel.NONDATA_COLUMN_COUNT:
                return QtCore.Qt.AlignRight

        if role == QtCore.Qt.CheckStateRole and col == EventTreeModel.PLOT_COLUMN:
            return QtCore.Qt.Checked if skNode.isChecked() else QtCore.Qt.Unchecked

        if role == QtCore.Qt.DecorationRole and col == EventTreeModel.PLOT_COLUMN and skNode.isChecked():
            return skNode.getColor()



    def flags(self, index):
        if not index.isValid():
            return None

        f = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if index.column() == EventTreeModel.PLOT_COLUMN:
            return f | QtCore.Qt.ItemIsUserCheckable

        return f


    # FIXME: Does the checkbox stuff belong in the proxy model?
    def setData(self, index, value, role):
        if not index.isValid():
            return None
        col = index.column()
        if col != EventTreeModel.PLOT_COLUMN:
            return False
        if role != QtCore.Qt.CheckStateRole:
            return False
        val = value.toInt()[0]
        index.internalPointer().setChecked( val!=0 )
        self.dataChanged.emit(index, index)
        return True


    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if section == EventTreeModel.TREE_COLUMN:
                return "Command/Module/Function"
            if section == EventTreeModel.TYPE_COLUMN:
                return "Type"
            if section == EventTreeModel.PLOT_COLUMN:
                return "Plot"
            col = section-EventTreeModel.NONDATA_COLUMN_COUNT
            return self._root.getKey(col)


    def addColumnFormula(self, str):
        cc = self.columnCount()
        # If there are 3 nondata columns and 4 data columns, the column count
        # before we add the new column is 7 (cc); so 7 is the right number for
        # the new column index.
#        self.beginInsertColumns(QtCore.QModelIndex(), cc, cc)
        self.beginResetModel()
        formula = SkColumnFormula(str, self._root.getKeyList())
        self._root.setFormula(formula.label(), formula)
#        self.endInsertColumns()
        self.endResetModel()

    def _getSkNode(self, index):
        node = False
        if index.isValid():
            node = index.internalPointer()
        return node if node else self._root;




class SkSortFilterProxyModel(QtGui.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(SkSortFilterProxyModel, self).__init__(parent)

        self._showKernelModules   = True
        self._showSystemLibraries = True
        self._showRelocationStubs = True
        self._showReservedSymbols = True

    def filterAcceptsRow(self, row, parent):
        skNode = parent.internalPointer()
        if skNode is None:
            return True
        skNode = skNode.getChild(row)

        if not self._showKernelModules and skNode.isaKernelModule():
            return False
        if not self._showSystemLibraries and skNode.isaSystemLibrary():
            return False
        if not self._showRelocationStubs and skNode.isaRelocationStub():
            return False
        if not self._showReservedSymbols and skNode.isaReservedSymbol():
            return False
        return True

    def showKernelModules(self, show):
        self._showKernelModules = show

    def showSystemLibraries(self, show):
        self._showSystemLibraries = show

    def showRelocationStubs(self, show):
        self._showRelocationStubs = show

    def showReservedSymbols(self, show):
        self._showReservedSymbols = show

class SkController(object):
    def __init__(self, model, view):
        super(SkController, self).__init__()

        self._model = model
        self._view  = view
        self._proxyModel = SkSortFilterProxyModel()
        self._proxyModel.setSourceModel(model)
        tv = view.uiTreeView
        tv.setModel(self._proxyModel)
        tv.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        tv.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        tv.setSortingEnabled(True)
        tv.setUniformRowHeights(True)

        self.connectTreeView()
        self.connectViewMenu()
        self.connectModelCheckboxes()
# Plot clicks are connected with a HACK
#        self.connectPlotClick()
        self.setupAxisScaleComboBoxes()
        self.setupAxisExtents()
        self.setupEventSelectorComboBoxes()

        view.show()
        view.mplWidget.drawAxes()
        view.mplWidget.drawCpiLines()

# Plot clicks are connected with a HACK
#    def connectPlotClick(self):
#        QtCore.QObject.connect(self._view.mplWidget, QtCore.SIGNAL('pointClicked(QModelIndex)'), self.plotClicked)


    # The index passed in here is, in this case, a source model index
    def plotClicked(self, index):
        if index.isValid():
            pmi = self._proxyModel.mapFromSource(index)
            tsm = self._view.uiTreeView.selectionModel()
            tsm.select(pmi, QtGui.QItemSelectionModel.ClearAndSelect | QtGui.QItemSelectionModel.Rows)
#        print index.internalPointer().getPath()

    def connectTreeView(self):
        QtCore.QObject.connect(self._view.uiTreeView, QtCore.SIGNAL('expanded(QModelIndex)'), self.sizeTreeView)
        QtCore.QObject.connect(self._model, QtCore.SIGNAL('modelReset()'), self.modelReset)


    def sizeTreeView(self, index):
        tv = self._view.uiTreeView
        tv.resizeColumnToContents(0)
        tv.setColumnWidth(1,125)
        tv.setColumnWidth(2,56)
        for i in range(3,self._model.columnCount()):
            tv.setColumnWidth(i,80)


    def connectViewMenu(self):
        v = self._view
        QtCore.QObject.connect(v.actionShow_kernel_modules,   QtCore.SIGNAL('triggered()'), self.updateShowFlags)
        QtCore.QObject.connect(v.actionShow_system_libraries, QtCore.SIGNAL('triggered()'), self.updateShowFlags)
        QtCore.QObject.connect(v.actionShow_relocation_stubs, QtCore.SIGNAL('triggered()'), self.updateShowFlags)
        QtCore.QObject.connect(v.actionShow_reserved_symbols, QtCore.SIGNAL('triggered()'), self.updateShowFlags)
        QtCore.QObject.connect(v.actionAdd_computed_column,   QtCore.SIGNAL('triggered()'), self.addComputedColumn)
        QtCore.QObject.connect(v.uiTreeView, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showTreeContextMenu)
        v.uiTreeView.header().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        QtCore.QObject.connect(v.uiTreeView.header(), QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showTreeHeaderMenu)


    def addComputedColumn(self):
        qstr,ok = QtGui.QInputDialog.getText(self._view, 'Input Formula', 'Formula:')
        if ok:
            self._model.addColumnFormula(str(qstr))


    def connectModelCheckboxes(self):
        m = self._model
        QtCore.QObject.connect(m, QtCore.SIGNAL('dataChanged(QModelIndex,QModelIndex)'), self.checkBoxToggle)


    def checkBoxToggle(self, topLeftIndex, bottomRightIndex):
        if topLeftIndex != bottomRightIndex:
            print "Yikes!"
            return None

        index = topLeftIndex
        if not index.isValid():
            return None

#        skNode = self._proxyModel.mapToSource(index).internalPointer()
        skNode = index.internalPointer()
        xev = str(self._view.xAxisEvent.currentText())
        yev = str(self._view.yAxisEvent.currentText())

        x = skNode.getData(xev)
        y = skNode.getData(yev)

        if not x or not y:
            skNode.setChecked(False)
            QtGui.QMessageBox( QtGui.QMessageBox.Warning, "Skillion Warning",
                "Symbol '{}' has no value for checked plot event '{}'.".format(skNode.label(),yev if x else xev)).exec_()
            return None

        # HACK: Work around not being able to get QtCore.pyqtSignal() to work in SkPlotWidget
        if skNode.isChecked():
            r,g,b = self._view.mplWidget.addPoint( skNode.getPath(), x, y, lambda: self.plotClicked(index) )
            skNode.setColor( QtGui.QColor(int(255*r),int(255*g),int(255*b)) )
        else:
            skNode.setColor( None )
            self._view.mplWidget.removePoint( skNode.getPath() )


    def updateShowFlags(self):
        show = self._view.actionShow_kernel_modules.isChecked()
        self._proxyModel.showKernelModules(show)
        show = self._view.actionShow_system_libraries.isChecked()
        self._proxyModel.showSystemLibraries(show)
        show = self._view.actionShow_relocation_stubs.isChecked()
        self._proxyModel.showRelocationStubs(show)
        show = self._view.actionShow_reserved_symbols.isChecked()
        self._proxyModel.showReservedSymbols(show)
        self._proxyModel.invalidateFilter()


    def setupAxisScaleComboBoxes(self):
        v = self._view
        m = v.mplWidget
        items = ['log10', 'log2', 'lin']
        v.xAxisScale.addItems( items )
        v.xAxisScale.setCurrentIndex(0)
        self.setXAxisScale('log10', draw=False)
        v.yAxisScale.addItems( items )
        v.yAxisScale.setCurrentIndex(0)
        self.setYAxisScale('log10', draw=False)
        QtCore.QObject.connect(v.xAxisScale, QtCore.SIGNAL('currentIndexChanged(QString)'), self.setXAxisScale)
        QtCore.QObject.connect(v.yAxisScale, QtCore.SIGNAL('currentIndexChanged(QString)'), self.setYAxisScale)

    @staticmethod
    def _updateSpinners(lo, hi, base, draw):
        # We need to fetch these values before we set the new spinner maxima/minima:
        if draw:
            lo_base, lo_exp = [int(x) for x in str(lo.text()).split('^')]
            hi_base, hi_exp = [int(x) for x in str(hi.text()).split('^')]

        pfx = str(base)+'^'
        lo.setPrefix( pfx )
        hi.setPrefix( pfx )

        if base==2:
            lo.setMinimum(-1)
            lo.setMaximum(36)
            hi.setMinimum(1)
            hi.setMaximum(37)

        elif base==10:
            lo.setMinimum(-1)
            lo.setMaximum(10)
            hi.setMinimum(0)
            hi.setMaximum(11)

        if draw:
            lo_lin = lo_base**lo_exp
            hi_lin = hi_base**hi_exp
            lo_log = int(math.floor(math.log(lo_lin,base)+0.5))
            hi_log = int(math.floor(math.log(hi_lin,base)+0.5))
            lo.setValue(lo_log)
            hi.setValue(hi_log)


    def setXAxisScale(self, value, draw=True):
        s = str(value)
        v = self._view
        p = v.mplWidget

        if s == 'lin':
            p.setXBase(0, draw)
            return True
        if s == 'log2':
            p.setXBase(2,draw)
            self._updateSpinners(v.xAxisLo,v.xAxisHi,2,draw)
        elif s == 'log10':
            p.setXBase(10, draw)
            self._updateSpinners(v.xAxisLo,v.xAxisHi,10,draw)
        else:
            return False
        return True


    def setYAxisScale(self, value, draw=True):
        s = str(value)
        v = self._view
        p = v.mplWidget

        if s == 'lin':
            p.setYBase(0, draw)
            return True
        if s == 'log2':
            p.setYBase(2,draw)
            self._updateSpinners(v.yAxisLo,v.yAxisHi,2,draw)
        elif s == 'log10':
            p.setYBase(10, draw)
            self._updateSpinners(v.yAxisLo,v.yAxisHi,10,draw)
        else:
            return False
        return True


    def setupEventSelectorComboBoxes(self, reset=False):
        v = self._view
        p = self._view.mplWidget

        if reset:
            v.xAxisEvent.clear()
            v.yAxisEvent.clear()

        # FIXME: ENCAPSULATION
        evlist = self._model._root.getKeyList()
        v.xAxisEvent.addItems( evlist )
        p.setXAxisEvent(evlist[0], draw=False)
        v.yAxisEvent.addItems(evlist)
        p.setYAxisEvent(evlist[1], draw=False)
        v.yAxisEvent.setCurrentIndex(1)

        if not reset:
            QtCore.QObject.connect(v.xAxisEvent, QtCore.SIGNAL('currentIndexChanged(QString)'), p.setXAxisEvent)
            QtCore.QObject.connect(v.yAxisEvent, QtCore.SIGNAL('currentIndexChanged(QString)'), p.setYAxisEvent)


    def modelReset(self):
        """When the model is reset (after adding or deleting a computed column),
        the only thing we really need to do is add or delete items from the
        X/Y picklists"""
        # FIXME: What about when the plot includes a computed column that's
        # just been deleted?
        self.setupEventSelectorComboBoxes(reset=True)


    def setupAxisExtents(self):
        v = self._view
        p = self._view.mplWidget

        p.setXAxisHi('10^6', draw=False)
        p.setYAxisHi('10^6', draw=False)
        p.setXAxisLo('10^0', draw=False)
        p.setYAxisLo('10^0', draw=False)
        QtCore.QObject.connect(v.xAxisLo,   QtCore.SIGNAL('valueChanged(QString)'), p.setXAxisLo)
        QtCore.QObject.connect(v.xAxisHi,   QtCore.SIGNAL('valueChanged(QString)'), p.setXAxisHi)
        QtCore.QObject.connect(v.yAxisLo,   QtCore.SIGNAL('valueChanged(QString)'), p.setYAxisLo)
        QtCore.QObject.connect(v.yAxisHi,   QtCore.SIGNAL('valueChanged(QString)'), p.setYAxisHi)
        QtCore.QObject.connect(v.xAxisAuto, QtCore.SIGNAL('toggled(bool)'), self.setXAxisAuto)
        QtCore.QObject.connect(v.yAxisAuto, QtCore.SIGNAL('toggled(bool)'), self.setYAxisAuto)
        QtCore.QObject.connect(v.cpiLineButton, QtCore.SIGNAL('clicked()'), p.drawCpiLines)



    def setXAxisAuto(self, enabled, draw=True):
        auto = bool(enabled)
        v = self._view
        p = self._view.mplWidget

        v.xAxisLo.setEnabled(not auto)
        v.xAxisHi.setEnabled(not auto)
        p.setXAxisAuto(auto, draw)


    def setYAxisAuto(self, enabled, draw=True):
        auto = bool(enabled)
        v = self._view
        p = self._view.mplWidget

        p.setYAxisAuto(auto, draw)
        v.yAxisLo.setEnabled(not auto)
        v.yAxisHi.setEnabled(not auto)




    def showTreeContextMenu(self, wxy):
        index = self._view.uiTreeView.indexAt(wxy)
        print "Body ctx", wxy, index.row(), index.column()

    def showTreeHeaderMenu(self, wxy):
        pmi = self._view.uiTreeView.indexAt(wxy)
        smi = self._proxyModel.mapToSource(pmi)
        lbl = self._model.headerData(smi.column(), None, QtCore.Qt.DisplayRole)
        print "Header ctx", wxy, lbl


base, form = uic.loadUiType( os.path.dirname(os.path.realpath(__file__))+"/skillion.ui")
class SkillionWindow(base, form):
    def __init__(self, parent=None):
        super(base, self).__init__(parent)
        self.setupUi(self)


if __name__ == '__main__':
    dbfile = "perf.data.db"
    app = QtGui.QApplication(sys.argv)
#    app.setStyle('windowsvista')

    db = QtSql.QSqlDatabase.addDatabase("QSQLITE")

    if not os.path.isfile(dbfile):
        sys.stderr.write("No '%s' file.\n" % dbfile)
        sys.exit(1)

    db.setDatabaseName(dbfile)
    db.open()
    model = EventTreeModel(db)
    db.close()

    view = SkillionWindow()

    con = SkController(model, view)

    sys.exit(app.exec_())

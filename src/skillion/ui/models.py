# When subclassing QAbstractItemModel, at the very least you must implement index(), parent(), rowCount(), columnCount(), and data().

import re

from PyQt4 import QtCore
from PyQt4 import QtGui

from skillion.tree import SkTree, SkColumnFormula, SkCommandNode, SkLibraryNode, SkFunctionNode


class SkTreeModel(QtCore.QAbstractItemModel):
    TREE_COLUMN = 0
    TYPE_COLUMN = 1
    PLOT_COLUMN = 2
    # Expandable tree + node type + check mark (for plotting)
    NONDATA_COLUMN_COUNT = 3

    def __init__(self, arg, parent=None):
        super(SkTreeModel, self).__init__(parent)

        if isinstance(arg, SkTree):
            self._root = arg
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
        return self._root.keyCount() + SkTreeModel.NONDATA_COLUMN_COUNT


    # FIXME: Does the checkbox stuff belong in the proxy model?
    def data(self, index, role):
        if not index.isValid():
            return None

        col = index.column()
        skNode = index.internalPointer()

        if role == QtCore.Qt.DisplayRole:
            if col == SkTreeModel.TREE_COLUMN:
                return skNode.label
            if col == SkTreeModel.TYPE_COLUMN:
                return '[ERROR]'
            if col == SkTreeModel.PLOT_COLUMN:
                return None
            else:
                evtName = self._root.getKey(col-SkTreeModel.NONDATA_COLUMN_COUNT)
                return skNode.getData(evtName)

        if role == QtCore.Qt.TextAlignmentRole:
            if col == SkTreeModel.PLOT_COLUMN:
                return QtCore.Qt.AlignCenter
            if col >= SkTreeModel.NONDATA_COLUMN_COUNT:
                return QtCore.Qt.AlignRight

        if role == QtCore.Qt.CheckStateRole and col == SkTreeModel.PLOT_COLUMN:
            return QtCore.Qt.Checked if skNode.isChecked() else QtCore.Qt.Unchecked

        if role == QtCore.Qt.DecorationRole and col == SkTreeModel.PLOT_COLUMN and skNode.isChecked():
            return skNode.getColor()



    def flags(self, index):
        if not index.isValid():
            return None

        f = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if index.column() == SkTreeModel.PLOT_COLUMN:
            return f | QtCore.Qt.ItemIsUserCheckable

        return f


    # FIXME: Does the checkbox stuff belong in the proxy model?
    def setData(self, index, value, role):
        if not index.isValid():
            return None
        col = index.column()
        if col != SkTreeModel.PLOT_COLUMN:
            return False
        if role != QtCore.Qt.CheckStateRole:
            return False
        val = value.toInt()[0]
        index.internalPointer().setChecked( val!=0 )
        self.dataChanged.emit(index, index)
        return True


    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if section == SkTreeModel.TREE_COLUMN:
                return "Command/Module/Function"
            if section == SkTreeModel.TYPE_COLUMN:
                return "Type"
            if section == SkTreeModel.PLOT_COLUMN:
                return "Plot"
            col = section-SkTreeModel.NONDATA_COLUMN_COUNT
            return self._root.getKey(col)


    def addColumnFormula(self, string):
        # If there are 3 nondata columns and 4 data columns, the column count
        # before we add the new column is 7 (cc); so 7 is the right number for
        # the new column index.
#        cc = self.columnCount()
#        self.beginInsertColumns(QtCore.QModelIndex(), cc, cc)
        self.beginResetModel()
        formula = SkColumnFormula(string, self._root.getKeyList())
        self._root.setFormula(formula.label(), formula)
#        self.endInsertColumns()
        self.endResetModel()


    def _getSkNode(self, index):
        node = False
        if index.isValid():
            node = index.internalPointer()
        return node if node else self._root;



class SkFilter(QtCore.QObject):
    toggled = QtCore.pyqtSignal()

    def __init__(self, klass, attr, regex, name, plural=None, show=True):
        super(SkFilter,self).__init__()
        self.klass = klass
        self.attr  = attr
        self.regex = re.compile(regex)
        self.name  = name
        if plural is None:
            self.plural = name + 's'
        else:
            self.plural = plural
        self.isActive = show

        
    def setActive(self, active):
        if self.isActive == active:
            return
        self.isActive = active
        self.toggled.emit()



class SkSortFilterProxyModel(QtGui.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super(SkSortFilterProxyModel, self).__init__(parent)
        self._filterSet = {}


    def addFilter(self, filter_):
        assert isinstance(filter_, SkFilter)
        if filter_.klass not in self._filterSet:
            self._filterSet[filter_.klass] = []
        self._filterSet[filter_.klass].append(filter_)
        filter_.toggled.connect(self.invalidateFilter)


    def findFilter(self, skNode, activeOnly=True):
        if type(skNode) not in self._filterSet:
            return None

        match = None
        for f in self._filterSet[type(skNode)]:
            if activeOnly and f.isActive:
                continue
            if f.regex.search(skNode.__dict__[f.attr]):
                match = f
                break   
        return match     


    def filterAcceptsRow(self, row, parent):
        skNode = parent.internalPointer()
        if skNode is None:
            return True
        skNode = skNode.getChild(row)

        match = self.findFilter(skNode, activeOnly=True)

        if match is None:
            return True
        
        return False
    
    
    def data(self, index, role):
        smi = self.mapToSource(index)
        if not smi.isValid():
            return None

        # We only use the proxy model data for the "type" column:
        if smi.column() != SkTreeModel.TYPE_COLUMN:
            return self.sourceModel().data(smi, role)
        
        if role != QtCore.Qt.DisplayRole:
            return None
        
        match = self.findFilter(smi.internalPointer(), activeOnly=False)
        if match is not None:
            return match.name.capitalize()
        
        t = type(smi.internalPointer())
        if t == SkFunctionNode:
            return 'Vanilla function'
        if t == SkLibraryNode:
            if smi.internalPointer().isJunior():
                return 'Vanilla binary'
            return 'Vanilla module'
        if t == SkCommandNode:
            return 'Vanilla command'
        

        
        
        


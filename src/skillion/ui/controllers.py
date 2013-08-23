import math

from PyQt4 import QtGui
from PyQt4 import QtCore

from models import SkSortFilterProxyModel
from widgets import SkTreeViewHeaderContextMenu

class SkController(object):
    def __init__(self, model, view):
        super(SkController, self).__init__()

        self._model = model
        self._view  = view
        self._proxyModel = SkSortFilterProxyModel()
        self._proxyModel.setSourceModel(model)
        self._popupMenu = SkTreeViewHeaderContextMenu(view)
        self._dynamicActions = {}
        
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


    def _addColumnAction(self, col):
        label = self._model.headerData(col, None, QtCore.Qt.DisplayRole)
        action = QtGui.QAction(self._view)
        if col<10:
            action.setText("Show column &%d (%s)" % (col,label))
        else:
            action.setText("Show column %d (%s)" % (col,label))
        action.setCheckable(True)
        action.setChecked(True)
        action.setData(col)
        action.toggled.connect(lambda:self.setColumnVisibility(action))
        self._view.menuShow_hide_columns.addAction(action)        


    def connectViewMenu(self):
        v = self._view
        QtCore.QObject.connect(v.actionShow_kernel_modules,   QtCore.SIGNAL('triggered()'), self.updateShowFlags)
        QtCore.QObject.connect(v.actionShow_system_libraries, QtCore.SIGNAL('triggered()'), self.updateShowFlags)
        QtCore.QObject.connect(v.actionShow_relocation_stubs, QtCore.SIGNAL('triggered()'), self.updateShowFlags)
        QtCore.QObject.connect(v.actionShow_reserved_symbols, QtCore.SIGNAL('triggered()'), self.updateShowFlags)
        QtCore.QObject.connect(v.actionAdd_computed_column,   QtCore.SIGNAL('triggered()'), self.addComputedColumn)
        for col in range(3, self._model.columnCount()):
            self._addColumnAction(col)

        QtCore.QObject.connect(v.actionHide_column,           QtCore.SIGNAL('triggered()'), self.hideThisColumn)
        QtCore.QObject.connect(v.uiTreeView, QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showTreeContextMenu)
        v.uiTreeView.header().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        QtCore.QObject.connect(v.uiTreeView.header(), QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.showTreeHeaderMenu)


    def setColumnVisibility(self, action):
        assert isinstance(action, QtGui.QAction)
        column = action.data().toInt()[0]
        if action.isChecked():
            self._view.uiTreeView.header().showSection(column)
        else:
            self._view.uiTreeView.header().hideSection(column)


    def hideThisColumn(self):
        column = self._view.uiTreeView.indexAt(self._popupCoords).column()
        action = self._view.menuShow_hide_columns.actions()[column-self._model.NONDATA_COLUMN_COUNT]
        assert column == action.data().toInt()[0], "Column numbers cannot differ"
        action.setChecked(False)


    def addComputedColumn(self):
        qstr,ok = QtGui.QInputDialog.getText(self._view, 'Input Formula', 'Formula:')
        if not ok:
            return False
        # FIXME: dumb ad-hoc way of checking that adding the formula succeeded
        cc = self._model.columnCount()
        self._model.addColumnFormula(str(qstr))
        if cc+1 == self._model.columnCount():
            self._addColumnAction(cc)


    def connectModelCheckboxes(self):
        m = self._model
        QtCore.QObject.connect(m, QtCore.SIGNAL('dataChanged(QModelIndex,QModelIndex)'), self.checkBoxToggle)


    def checkBoxToggle(self, topLeftIndex, bottomRightIndex):
        assert topLeftIndex == bottomRightIndex, "Indices cannot differ here"
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
            return self.warn("Symbol '{}' has no value for checked plot event '{}'.".format(skNode.label(),yev if x else xev))

        # HACK: Work around not being able to get QtCore.pyqtSignal() to work in SkPlotWidget
        if skNode.isChecked():
            r,g,b = self._view.mplWidget.addPoint( skNode.getPath(), x, y, lambda: self.plotClicked(index) )
            skNode.setColor( QtGui.QColor(int(255*r),int(255*g),int(255*b)) )
        else:
            skNode.setColor( None )
            self._view.mplWidget.removePoint( skNode.getPath() )


    def warn(self, msg, level=QtGui.QMessageBox.Warning):
        QtGui.QMessageBox( level, "Skillion Warning", msg ).exec_()
        return None


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
        self._popupCoords = wxy
        self._popupMenu.exec_(self._view.uiTreeView.mapToGlobal(wxy))
        
        

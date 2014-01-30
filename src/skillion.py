#!/usr/bin/python

import sys
import os

from PyQt4 import QtSql
from PyQt4 import QtGui

from skillion.ui.models import SkTreeModel
from skillion.io.backend import SkSqliteBackend
from skillion.ui.mainwindow import SkMainWindow
from skillion.ui.controllers import SkController


if __name__ == '__main__':
    dbfile = "perf.data.db"
    model  = None

    app = QtGui.QApplication(sys.argv)
#    app.setStyle('windowsvista')

    # If an argument is given, assume it's a filename:
    if len(sys.argv)>1:
        dbfile = sys.argv[1]

    # If we have a filename, try creating a SkTreeModel from it:
    if os.path.isfile(dbfile):
        model = SkTreeModel( SkSqliteBackend.buildSkTree(dbfile) )

    # Open the main window, populated with the model if we have one:
    SkController(SkMainWindow(), model)
    sys.exit(app.exec_())

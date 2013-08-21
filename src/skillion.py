#!/usr/bin/python

import sys
import os

from PyQt4 import QtSql
from PyQt4 import QtGui

from skillion.ui.models import SkTreeModel
from skillion.io.backend import SkSqlBackend
from skillion.ui.mainwindow import SkMainWindow
from skillion.ui.controllers import SkController


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
    rawDataTree = SkSqlBackend.buildSkTree(db)
    db.close()

    con = SkController(SkTreeModel(rawDataTree), SkMainWindow())

    sys.exit(app.exec_())

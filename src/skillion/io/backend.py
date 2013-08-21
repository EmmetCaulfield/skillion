'''
Created on Aug 21, 2013

@author: emmet
'''

from PyQt4 import QtSql
from PyQt4 import QtCore

from skillion.exceptions import SkError, SkAbstractMethodCalled
from skillion.tree import SkTree, SkCommandNode, SkLibraryNode, SkFunctionNode

class SkDatabaseError(SkError):
    pass

class SkBackend(object):
    def __init__(self):
        super(SkBackend,self).__init__()
        
    @classmethod
    def buildSkTree(cls, datasource):
        raise SkAbstractMethodCalled()


class SkSqlBackend(SkBackend):
    @staticmethod
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
            raise SkDatabaseError("SELECT failed:" + qry.lastError().text())
        numCols = qry.record().count()
        nodes = []
        while( qry.next() ):
            nodes.append( [ qry.value(i) for i in range(numCols) ] )
        
        return nodes


    @classmethod
    def buildSkTree(cls, db):
        root = SkTree('Skillion')
        for row in cls._sqlGetList(db,  'hierView', 'event'):
            for col in row:
                s = str(col.toString() if isinstance(col, QtCore.QVariant) else col)
                s = s.replace('-', '_')
                root.appendKey(s)

        comms = cls._sqlGetList(db, 'hierView', 'comm')
        for comm, in comms:
            commStr = str(comm.toString() if isinstance (comm, QtCore.QVariant) else comm)
            commNode = SkCommandNode(commStr)
            root.appendChild(commNode)
            dsos = cls._sqlGetList(db, 'hierView', 'dso', {'comm':commStr})
            for dso, in dsos:
                dsoStr = str(dso.toString() if isinstance (dso, QtCore.QVariant) else dso)
                dsoNode = SkLibraryNode(dsoStr)
                commNode.appendChild(dsoNode)
                syms = cls._sqlGetList(db, 'hierView', 'symbol', {'comm':commStr, 'dso':dsoStr})
                for sym, in syms:
                    symStr = str(sym.toString() if isinstance (sym, QtCore.QVariant) else sym)
                    if not symStr:
                        symStr = None
                    symNode = SkFunctionNode(symStr)
                    rawData = cls._sqlGetList(db, 'hierView', ['event', 'tally', 'tsc'], {'comm':commStr, 'dso':dsoStr, 'symbol':symStr}, False )
                    for eventName, tally, tsc in rawData:
                        # QVariant has a bug in its toInt() method that necessitates going via QString
                        key = str(eventName.toString()).replace('-', '_')
                        symNode.setData(key, tally.toString().toULongLong()[0])
                        symNode.setTimestamp(key, tsc.toString().toULongLong()[0])
                    dsoNode.appendChild(symNode)

        return root

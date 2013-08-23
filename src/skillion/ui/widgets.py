"""Skillion is a Python GUI application that plots an empirical
   roofline based on hardware events"""

import sys
import math

from PyQt4 import QtGui

import numpy
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import colorConverter as ColorConverter

class SkPlotWidget(FigureCanvas):
    def __init__(self,  parent=None):
        self._fig    = Figure( (8, 5), dpi=96 )
        super(SkPlotWidget, self).__init__(self._fig)
        self.setParent(parent)
        self._xbase  = None
        self._ybase  = None
        self._xevent = None
        self._yevent = None
        self._xlim   = None
        self._ylim   = None
        self._points = []
        self._lines  = {}
        self._cpi_lines = []
        self._fontspec = {
            'family': 'sans-serif',
            'weight': 'normal',
            'size': '11'
        }

        matplotlib.rcParams.update({'figure.autolayout': True})
        matplotlib.rc('font', **self._fontspec)
        self.setupMpl(100, 8, 5)
        self.mpl_connect('pick_event', self.onPick)


    def addPoint(self, pid, x, y, callback):
        l=self._axes.plot(x, y, 'o', picker=5)[0]
        self._lines[pid] = l
        l.skCallback = callback
        self.draw()
        return ColorConverter.to_rgb(l.get_color())


    def removePoint(self, pid):
        l = self._lines.pop(pid)
        self._axes.lines.remove(l)
        del l
        self.draw()


    def clearCpiLines(self):
        while self._cpi_lines:
            l = self._cpi_lines.pop()
            self._axes.lines.remove(l)
            del l


    def onPick(self, event):
        event.artist.skCallback()

    def drawCpiLines(self):
        self.clearCpiLines()

        x_lim = self._axes.get_xlim()
        if self._xbase == self._ybase:
            x = numpy.array(x_lim)
        elif self._xbase == 0:
            x = numpy.linspace(x_lim[0], x_lim[1], 100)
        else:
            x = numpy.logspace(math.log(x_lim[0], self._xbase), math.log(x_lim[1],self._xbase), 100, True, self._xbase)

        self._axes.hold(True)
        l,=self._axes.plot(x, x, '-', linewidth=1.0, color='0.5', marker=None, zorder=1)
        self._cpi_lines.append(l)
        for m in range(2,9):
            y = m*x
            l,=self._axes.plot(x, y, '-', linewidth=1.0, color=str(0.5+0.05*m), marker=None, zorder=1)
            self._cpi_lines.append(l)
            y = x/m
            l,=self._axes.plot(x, y, '-', linewidth=1.0, color=str(0.5+0.05*m), marker=None, zorder=1)
            self._cpi_lines.append(l)
        self.draw()


    def setXBase(self, value, draw=True):
        self._xbase = int(str(value))
        if draw:
            self.drawAxes()

    def setYBase(self, value, draw=True):
        self._ybase = int(str(value))
        if draw:
            self.drawAxes()

    @classmethod
    def _parsePow(cls, s):
        n = s.split('^')
        if len(n)==1:
            return 10, int(n[0])
        return int(n[0]), int(n[1])

    def setXAxisLo(self, value, draw=True):
        base,exponent = SkPlotWidget._parsePow(str(value))
        self._xlim = list(self._axes.get_xlim())
        self._xlim[0] = base**exponent
        self._axes.set_xlim(self._xlim)
        if draw:
            self.drawAxes()

    def setXAxisHi(self, value, draw=True):
        base,exponent = SkPlotWidget._parsePow(str(value))
        self._xlim = list(self._axes.get_xlim())
        self._xlim[1] = base**exponent
        self._axes.set_xlim(self._xlim)
        if draw:
            self.drawAxes()

    def setXAxisAuto(self, auto, draw=True):
        if bool(auto):
            self._axes.set_autoscalex_on( True )
        else:
            self._axes.set_autoscalex_on( False )
            self._axes.set_xlim(self._xlim)
        if draw:
            self.drawAxes()
        self.drawCpiLines()


    def setYAxisLo(self, value, draw=True):
        base,exponent = SkPlotWidget._parsePow(str(value))
        self._ylim = list(self._axes.get_ylim())
        self._ylim[0] = base**exponent
        self._axes.set_ylim(self._ylim)
        if draw:
            self.drawAxes()

    def setYAxisHi(self, value, draw=True):
        base,exponent = SkPlotWidget._parsePow(str(value))
        self._ylim = list(self._axes.get_ylim())
        self._ylim[1] = base**exponent
        self._axes.set_ylim(self._ylim)
        if draw:
            self.drawAxes()

    def setYAxisAuto(self, auto, draw=True):
        if bool(auto):
            self._axes.set_autoscaley_on( True )
        else:
            self._axes.set_autoscaley_on( False )
            self._axes.set_ylim(self._ylim)
        if draw:
            self.drawAxes()

    def setXAxisEvent(self, value, draw=True):
        self._xevent = str(value)
        if draw:
            self.drawAxes()

    def setYAxisEvent(self, value, draw=True):
        self._yevent = str(value)
        if draw:
            self.drawAxes()

#    def setXAxisScale(self, value):
#        self._xevent = str(value)

#    def setYAxisEvent(self, value):
#        self._yevent = str(value)


    def drawAxes(self):
        if self._xbase == 0:
            self._axes.set_xscale('linear')
            self._axes.set_xlabel(self._xevent + ' [count]')
        else:
            self._axes.set_xscale('log', basex=self._xbase)
            self._axes.set_xlabel(self._xevent + ' [log_%s(count)]' % self._xbase)

        if self._ybase == 0:
            self._axes.set_yscale('linear')
            self._axes.set_ylabel(self._yevent + ' [count]')
        else:
            self._axes.set_yscale('log', basey=self._ybase)
            self._axes.set_ylabel(self._yevent + ' [log_%s(count)]' % self._ybase)

        self.draw()


    def setupMpl(self,  dpi, xdim, ydim):
        # This allows us to add the subplot configuration widget later
        # if we need to:
        self._axes = self._fig.add_subplot('111')
        self._axes.grid(True, which='both', ls='-', color='0.75')
        self._axes.set_axisbelow(True)
        self._fig.subplots_adjust(bottom=0.15)

        # Bind the mouse motion event for experimental purposes:
#        self.mpl_connect('motion_notify_event', self.on_mousemove)


#    def on_mousemove(self, evt):
        # The event received here is of the type
        # matplotlib.backend_bases.MouseEvent
#        msg = "({},{}), ({:.4},{:.4})".format(int(evt.x), int(evt.y), evt.xdata, evt.ydata)
#        self.statusBar().showMessage( msg )


class SkTreeViewHeaderContextMenu(QtGui.QMenu):
    def __init__(self, parent):
        super(SkTreeViewHeaderContextMenu,self).__init__(parent)
        self.addAction(parent.actionAdd_computed_column)
        self.addAction(parent.actionHide_column)

#    def exec_(self, QtCore.Qt.QModelIndex qmi):



def main():
    app = QtGui.QApplication(sys.argv)
    form = SkPlotWidget()
    form.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


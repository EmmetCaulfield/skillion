'''
Created on Aug 21, 2013

@author: emmet
'''

import os
from PyQt4 import uic

base, form = uic.loadUiType( os.path.dirname(os.path.realpath(__file__))+"/skillion.ui")
class SkMainWindow(base, form):
    def __init__(self, parent=None):
        super(base, self).__init__(parent)
        self.setupUi(self)

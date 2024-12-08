# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2021-2022 Johannes Hermann
#
#  autotag-metadata is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  autotag-metadata is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with autotag-metadata. If not, see
#  <https://www.gnu.org/licenses/>.
# ********************************************************************

from PyQt6 import QtCore
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


class MyEventHandler(PatternMatchingEventHandler, QtCore.QThread):
    create_signal = QtCore.pyqtSignal(str)
    modify_signal = QtCore.pyqtSignal(str)

    def __init__(self, patterns=None):
        super(MyEventHandler, self).__init__(patterns=patterns)
        # self.filename = filename
        # self.signalName = str(filename) + "_modified"

    def on_created(self, event):
        self.create_signal.emit(str(event.src_path))

        # self.create_signal.emit('test')

    def on_modified(self, event):
        self.modify_signal.emit(str(event.src_path))


class FileMonitor(QtCore.QObject):
    def __init__(self, patterns=None):
        super(FileMonitor, self).__init__()
        # self.path = path
        # self.filename = filename
        self.observer = Observer()
        self.event_handler = MyEventHandler(patterns=patterns)

    def blind(self):
        pass

    def run(self):
        pass

    def getEmitter(self):
        return self.event_handler

    # def getSignalName(self):
    #    return self.event_handler.signalName

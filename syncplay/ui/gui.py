from PySide import QtGui
from PySide.QtCore import Qt, QSettings, QSize, QPoint, QUrl, QLine
from syncplay import utils, constants, version
from syncplay.messages import getMessage
import sys
import time
import urllib
from datetime import datetime
import re
import os
from syncplay.utils import formatTime, sameFilename, sameFilesize, sameFileduration, RoomPasswordProvider, formatSize, isURL
from functools import wraps
from twisted.internet import task
lastCheckedForUpdates = None

class UserlistItemDelegate(QtGui.QStyledItemDelegate):
    def __init__(self):
        QtGui.QStyledItemDelegate.__init__(self)

    def sizeHint(self, option, index):
        size = QtGui.QStyledItemDelegate.sizeHint(self, option, index)
        if (index.column() == constants.USERLIST_GUI_USERNAME_COLUMN):
            size.setWidth(size.width() + constants.USERLIST_GUI_USERNAME_OFFSET)
        return size

    def paint(self, itemQPainter, optionQStyleOptionViewItem, indexQModelIndex):
        column = indexQModelIndex.column()
        midY = int((optionQStyleOptionViewItem.rect.y() + optionQStyleOptionViewItem.rect.bottomLeft().y()) / 2)
        if column == constants.USERLIST_GUI_USERNAME_COLUMN:
            currentQAbstractItemModel = indexQModelIndex.model()
            itemQModelIndex = currentQAbstractItemModel.index(indexQModelIndex.row(), constants.USERLIST_GUI_USERNAME_COLUMN, indexQModelIndex.parent())
            if sys.platform.startswith('win'):
                resourcespath = utils.findWorkingDir() + u"\\resources\\"
            else:
                resourcespath = utils.findWorkingDir() + u"/resources/"
            controlIconQPixmap = QtGui.QPixmap(resourcespath + u"user_key.png")
            tickIconQPixmap = QtGui.QPixmap(resourcespath + u"tick.png")
            crossIconQPixmap = QtGui.QPixmap(resourcespath + u"cross.png")
            roomController = currentQAbstractItemModel.data(itemQModelIndex, Qt.UserRole + constants.USERITEM_CONTROLLER_ROLE)
            userReady = currentQAbstractItemModel.data(itemQModelIndex, Qt.UserRole + constants.USERITEM_READY_ROLE)

            if roomController and not controlIconQPixmap.isNull():
                itemQPainter.drawPixmap (
                    optionQStyleOptionViewItem.rect.x()+6,
                    midY-8,
                    controlIconQPixmap.scaled(16, 16, Qt.KeepAspectRatio))

            if userReady and not tickIconQPixmap.isNull():
                itemQPainter.drawPixmap (
                    (optionQStyleOptionViewItem.rect.x()-10),
                    midY - 8,
                    tickIconQPixmap.scaled(16, 16, Qt.KeepAspectRatio))

            elif userReady == False and not crossIconQPixmap.isNull():
                itemQPainter.drawPixmap (
                    (optionQStyleOptionViewItem.rect.x()-10),
                    midY - 8,
                    crossIconQPixmap.scaled(16, 16, Qt.KeepAspectRatio))
            isUserRow = indexQModelIndex.parent() != indexQModelIndex.parent().parent()
            if isUserRow:
                optionQStyleOptionViewItem.rect.setX(optionQStyleOptionViewItem.rect.x()+constants.USERLIST_GUI_USERNAME_OFFSET)
        if column == constants.USERLIST_GUI_FILENAME_COLUMN:
            if sys.platform.startswith('win'):
                resourcespath = utils.findWorkingDir() + u"\\resources\\"
            else:
                resourcespath = utils.findWorkingDir() + u"/resources/"
            currentQAbstractItemModel = indexQModelIndex.model()
            itemQModelIndex = currentQAbstractItemModel.index(indexQModelIndex.row(), constants.USERLIST_GUI_FILENAME_COLUMN, indexQModelIndex.parent())
            fileSwitchRole = currentQAbstractItemModel.data(itemQModelIndex, Qt.UserRole + constants.FILEITEM_SWITCH_ROLE)
            if fileSwitchRole == constants.FILEITEM_SWITCH_FILE_SWITCH:
                fileSwitchIconQPixmap = QtGui.QPixmap(resourcespath + u"film_go.png")
                itemQPainter.drawPixmap (
                    (optionQStyleOptionViewItem.rect.x()),
                    midY - 8,
                    fileSwitchIconQPixmap.scaled(16, 16, Qt.KeepAspectRatio))
                optionQStyleOptionViewItem.rect.setX(optionQStyleOptionViewItem.rect.x()+16)

            elif fileSwitchRole == constants.FILEITEM_SWITCH_STREAM_SWITCH:
                streamSwitchIconQPixmap = QtGui.QPixmap(resourcespath + u"world_go.png")
                itemQPainter.drawPixmap (
                    (optionQStyleOptionViewItem.rect.x()),
                    midY - 8,
                    streamSwitchIconQPixmap.scaled(16, 16, Qt.KeepAspectRatio))
                optionQStyleOptionViewItem.rect.setX(optionQStyleOptionViewItem.rect.x()+16)
        QtGui.QStyledItemDelegate.paint(self, itemQPainter, optionQStyleOptionViewItem, indexQModelIndex)

class MainWindow(QtGui.QMainWindow):
    insertPosition = None
    playlistState = []
    updatingPlaylist = False
    playlistIndex = None

    def setPlaylistInsertPosition(self, newPosition):
        if not self.playlist.isEnabled():
            return
        if MainWindow.insertPosition <> newPosition:
            MainWindow.insertPosition = newPosition
            self.playlist.forceUpdate()

    class PlaylistItemDelegate(QtGui.QStyledItemDelegate):
        def paint(self, itemQPainter, optionQStyleOptionViewItem, indexQModelIndex):
            itemQPainter.save()
            currentQAbstractItemModel = indexQModelIndex.model()
            currentlyPlayingFile = currentQAbstractItemModel.data(indexQModelIndex, Qt.UserRole + constants.PLAYLISTITEM_CURRENTLYPLAYING_ROLE)
            if sys.platform.startswith('win'):
                resourcespath = utils.findWorkingDir() + u"\\resources\\"
            else:
                resourcespath = utils.findWorkingDir() + u"/resources/"
            if currentlyPlayingFile:
                currentlyplayingIconQPixmap = QtGui.QPixmap(resourcespath + u"bullet_right_grey.png")
                midY = int((optionQStyleOptionViewItem.rect.y() + optionQStyleOptionViewItem.rect.bottomLeft().y()) / 2)
                itemQPainter.drawPixmap (
                    (optionQStyleOptionViewItem.rect.x()+4),
                    midY-8,
                    currentlyplayingIconQPixmap.scaled(6, 16, Qt.KeepAspectRatio))
                optionQStyleOptionViewItem.rect.setX(optionQStyleOptionViewItem.rect.x()+10)

            QtGui.QStyledItemDelegate.paint(self, itemQPainter, optionQStyleOptionViewItem, indexQModelIndex)

            lineAbove = False
            lineBelow = False
            if MainWindow.insertPosition == 0 and indexQModelIndex.row() == 0:
                lineAbove = True
            elif MainWindow.insertPosition and indexQModelIndex.row() == MainWindow.insertPosition-1:
                lineBelow = True
            if lineAbove:
                line = QLine(optionQStyleOptionViewItem.rect.topLeft(), optionQStyleOptionViewItem.rect.topRight())
                itemQPainter.drawLine(line)
            elif lineBelow:
                line = QLine(optionQStyleOptionViewItem.rect.bottomLeft(), optionQStyleOptionViewItem.rect.bottomRight())
                itemQPainter.drawLine(line)
            itemQPainter.restore()

    class PlaylistGroupBox(QtGui.QGroupBox):

        def dragEnterEvent(self, event):
            data = event.mimeData()
            urls = data.urls()
            window = self.parent().parent().parent().parent().parent()
            if urls and urls[0].scheme() == 'file':
                event.acceptProposedAction()
                window.setPlaylistInsertPosition(window.playlist.count())
            else:
                super(MainWindow.PlaylistGroupBox, self).dragEnterEvent(event)

        def dragLeaveEvent(self, event):
            window = self.parent().parent().parent().parent().parent()
            window.setPlaylistInsertPosition(None)

        def dropEvent(self, event):
            window = self.parent().parent().parent().parent().parent()
            if not window.playlist.isEnabled():
                return
            window.setPlaylistInsertPosition(None)
            if QtGui.QDropEvent.proposedAction(event) == Qt.MoveAction:
                QtGui.QDropEvent.setDropAction(event, Qt.CopyAction)  # Avoids file being deleted
            data = event.mimeData()
            urls = data.urls()

            if urls and urls[0].scheme() == 'file':
                indexRow = window.playlist.count() if window.clearedPlaylistNote else 0

                for url in urls[::-1]:
                    dropfilepath = os.path.abspath(unicode(url.toLocalFile()))
                    if os.path.isfile(dropfilepath):
                        window.addFileToPlaylist(dropfilepath, indexRow)
                    elif os.path.isdir(dropfilepath):
                        window.addFolderToPlaylist(dropfilepath)
            else:
                super(MainWindow.PlaylistWidget, self).dropEvent(event)

    class PlaylistWidget(QtGui.QListWidget):
        selfWindow = None
        playlistIndexFilename = None

        def setPlaylistIndexFilename(self, filename):
            if filename <> self.playlistIndexFilename:
                self.playlistIndexFilename = filename
            self.updatePlaylistIndexIcon()

        def updatePlaylistIndexIcon(self):
            for item in xrange(self.count()):
                itemFilename = self.item(item).text()
                isPlayingFilename = itemFilename == self.playlistIndexFilename
                self.item(item).setData(Qt.UserRole + constants.PLAYLISTITEM_CURRENTLYPLAYING_ROLE, isPlayingFilename)
                fileIsAvailable = self.selfWindow.isFileAvailable(itemFilename)
                fileIsUntrusted = self.selfWindow.isItemUntrusted(itemFilename)
                if fileIsUntrusted:
                    self.item(item).setForeground(QtGui.QBrush(QtGui.QColor(constants.STYLE_UNTRUSTEDITEM_COLOR)))
                elif fileIsAvailable:
                    self.item(item).setForeground(QtGui.QBrush(QtGui.QColor(QtGui.QPalette.ColorRole(QtGui.QPalette.Text))))
                else:
                    self.item(item).setForeground(QtGui.QBrush(QtGui.QColor(constants.STYLE_DIFFERENTITEM_COLOR)))
            self.selfWindow._syncplayClient.fileSwitch.setFilenameWatchlist(self.selfWindow.newWatchlist)
            self.forceUpdate()

        def setWindow(self, window):
            self.selfWindow = window

        def dragLeaveEvent(self, event):
            window = self.parent().parent().parent().parent().parent().parent()
            window.setPlaylistInsertPosition(None)

        def forceUpdate(self):
            root = self.rootIndex()
            self.dataChanged(root, root)

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Delete:
                self.remove_selected_items()
            else:
                super(MainWindow.PlaylistWidget, self).keyPressEvent(event)

        def updatePlaylist(self, newPlaylist):
            for index in xrange(self.count()):
                self.takeItem(0)
            uniquePlaylist = []
            for item in newPlaylist:
                if item not in uniquePlaylist:
                    uniquePlaylist.append(item)
            self.insertItems(0, uniquePlaylist)
            self.updatePlaylistIndexIcon()

        def remove_selected_items(self):
            for item in self.selectedItems():
                self.takeItem(self.row(item))

        def dragEnterEvent(self, event):
            data = event.mimeData()
            urls = data.urls()
            if urls and urls[0].scheme() == 'file':
                event.acceptProposedAction()
            else:
                super(MainWindow.PlaylistWidget, self).dragEnterEvent(event)

        def dragMoveEvent(self, event):
            data = event.mimeData()
            urls = data.urls()
            if urls and urls[0].scheme() == 'file':
                event.acceptProposedAction()
                indexRow = self.indexAt(event.pos()).row()
                window = self.parent().parent().parent().parent().parent().parent()
                if indexRow == -1 or not window.clearedPlaylistNote:
                    indexRow = window.playlist.count()
                window.setPlaylistInsertPosition(indexRow)
            else:
                super(MainWindow.PlaylistWidget, self).dragMoveEvent(event)

        def dropEvent(self, event):
            window = self.parent().parent().parent().parent().parent().parent()
            if not window.playlist.isEnabled():
                return
            window.setPlaylistInsertPosition(None)
            if QtGui.QDropEvent.proposedAction(event) == Qt.MoveAction:
                QtGui.QDropEvent.setDropAction(event, Qt.CopyAction)  # Avoids file being deleted
            data = event.mimeData()
            urls = data.urls()

            if urls and urls[0].scheme() == 'file':
                indexRow = self.indexAt(event.pos()).row()
                if not window.clearedPlaylistNote:
                    indexRow = 0
                if indexRow == -1:
                    indexRow = window.playlist.count()
                for url in urls[::-1]:
                    dropfilepath = os.path.abspath(unicode(url.toLocalFile()))
                    if os.path.isfile(dropfilepath):
                        window.addFileToPlaylist(dropfilepath, indexRow)
                    elif os.path.isdir(dropfilepath):
                        window.addFolderToPlaylist(dropfilepath)
            else:
                super(MainWindow.PlaylistWidget, self).dropEvent(event)



    class topSplitter(QtGui.QSplitter):
        def createHandle(self):
            return self.topSplitterHandle(self.orientation(), self)

        class topSplitterHandle(QtGui.QSplitterHandle):
            def mouseReleaseEvent(self, event):
                QtGui.QSplitterHandle.mouseReleaseEvent(self, event)
                self.parent().parent().parent().updateListGeometry()

            def mouseMoveEvent(self, event):
                QtGui.QSplitterHandle.mouseMoveEvent(self, event)
                self.parent().parent().parent().updateListGeometry()

    def needsClient(f):  # @NoSelf
        @wraps(f)
        def wrapper(self, *args, **kwds):
            if not self._syncplayClient:
                self.showDebugMessage("Tried to use client before it was ready!")
                return
            return f(self, *args, **kwds)
        return wrapper

    def addClient(self, client):
        self._syncplayClient = client
        self.roomInput.setText(self._syncplayClient.getRoom())
        self.config = self._syncplayClient.getConfig()
        try:
            self.playlistGroup.blockSignals(True)
            self.playlistGroup.setChecked(self.config['sharedPlaylistEnabled'])
            self.playlistGroup.blockSignals(False)
            self._syncplayClient.fileSwitch.setMediaDirectories(self.config["mediaSearchDirectories"])
            if not self.config["mediaSearchDirectories"]:
                self._syncplayClient.ui.showErrorMessage(getMessage("no-media-directories-error"))
            self.updateReadyState(self.config['readyAtStart'])
            autoplayInitialState = self.config['autoplayInitialState']
            if autoplayInitialState is not None:
                self.autoplayPushButton.blockSignals(True)
                self.autoplayPushButton.setChecked(autoplayInitialState)
                self.autoplayPushButton.blockSignals(False)
            if self.config['autoplayMinUsers'] > 1:
                self.autoplayThresholdSpinbox.blockSignals(True)
                self.autoplayThresholdSpinbox.setValue(self.config['autoplayMinUsers'])
                self.autoplayThresholdSpinbox.blockSignals(False)
            self.changeAutoplayState()
            self.changeAutoplayThreshold()
            self.updateAutoPlayIcon()
        except:
            self.showErrorMessage("Failed to load some settings.")
        self.automaticUpdateCheck()

    def promptFor(self, prompt=">", message=""):
        # TODO: Prompt user
        return None

    def setFeatures(self, featureList):
        if not featureList["readiness"]:
            self.readyPushButton.setEnabled(False)
        if not featureList["chat"]:
            self.chatFrame.setEnabled(False)
        if not featureList["sharedPlaylists"]:
            self.playlistGroup.setEnabled(False)

    def showMessage(self, message, noTimestamp=False):
        message = unicode(message)
        username = None
        messageWithUsername = re.match(constants.MESSAGE_WITH_USERNAME_REGEX, message, re.UNICODE)
        if messageWithUsername:
            username = messageWithUsername.group("username")
            message = messageWithUsername.group("message")
        message = message.replace(u"&", u"&amp;").replace(u'"', u"&quot;").replace(u"<", u"&lt;").replace(u">", u"&gt;")
        if username:
            message = constants.STYLE_USER_MESSAGE.format(constants.STYLE_USERNAME, username, message)
        message = message.replace(u"\n", u"<br />")
        if noTimestamp:
            self.newMessage(u"{}<br />".format(message))
        else:
            self.newMessage(time.strftime(constants.UI_TIME_FORMAT, time.localtime()) + message + u"<br />")

    @needsClient
    def getFileSwitchState(self, filename):
        if filename:
            if filename == getMessage("nofile-note"):
                return constants.FILEITEM_SWITCH_NO_SWITCH
            if self._syncplayClient.userlist.currentUser.file and utils.sameFilename(filename,self._syncplayClient.userlist.currentUser.file['name']):
                return constants.FILEITEM_SWITCH_NO_SWITCH
            if isURL(filename):
                return constants.FILEITEM_SWITCH_STREAM_SWITCH
            elif filename not in self.newWatchlist:
                if self._syncplayClient.fileSwitch.findFilepath(filename):
                    return constants.FILEITEM_SWITCH_FILE_SWITCH
                else:
                    self.newWatchlist.extend([filename])
        return constants.FILEITEM_SWITCH_NO_SWITCH

    @needsClient
    def isItemUntrusted(self, filename):
        return isURL(filename) and not self._syncplayClient.isURITrusted(filename)
    
    @needsClient
    def isFileAvailable(self, filename):
        if filename:
            if filename == getMessage("nofile-note"):
                return None
            if isURL(filename):
                return True
            elif filename not in self.newWatchlist:
                if self._syncplayClient.fileSwitch.findFilepath(filename):
                    return True
                else:
                    self.newWatchlist.extend([filename])
        return False

    @needsClient
    def showUserList(self, currentUser, rooms):
        self._usertreebuffer = QtGui.QStandardItemModel()
        self._usertreebuffer.setHorizontalHeaderLabels(
            (getMessage("roomuser-heading-label"), getMessage("size-heading-label"), getMessage("duration-heading-label"), getMessage("filename-heading-label") ))
        usertreeRoot = self._usertreebuffer.invisibleRootItem()
        if self._syncplayClient.userlist.currentUser.file and self._syncplayClient.userlist.currentUser.file and os.path.isfile(self._syncplayClient.userlist.currentUser.file["path"]):
            self._syncplayClient.fileSwitch.setCurrentDirectory(os.path.dirname(self._syncplayClient.userlist.currentUser.file["path"]))

        for room in rooms:
            self.newWatchlist = []
            roomitem = QtGui.QStandardItem(room)
            font = QtGui.QFont()
            font.setItalic(True)
            if room == currentUser.room:
                font.setWeight(QtGui.QFont.Bold)
            roomitem.setFont(font)
            roomitem.setFlags(roomitem.flags() & ~Qt.ItemIsEditable)
            usertreeRoot.appendRow(roomitem)
            isControlledRoom = RoomPasswordProvider.isControlledRoom(room)

            if isControlledRoom:
                if room == currentUser.room and currentUser.isController():
                    roomitem.setIcon(QtGui.QIcon(self.resourcespath + 'lock_open.png'))
                else:
                    roomitem.setIcon(QtGui.QIcon(self.resourcespath + 'lock.png'))
            else:
                roomitem.setIcon(QtGui.QIcon(self.resourcespath + 'chevrons_right.png'))

            for user in rooms[room]:
                useritem = QtGui.QStandardItem(user.username)
                isController = user.isController()
                sameRoom = room == currentUser.room
                if sameRoom:
                    isReadyWithFile = user.isReadyWithFile()
                else:
                    isReadyWithFile = None
                useritem.setData(isController, Qt.UserRole + constants.USERITEM_CONTROLLER_ROLE)
                useritem.setData(isReadyWithFile, Qt.UserRole + constants.USERITEM_READY_ROLE)
                if user.file:
                    filesizeitem = QtGui.QStandardItem(formatSize(user.file['size']))
                    filedurationitem = QtGui.QStandardItem(u"({})".format(formatTime(user.file['duration'])))
                    filename = user.file['name']
                    if isURL(filename):
                        filename = urllib.unquote(filename)
                        try:
                            filename = filename.decode('utf-8')
                        except UnicodeEncodeError:
                            pass
                    filenameitem = QtGui.QStandardItem(filename)
                    fileSwitchState = self.getFileSwitchState(user.file['name']) if room == currentUser.room else None
                    if fileSwitchState != constants.FILEITEM_SWITCH_NO_SWITCH:
                        filenameTooltip = getMessage("switch-to-file-tooltip").format(filename)
                    else:
                        filenameTooltip = filename
                    filenameitem.setToolTip(filenameTooltip)
                    filenameitem.setData(fileSwitchState, Qt.UserRole + constants.FILEITEM_SWITCH_ROLE)
                    if currentUser.file:
                        sameName = sameFilename(user.file['name'], currentUser.file['name'])
                        sameSize = sameFilesize(user.file['size'], currentUser.file['size'])
                        sameDuration = sameFileduration(user.file['duration'], currentUser.file['duration'])
                        underlinefont = QtGui.QFont()
                        underlinefont.setUnderline(True)
                        if sameRoom:
                            if not sameName:
                                filenameitem.setForeground(QtGui.QBrush(QtGui.QColor(constants.STYLE_DIFFERENTITEM_COLOR)))
                                filenameitem.setFont(underlinefont)
                            if not sameSize:
                                if currentUser.file is not None and formatSize(user.file['size']) == formatSize(currentUser.file['size']):
                                    filesizeitem = QtGui.QStandardItem(formatSize(user.file['size'],precise=True))
                                filesizeitem.setFont(underlinefont)
                                filesizeitem.setForeground(QtGui.QBrush(QtGui.QColor(constants.STYLE_DIFFERENTITEM_COLOR)))
                            if not sameDuration:
                                filedurationitem.setForeground(QtGui.QBrush(QtGui.QColor(constants.STYLE_DIFFERENTITEM_COLOR)))
                                filedurationitem.setFont(underlinefont)
                else:
                    filenameitem = QtGui.QStandardItem(getMessage("nofile-note"))
                    filedurationitem = QtGui.QStandardItem("")
                    filesizeitem = QtGui.QStandardItem("")
                    if room == currentUser.room:
                        filenameitem.setForeground(QtGui.QBrush(QtGui.QColor(constants.STYLE_NOFILEITEM_COLOR)))
                font = QtGui.QFont()
                if currentUser.username == user.username:
                    font.setWeight(QtGui.QFont.Bold)
                    self.updateReadyState(currentUser.isReadyWithFile())
                if isControlledRoom and not isController:
                    useritem.setForeground(QtGui.QBrush(QtGui.QColor(constants.STYLE_NOTCONTROLLER_COLOR)))
                useritem.setFont(font)
                useritem.setFlags(useritem.flags() & ~Qt.ItemIsEditable)
                filenameitem.setFlags(filenameitem.flags() & ~Qt.ItemIsEditable)
                filesizeitem.setFlags(filesizeitem.flags() & ~Qt.ItemIsEditable)
                filedurationitem.setFlags(filedurationitem.flags() & ~Qt.ItemIsEditable)
                roomitem.appendRow((useritem, filesizeitem, filedurationitem, filenameitem))
        self.listTreeModel = self._usertreebuffer
        self.listTreeView.setModel(self.listTreeModel)
        self.listTreeView.setItemDelegate(UserlistItemDelegate())
        self.listTreeView.setItemsExpandable(False)
        self.listTreeView.setRootIsDecorated(False)
        self.listTreeView.expandAll()
        self.updateListGeometry()
        self._syncplayClient.fileSwitch.setFilenameWatchlist(self.newWatchlist)

    @needsClient
    def undoPlaylistChange(self):
        self._syncplayClient.playlist.undoPlaylistChange()

    @needsClient
    def shufflePlaylist(self):
        self._syncplayClient.playlist.shufflePlaylist()

    @needsClient
    def openPlaylistMenu(self, position):
        indexes = self.playlist.selectedIndexes()
        if sys.platform.startswith('win'):
            resourcespath = utils.findWorkingDir() + u"\\resources\\"
        else:
            resourcespath = utils.findWorkingDir() + u"/resources/"
        if len(indexes) > 0:
            item = self.playlist.selectedIndexes()[0]
        else:
            item = None
        menu = QtGui.QMenu()

        if item:
            firstFile = item.sibling(item.row(), 0).data()
            pathFound = self._syncplayClient.fileSwitch.findFilepath(firstFile) if not isURL(firstFile) else None
            if self._syncplayClient.userlist.currentUser.file is None or firstFile <> self._syncplayClient.userlist.currentUser.file["name"]:
                if isURL(firstFile):
                    menu.addAction(QtGui.QPixmap(resourcespath + u"world_go.png"), getMessage("openstreamurl-menu-label"), lambda: self.openFile(firstFile))
                elif pathFound:
                        menu.addAction(QtGui.QPixmap(resourcespath + u"film_go.png"), getMessage("openmedia-menu-label"), lambda: self.openFile(pathFound))
            if pathFound:
                menu.addAction(QtGui.QPixmap(resourcespath + u"folder_film.png"),
                               getMessage('open-containing-folder'),
                               lambda: utils.open_system_file_browser(pathFound))
            if self._syncplayClient.isUntrustedTrustableURI(firstFile):
                domain = utils.getDomainFromURL(firstFile)
                menu.addAction(QtGui.QPixmap(resourcespath + u"shield_add.png"),getMessage("addtrusteddomain-menu-label").format(domain), lambda: self.addTrustedDomain(domain))
            menu.addAction(QtGui.QPixmap(resourcespath + u"delete.png"), getMessage("removefromplaylist-menu-label"), lambda: self.deleteSelectedPlaylistItems())
            menu.addSeparator()
        menu.addAction(QtGui.QPixmap(resourcespath + u"arrow_switch.png"), getMessage("shuffleplaylist-menuu-label"), lambda: self.shufflePlaylist())
        menu.addAction(QtGui.QPixmap(resourcespath + u"arrow_undo.png"), getMessage("undoplaylist-menu-label"), lambda: self.undoPlaylistChange())
        menu.addAction(QtGui.QPixmap(resourcespath + u"film_edit.png"), getMessage("editplaylist-menu-label"), lambda: self.openEditPlaylistDialog())
        menu.addAction(QtGui.QPixmap(resourcespath + u"film_add.png"),getMessage("addfilestoplaylist-menu-label"), lambda: self.OpenAddFilesToPlaylistDialog())
        menu.addAction(QtGui.QPixmap(resourcespath + u"world_add.png"), getMessage("addurlstoplaylist-menu-label"), lambda: self.OpenAddURIsToPlaylistDialog())
        menu.addSeparator()
        menu.addAction(QtGui.QPixmap(resourcespath + u"film_folder_edit.png"), getMessage("setmediadirectories-menu-label"), lambda: self.openSetMediaDirectoriesDialog())
        menu.addAction(QtGui.QPixmap(resourcespath + u"shield_edit.png"), getMessage("settrusteddomains-menu-label"), lambda: self.openSetTrustedDomainsDialog())
        menu.exec_(self.playlist.viewport().mapToGlobal(position))


    def openRoomMenu(self, position):
        # TODO: Deselect items after right click
        indexes = self.listTreeView.selectedIndexes()
        if sys.platform.startswith('win'):
            resourcespath = utils.findWorkingDir() + u"\\resources\\"
        else:
            resourcespath = utils.findWorkingDir() + u"/resources/"
        if len(indexes) > 0:
            item = self.listTreeView.selectedIndexes()[0]
        else:
            return

        menu = QtGui.QMenu()
        username = item.sibling(item.row(), 0).data()
        if username == self._syncplayClient.userlist.currentUser.username:
            shortUsername = getMessage("item-is-yours-indicator")
        elif len(username) < 15:
            shortUsername = getMessage("item-is-others-indicator").format(username)
        else:
            shortUsername = u"{}...".format(getMessage("item-is-others-indicator").format(username[0:12])) # TODO: Enforce username limits in client and server

        filename = item.sibling(item.row(), 3).data()
        while item.parent().row() != -1:
            item = item.parent()
        roomToJoin = item.sibling(item.row(), 0).data()
        if roomToJoin <> self._syncplayClient.getRoom():
            menu.addAction(getMessage("joinroom-menu-label").format(roomToJoin), lambda: self.joinRoom(roomToJoin))
        elif username and filename and filename <> getMessage("nofile-note"):
            if self.config['sharedPlaylistEnabled'] and not self.isItemInPlaylist(filename):
                if isURL(filename):
                    menu.addAction(QtGui.QPixmap(resourcespath + u"world_add.png"),getMessage("addusersstreamstoplaylist-menu-label").format(shortUsername), lambda: self.addStreamToPlaylist(filename))
                else:
                    menu.addAction(QtGui.QPixmap(resourcespath + u"film_add.png"), getMessage("addusersfiletoplaylist-menu-label").format(shortUsername), lambda: self.addStreamToPlaylist(filename))

            if self._syncplayClient.userlist.currentUser.file is None or filename <> self._syncplayClient.userlist.currentUser.file["name"]:
                if isURL(filename):
                    menu.addAction(QtGui.QPixmap(resourcespath + u"world_go.png"), getMessage("openusersstream-menu-label").format(shortUsername), lambda: self.openFile(filename))
                else:
                    pathFound = self._syncplayClient.fileSwitch.findFilepath(filename)
                    if pathFound:
                        menu.addAction(QtGui.QPixmap(resourcespath + u"film_go.png"), getMessage("openusersfile-menu-label").format(shortUsername), lambda: self.openFile(pathFound))
            if self._syncplayClient.isUntrustedTrustableURI(filename):
                domain = utils.getDomainFromURL(filename)
                menu.addAction(QtGui.QPixmap(resourcespath + u"shield_add.png"),getMessage("addtrusteddomain-menu-label").format(domain), lambda: self.addTrustedDomain(domain))

            if not isURL(filename) and filename <> getMessage("nofile-note"):
                path = self._syncplayClient.fileSwitch.findFilepath(filename)
                if path:
                    menu.addAction(QtGui.QPixmap(resourcespath + u"folder_film.png"), getMessage('open-containing-folder'), lambda: utils.open_system_file_browser(path))
        else:
            return
        menu.exec_(self.listTreeView.viewport().mapToGlobal(position))

    def updateListGeometry(self):
        try:
            roomtocheck = 0
            while self.listTreeModel.item(roomtocheck):
                self.listTreeView.setFirstColumnSpanned(roomtocheck, self.listTreeView.rootIndex(), True)
                roomtocheck += 1
            self.listTreeView.header().setStretchLastSection(False)
            self.listTreeView.header().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
            self.listTreeView.header().setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
            self.listTreeView.header().setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
            self.listTreeView.header().setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
            NarrowTabsWidth = self.listTreeView.header().sectionSize(0)+self.listTreeView.header().sectionSize(1)+self.listTreeView.header().sectionSize(2)
            if self.listTreeView.header().width() < (NarrowTabsWidth+self.listTreeView.header().sectionSize(3)):
                self.listTreeView.header().resizeSection(3,self.listTreeView.header().width()-NarrowTabsWidth)
            else:
                self.listTreeView.header().setResizeMode(3, QtGui.QHeaderView.Stretch)
            self.listTreeView.expandAll()
        except:
            pass

    def updateReadyState(self, newState):
        oldState = self.readyPushButton.isChecked()
        if newState != oldState and newState != None:
            self.readyPushButton.blockSignals(True)
            self.readyPushButton.setChecked(newState)
            self.readyPushButton.blockSignals(False)
        self.updateReadyIcon()

    @needsClient
    def playlistItemClicked(self, item):
        # TODO: Integrate into client.py code
        filename = item.data()
        if self._isTryingToChangeToCurrentFile(filename):
            return
        if isURL(filename):
            self._syncplayClient._player.openFile(filename)
        else:
            pathFound = self._syncplayClient.fileSwitch.findFilepath(filename, highPriority=True)
            if pathFound:
                self._syncplayClient._player.openFile(pathFound)
            else:
                self._syncplayClient.ui.showErrorMessage(getMessage("cannot-find-file-for-playlist-switch-error").format(filename))

    def _isTryingToChangeToCurrentFile(self, filename):
        if self._syncplayClient.userlist.currentUser.file and filename == self._syncplayClient.userlist.currentUser.file["name"]:
            self.showDebugMessage("File change request ignored (Syncplay should not be asked to change to current filename)")
            return True
        else:
            return False

    def roomClicked(self, item):
        username = item.sibling(item.row(), 0).data()
        filename = item.sibling(item.row(), 3).data()
        while item.parent().row() != -1:
            item = item.parent()
        roomToJoin = item.sibling(item.row(), 0).data()
        if roomToJoin <> self._syncplayClient.getRoom():
            self.joinRoom(item.sibling(item.row(), 0).data())
        elif username and filename and username <> self._syncplayClient.userlist.currentUser.username:
            if self._isTryingToChangeToCurrentFile(filename):
                return
            if isURL(filename):
                self._syncplayClient._player.openFile(filename)
            else:
                pathFound = self._syncplayClient.fileSwitch.findFilepath(filename, highPriority=True)
                if pathFound:
                    self._syncplayClient._player.openFile(pathFound)
                else:
                    self._syncplayClient.fileSwitch.updateInfo()
                    self.showErrorMessage(getMessage("switch-file-not-found-error").format(filename))

    @needsClient
    def userListChange(self):
        self._syncplayClient.showUserList()

    def fileSwitchFoundFiles(self):
        self._syncplayClient.showUserList()
        self.playlist.updatePlaylistIndexIcon()

    def updateRoomName(self, room=""):
        self.roomInput.setText(room)

    def showDebugMessage(self, message):
        print(message)

    def showErrorMessage(self, message, criticalerror=False):
        message = unicode(message)
        if criticalerror:
            QtGui.QMessageBox.critical(self, "Syncplay", message)
        message = message.replace(u"&", u"&amp;").replace(u'"', u"&quot;").replace(u"<", u"&lt;").replace(u">", u"&gt;")
        message = message.replace(u"\n", u"<br />")
        message = u"<span style=\"{}\">".format(constants.STYLE_ERRORNOTIFICATION) + message + u"</span>"
        self.newMessage(time.strftime(constants.UI_TIME_FORMAT, time.localtime()) + message + u"<br />")

    @needsClient
    def joinRoom(self, room=None):
        if room == None:
            room = self.roomInput.text()
        if room == "":
            if self._syncplayClient.userlist.currentUser.file:
                room = self._syncplayClient.userlist.currentUser.file["name"]
            else:
                room = self._syncplayClient.defaultRoom
        self.roomInput.setText(room)
        if room != self._syncplayClient.getRoom():
            self._syncplayClient.setRoom(room, resetAutoplay=True)
            self._syncplayClient.sendRoom()

    def seekPositionDialog(self):
        seekTime, ok = QtGui.QInputDialog.getText(self, getMessage("seektime-menu-label"),
                                                   getMessage("seektime-msgbox-label"), QtGui.QLineEdit.Normal,
                                                   u"0:00")
        if ok and seekTime != '':
            self.seekPosition(seekTime)



    def seekFromButton(self):
        self.seekPosition(self.seekInput.text())

    @needsClient
    def seekPosition(self, seekTime):
        s = re.match(constants.UI_SEEK_REGEX, seekTime)
        if s:
            sign = self._extractSign(s.group('sign'))
            t = utils.parseTime(s.group('time'))
            if t is None:
                return
            if sign:
                t = self._syncplayClient.getGlobalPosition() + sign * t
            self._syncplayClient.setPosition(t)
        else:
            self.showErrorMessage(getMessage("invalid-seek-value"))

    @needsClient
    def undoSeek(self):
        tmp_pos = self._syncplayClient.getPlayerPosition()
        self._syncplayClient.setPosition(self._syncplayClient.playerPositionBeforeLastSeek)
        self._syncplayClient.playerPositionBeforeLastSeek = tmp_pos

    @needsClient
    def togglePause(self):
        self._syncplayClient.setPaused(not self._syncplayClient.getPlayerPaused())

    @needsClient
    def play(self):
        self._syncplayClient.setPaused(False)

    @needsClient
    def pause(self):
        self._syncplayClient.setPaused(True)

    @needsClient
    def exitSyncplay(self):
        self._syncplayClient.stop()

    def closeEvent(self, event):
        self.exitSyncplay()
        self.saveSettings()

    def loadMediaBrowseSettings(self):
        settings = QSettings("Syncplay", "MediaBrowseDialog")
        settings.beginGroup("MediaBrowseDialog")
        self.mediadirectory = settings.value("mediadir", "")
        settings.endGroup()

    def saveMediaBrowseSettings(self):
        settings = QSettings("Syncplay", "MediaBrowseDialog")
        settings.beginGroup("MediaBrowseDialog")
        settings.setValue("mediadir", self.mediadirectory)
        settings.endGroup()

    def getInitialMediaDirectory(self, includeUserSpecifiedDirectories=True):
        if self.config["mediaSearchDirectories"] and os.path.isdir(self.config["mediaSearchDirectories"][0]) and includeUserSpecifiedDirectories:
            defaultdirectory = self.config["mediaSearchDirectories"][0]
        elif includeUserSpecifiedDirectories and os.path.isdir(self.mediadirectory):
            defaultdirectory = self.mediadirectory
        elif os.path.isdir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.MoviesLocation)):
            defaultdirectory = QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.MoviesLocation)
        elif os.path.isdir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation)):
            defaultdirectory = QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation)
        else:
            defaultdirectory = ""
        return defaultdirectory

    @needsClient
    def browseMediapath(self):
        if self._syncplayClient._player.customOpenDialog == True:
            self._syncplayClient._player.openCustomOpenDialog()
            return

        self.loadMediaBrowseSettings()
        options = QtGui.QFileDialog.Options()
        self.mediadirectory = ""
        currentdirectory = os.path.dirname(self._syncplayClient.userlist.currentUser.file["path"]) if self._syncplayClient.userlist.currentUser.file else None
        if currentdirectory and os.path.isdir(currentdirectory):
            defaultdirectory = currentdirectory
        else:
            defaultdirectory = self.getInitialMediaDirectory()
        browserfilter = "All files (*)"
        fileName, filtr = QtGui.QFileDialog.getOpenFileName(self, getMessage("browseformedia-label"), defaultdirectory,
                                                            browserfilter, "", options)
        if fileName:
            if sys.platform.startswith('win'):
                fileName = fileName.replace("/", "\\")
            self.mediadirectory = os.path.dirname(fileName)
            self._syncplayClient.fileSwitch.setCurrentDirectory(self.mediadirectory)
            self.saveMediaBrowseSettings()
            self._syncplayClient._player.openFile(fileName)

    @needsClient
    def OpenAddFilesToPlaylistDialog(self):
        if self._syncplayClient._player.customOpenDialog == True:
            self._syncplayClient._player.openCustomOpenDialog()
            return

        self.loadMediaBrowseSettings()
        options = QtGui.QFileDialog.Options()
        self.mediadirectory = ""
        currentdirectory = os.path.dirname(self._syncplayClient.userlist.currentUser.file["path"]) if self._syncplayClient.userlist.currentUser.file else None
        if currentdirectory and os.path.isdir(currentdirectory):
            defaultdirectory = currentdirectory
        else:
            defaultdirectory = self.getInitialMediaDirectory()
        browserfilter = "All files (*)"
        fileNames, filtr = QtGui.QFileDialog.getOpenFileNames(self, getMessage("browseformedia-label"), defaultdirectory,
                                                            browserfilter, "", options)
        self.updatingPlaylist = True
        if fileNames:
            for fileName in fileNames:
                if sys.platform.startswith('win'):
                    fileName = fileName.replace("/", "\\")
                self.mediadirectory = os.path.dirname(fileName)
                self._syncplayClient.fileSwitch.setCurrentDirectory(self.mediadirectory)
                self.saveMediaBrowseSettings()
                self.addFileToPlaylist(fileName)
        self.updatingPlaylist = False
        self.playlist.updatePlaylist(self.getPlaylistState())

    @needsClient
    def OpenAddURIsToPlaylistDialog(self):
        URIsDialog = QtGui.QDialog()
        URIsDialog.setWindowTitle(getMessage("adduris-msgbox-label"))
        URIsLayout = QtGui.QGridLayout()
        URIsLabel = QtGui.QLabel(getMessage("adduris-msgbox-label"))
        URIsLayout.addWidget(URIsLabel, 0, 0, 1, 1)
        URIsTextbox = QtGui.QPlainTextEdit()
        URIsTextbox.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        URIsLayout.addWidget(URIsTextbox, 1, 0, 1, 1)
        URIsButtonBox = QtGui.QDialogButtonBox()
        URIsButtonBox.setOrientation(Qt.Horizontal)
        URIsButtonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel)
        URIsButtonBox.accepted.connect(URIsDialog.accept)
        URIsButtonBox.rejected.connect(URIsDialog.reject)
        URIsLayout.addWidget(URIsButtonBox, 2, 0, 1, 1)
        URIsDialog.setLayout(URIsLayout)
        URIsDialog.setModal(True)
        URIsDialog.show()
        result = URIsDialog.exec_()
        if result == QtGui.QDialog.Accepted:
            URIsToAdd = utils.convertMultilineStringToList(URIsTextbox.toPlainText())
            self.updatingPlaylist = True
            for URI in URIsToAdd:
                URI = URI.rstrip()
                try:
                    URI = URI.encode('utf-8')
                except UnicodeDecodeError:
                    pass
                URI = urllib.unquote(URI)
                URI = URI.decode('utf-8')
                if URI <> "":
                    self.addStreamToPlaylist(URI)
            self.updatingPlaylist = False

    @needsClient
    def openEditPlaylistDialog(self):
        oldPlaylist = utils.getListAsMultilineString(self.getPlaylistState())
        editPlaylistDialog = QtGui.QDialog()
        editPlaylistDialog.setWindowTitle(getMessage("editplaylist-msgbox-label"))
        editPlaylistLayout = QtGui.QGridLayout()
        editPlaylistLabel = QtGui.QLabel(getMessage("editplaylist-msgbox-label"))
        editPlaylistLayout.addWidget(editPlaylistLabel, 0, 0, 1, 1)
        editPlaylistTextbox = QtGui.QPlainTextEdit(oldPlaylist)
        editPlaylistTextbox.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        editPlaylistLayout.addWidget(editPlaylistTextbox, 1, 0, 1, 1)
        editPlaylistButtonBox = QtGui.QDialogButtonBox()
        editPlaylistButtonBox.setOrientation(Qt.Horizontal)
        editPlaylistButtonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel)
        editPlaylistButtonBox.accepted.connect(editPlaylistDialog.accept)
        editPlaylistButtonBox.rejected.connect(editPlaylistDialog.reject)
        editPlaylistLayout.addWidget(editPlaylistButtonBox, 2, 0, 1, 1)
        editPlaylistDialog.setLayout(editPlaylistLayout)
        editPlaylistDialog.setModal(True)
        editPlaylistDialog.setMinimumWidth(600)
        editPlaylistDialog.setMinimumHeight(500)
        editPlaylistDialog.show()
        result = editPlaylistDialog.exec_()
        if result == QtGui.QDialog.Accepted:
            newPlaylist = utils.convertMultilineStringToList(editPlaylistTextbox.toPlainText())
            if newPlaylist <> self.playlistState and self._syncplayClient and not self.updatingPlaylist:
                self.setPlaylist(newPlaylist)
                self._syncplayClient.playlist.changePlaylist(newPlaylist)
                self._syncplayClient.fileSwitch.updateInfo()

    @needsClient
    def openSetMediaDirectoriesDialog(self):
        MediaDirectoriesDialog = QtGui.QDialog()
        MediaDirectoriesDialog.setWindowTitle(getMessage("syncplay-mediasearchdirectories-title")) # TODO: Move to messages_*.py
        MediaDirectoriesLayout = QtGui.QGridLayout()
        MediaDirectoriesLabel = QtGui.QLabel(getMessage("syncplay-mediasearchdirectories-title"))
        MediaDirectoriesLayout.addWidget(MediaDirectoriesLabel, 0, 0, 1, 2)
        MediaDirectoriesTextbox = QtGui.QPlainTextEdit()
        MediaDirectoriesTextbox.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        MediaDirectoriesTextbox.setPlainText(utils.getListAsMultilineString(self.config["mediaSearchDirectories"]))
        MediaDirectoriesLayout.addWidget(MediaDirectoriesTextbox, 1, 0, 1, 1)
        MediaDirectoriesButtonBox = QtGui.QDialogButtonBox()
        MediaDirectoriesButtonBox.setOrientation(Qt.Horizontal)
        MediaDirectoriesButtonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel)
        MediaDirectoriesButtonBox.accepted.connect(MediaDirectoriesDialog.accept)
        MediaDirectoriesButtonBox.rejected.connect(MediaDirectoriesDialog.reject)
        MediaDirectoriesLayout.addWidget(MediaDirectoriesButtonBox, 2, 0, 1, 1)
        MediaDirectoriesAddFolderButton = QtGui.QPushButton(getMessage("addfolder-label"))
        MediaDirectoriesAddFolderButton.pressed.connect(lambda: self.openAddMediaDirectoryDialog(MediaDirectoriesTextbox, MediaDirectoriesDialog))
        MediaDirectoriesLayout.addWidget(MediaDirectoriesAddFolderButton, 1, 1, 1, 1, Qt.AlignTop)
        MediaDirectoriesDialog.setLayout(MediaDirectoriesLayout)
        MediaDirectoriesDialog.setModal(True)
        MediaDirectoriesDialog.show()
        result = MediaDirectoriesDialog.exec_()
        if result == QtGui.QDialog.Accepted:
            newMediaDirectories = utils.convertMultilineStringToList(MediaDirectoriesTextbox.toPlainText())
            self._syncplayClient.fileSwitch.changeMediaDirectories(newMediaDirectories)

    @needsClient
    def openSetTrustedDomainsDialog(self):
        TrustedDomainsDialog = QtGui.QDialog()
        TrustedDomainsDialog.setWindowTitle(getMessage("syncplay-trusteddomains-title"))
        TrustedDomainsLayout = QtGui.QGridLayout()
        TrustedDomainsLabel = QtGui.QLabel(getMessage("trusteddomains-msgbox-label"))
        TrustedDomainsLayout.addWidget(TrustedDomainsLabel, 0, 0, 1, 1)
        TrustedDomainsTextbox = QtGui.QPlainTextEdit()
        TrustedDomainsTextbox.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        TrustedDomainsTextbox.setPlainText(utils.getListAsMultilineString(self.config["trustedDomains"]))
        TrustedDomainsLayout.addWidget(TrustedDomainsTextbox, 1, 0, 1, 1)
        TrustedDomainsButtonBox = QtGui.QDialogButtonBox()
        TrustedDomainsButtonBox.setOrientation(Qt.Horizontal)
        TrustedDomainsButtonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel)
        TrustedDomainsButtonBox.accepted.connect(TrustedDomainsDialog.accept)
        TrustedDomainsButtonBox.rejected.connect(TrustedDomainsDialog.reject)
        TrustedDomainsLayout.addWidget(TrustedDomainsButtonBox, 2, 0, 1, 1)
        TrustedDomainsDialog.setLayout(TrustedDomainsLayout)
        TrustedDomainsDialog.setModal(True)
        TrustedDomainsDialog.show()
        result = TrustedDomainsDialog.exec_()
        if result == QtGui.QDialog.Accepted:
            newTrustedDomains = utils.convertMultilineStringToList(TrustedDomainsTextbox.toPlainText())
            self._syncplayClient.setTrustedDomains(newTrustedDomains)
    @needsClient
    def addTrustedDomain(self, newDomain):
        trustedDomains = self.config["trustedDomains"][:]
        if newDomain:
            trustedDomains.append(newDomain)
            self._syncplayClient.setTrustedDomains(trustedDomains)

    @needsClient
    def openAddMediaDirectoryDialog(self, MediaDirectoriesTextbox, MediaDirectoriesDialog):
        folderName = unicode(QtGui.QFileDialog.getExistingDirectory(self,None,self.getInitialMediaDirectory(includeUserSpecifiedDirectories=False),QtGui.QFileDialog.ShowDirsOnly))
        if folderName:
            existingMediaDirs = MediaDirectoriesTextbox.toPlainText()
            if existingMediaDirs == "":
                newMediaDirList = folderName
            else:
                newMediaDirList = existingMediaDirs + u"\n" + folderName
            MediaDirectoriesTextbox.setPlainText(newMediaDirList)
        MediaDirectoriesDialog.raise_()
        MediaDirectoriesDialog.activateWindow()

    @needsClient
    def promptForStreamURL(self):
        streamURL, ok = QtGui.QInputDialog.getText(self, getMessage("promptforstreamurl-msgbox-label"),
                                                   getMessage("promptforstreamurlinfo-msgbox-label"), QtGui.QLineEdit.Normal,
                                                   "")
        if ok and streamURL != '':
            self._syncplayClient._player.openFile(streamURL)

    @needsClient
    def createControlledRoom(self):
        controlroom, ok = QtGui.QInputDialog.getText(self, getMessage("createcontrolledroom-msgbox-label"),
                getMessage("controlledroominfo-msgbox-label"), QtGui.QLineEdit.Normal,
                utils.stripRoomName(self._syncplayClient.getRoom()))
        if ok and controlroom != '':
            self._syncplayClient.createControlledRoom(controlroom)

    @needsClient
    def identifyAsController(self):
        msgboxtitle = getMessage("identifyascontroller-msgbox-label")
        msgboxtext = getMessage("identifyinfo-msgbox-label")
        controlpassword, ok = QtGui.QInputDialog.getText(self, msgboxtitle, msgboxtext, QtGui.QLineEdit.Normal, "")
        if ok and controlpassword != '':
            self._syncplayClient.identifyAsController(controlpassword)

    def _extractSign(self, m):
        if m:
            if m == "-":
                return -1
            else:
                return 1
        else:
            return None

    @needsClient
    def setOffset(self):
        newoffset, ok = QtGui.QInputDialog.getText(self, getMessage("setoffset-msgbox-label"),
                                                   getMessage("offsetinfo-msgbox-label"), QtGui.QLineEdit.Normal,
                                                   "")
        if ok and newoffset != '':
            o = re.match(constants.UI_OFFSET_REGEX, "o " + newoffset)
            if o:
                sign = self._extractSign(o.group('sign'))
                t = utils.parseTime(o.group('time'))
                if t is None:
                    return
                if o.group('sign') == "/":
                    t = self._syncplayClient.getPlayerPosition() - t
                elif sign:
                    t = self._syncplayClient.getUserOffset() + sign * t
                self._syncplayClient.setUserOffset(t)
            else:
                self.showErrorMessage(getMessage("invalid-offset-value"))

    def openUserGuide(self):
        if sys.platform.startswith('linux'):
            self.QtGui.QDesktopServices.openUrl(QUrl("http://syncplay.pl/guide/linux/"))
        elif sys.platform.startswith('win'):
            self.QtGui.QDesktopServices.openUrl(QUrl("http://syncplay.pl/guide/windows/"))
        else:
            self.QtGui.QDesktopServices.openUrl(QUrl("http://syncplay.pl/guide/"))

    def drop(self):
        self.close()

    def getPlaylistState(self):
        playlistItems = []
        for playlistItem in xrange(self.playlist.count()):
            playlistItemText = self.playlist.item(playlistItem).text()
            if playlistItemText <> getMessage("playlist-instruction-item-message"):
                playlistItems.append(playlistItemText)
        return playlistItems

    def playlistChangeCheck(self):
        if self.updatingPlaylist:
            return
        newPlaylist = self.getPlaylistState()
        if newPlaylist <> self.playlistState and self._syncplayClient and not self.updatingPlaylist:
            self.playlistState = newPlaylist
            self._syncplayClient.playlist.changePlaylist(newPlaylist)
            self._syncplayClient.fileSwitch.updateInfo()

    def sendChatMessage(self):
        if self.chatInput.text() <> "":
            self._syncplayClient.sendChat(self.chatInput.text())
            self.chatInput.setText("")

    def addTopLayout(self, window):
        window.topSplit = self.topSplitter(Qt.Horizontal, self)

        window.outputLayout = QtGui.QVBoxLayout()
        window.outputbox = QtGui.QTextBrowser()
        window.outputbox.setReadOnly(True)
        window.outputbox.setTextInteractionFlags(window.outputbox.textInteractionFlags() | Qt.TextSelectableByKeyboard)
        window.outputbox.setOpenExternalLinks(True)
        window.outputbox.unsetCursor()
        window.outputbox.moveCursor(QtGui.QTextCursor.End)
        window.outputbox.insertHtml(constants.STYLE_CONTACT_INFO.format(getMessage("contact-label")))
        window.outputbox.moveCursor(QtGui.QTextCursor.End)
        window.outputbox.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        window.outputlabel = QtGui.QLabel(getMessage("notifications-heading-label"))
        window.chatInput = QtGui.QLineEdit()
        window.chatInput.setMaxLength(constants.MAX_CHAT_MESSAGE_LENGTH)
        window.chatInput.returnPressed.connect(self.sendChatMessage)
        window.chatButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + 'email_go.png'),
                                              getMessage("sendmessage-label"))
        window.chatButton.pressed.connect(self.sendChatMessage)
        window.chatLayout = QtGui.QHBoxLayout()
        window.chatFrame = QtGui.QFrame()
        window.chatFrame.setLayout(self.chatLayout)
        window.chatFrame.setContentsMargins(0,0,0,0)
        window.chatFrame.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        window.chatLayout.setContentsMargins(0,0,0,0)
        self.chatButton.setToolTip(getMessage("sendmessage-tooltip"))
        window.chatLayout.addWidget(window.chatInput)
        window.chatLayout.addWidget(window.chatButton)
        window.chatFrame.setMaximumHeight(window.chatFrame.sizeHint().height())
        window.outputFrame = QtGui.QFrame()
        window.outputFrame.setLineWidth(0)
        window.outputFrame.setMidLineWidth(0)
        window.outputLayout.setContentsMargins(0, 0, 0, 0)
        window.outputLayout.addWidget(window.outputlabel)
        window.outputLayout.addWidget(window.outputbox)
        window.outputLayout.addWidget(window.chatFrame)
        window.outputFrame.setLayout(window.outputLayout)

        window.listLayout = QtGui.QVBoxLayout()
        window.listTreeModel = QtGui.QStandardItemModel()
        window.listTreeView = QtGui.QTreeView()
        window.listTreeView.setModel(window.listTreeModel)
        window.listTreeView.setIndentation(21)
        window.listTreeView.doubleClicked.connect(self.roomClicked)
        self.listTreeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listTreeView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.listTreeView.customContextMenuRequested.connect(self.openRoomMenu)
        window.listlabel = QtGui.QLabel(getMessage("userlist-heading-label"))
        window.listFrame = QtGui.QFrame()
        window.listFrame.setLineWidth(0)
        window.listFrame.setMidLineWidth(0)
        window.listFrame.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        window.listLayout.setContentsMargins(0, 0, 0, 0)

        window.userlistLayout = QtGui.QVBoxLayout()
        window.userlistFrame = QtGui.QFrame()
        window.userlistFrame.setLineWidth(0)
        window.userlistFrame.setMidLineWidth(0)
        window.userlistFrame.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        window.userlistLayout.setContentsMargins(0, 0, 0, 0)
        window.userlistFrame.setLayout(window.userlistLayout)
        window.userlistLayout.addWidget(window.listlabel)
        window.userlistLayout.addWidget(window.listTreeView)

        window.listSplit = QtGui.QSplitter(Qt.Vertical, self)
        window.listSplit.addWidget(window.userlistFrame)
        window.listLayout.addWidget(window.listSplit)

        window.roomInput = QtGui.QLineEdit()
        window.roomInput.setMaxLength(constants.MAX_ROOM_NAME_LENGTH)
        window.roomInput.returnPressed.connect(self.joinRoom)
        window.roomButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + 'door_in.png'),
                                              getMessage("joinroom-label"))
        window.roomButton.pressed.connect(self.joinRoom)
        window.roomLayout = QtGui.QHBoxLayout()
        window.roomFrame = QtGui.QFrame()
        window.roomFrame.setLayout(self.roomLayout)
        window.roomFrame.setContentsMargins(0,0,0,0)
        window.roomFrame.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        window.roomLayout.setContentsMargins(0,0,0,0)
        self.roomButton.setToolTip(getMessage("joinroom-tooltip"))
        window.roomLayout.addWidget(window.roomInput)
        window.roomLayout.addWidget(window.roomButton)
        window.roomFrame.setMaximumHeight(window.roomFrame.sizeHint().height())
        window.listLayout.addWidget(window.roomFrame, Qt.AlignRight)

        window.listFrame.setLayout(window.listLayout)

        window.topSplit.addWidget(window.outputFrame)
        window.topSplit.addWidget(window.listFrame)
        window.topSplit.setStretchFactor(0,4)
        window.topSplit.setStretchFactor(1,5)
        window.mainLayout.addWidget(window.topSplit)
        window.topSplit.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)

    def addBottomLayout(self, window):
        window.bottomLayout = QtGui.QHBoxLayout()
        window.bottomFrame = QtGui.QFrame()
        window.bottomFrame.setLayout(window.bottomLayout)
        window.bottomLayout.setContentsMargins(0,0,0,0)

        self.addPlaybackLayout(window)

        window.playlistGroup = self.PlaylistGroupBox(getMessage("sharedplaylistenabled-label"))
        window.playlistGroup.setCheckable(True)
        window.playlistGroup.toggled.connect(self.changePlaylistEnabledState)
        window.playlistLayout = QtGui.QHBoxLayout()
        window.playlistGroup.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        window.playlistGroup.setAcceptDrops(True)
        window.playlist = self.PlaylistWidget()
        window.playlist.setWindow(window)
        window.playlist.setItemDelegate(self.PlaylistItemDelegate())
        window.playlist.setDragEnabled(True)
        window.playlist.setAcceptDrops(True)
        window.playlist.setDropIndicatorShown(True)
        window.playlist.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        window.playlist.setDefaultDropAction(Qt.MoveAction)
        window.playlist.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        window.playlist.doubleClicked.connect(self.playlistItemClicked)
        window.playlist.setContextMenuPolicy(Qt.CustomContextMenu)
        window.playlist.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        window.playlist.customContextMenuRequested.connect(self.openPlaylistMenu)
        self.playlistUpdateTimer = task.LoopingCall(self.playlistChangeCheck)
        self.playlistUpdateTimer.start(0.1, True)
        noteFont = QtGui.QFont()
        noteFont.setItalic(True)
        playlistItem = QtGui.QListWidgetItem(getMessage("playlist-instruction-item-message"))
        playlistItem.setFont(noteFont)
        window.playlist.addItem(playlistItem)
        playlistItem.setFont(noteFont)
        window.playlist.addItem(playlistItem)
        window.playlistLayout.addWidget(window.playlist)
        window.playlistLayout.setAlignment(Qt.AlignTop)
        window.playlistGroup.setLayout(window.playlistLayout)
        window.listSplit.addWidget(window.playlistGroup)

        window.readyPushButton = QtGui.QPushButton()
        readyFont = QtGui.QFont()
        readyFont.setWeight(QtGui.QFont.Bold)
        window.readyPushButton.setText(getMessage("ready-guipushbuttonlabel"))
        window.readyPushButton.setCheckable(True)
        window.readyPushButton.setAutoExclusive(False)
        window.readyPushButton.toggled.connect(self.changeReadyState)
        window.readyPushButton.setFont(readyFont)
        window.readyPushButton.setStyleSheet(constants.STYLE_READY_PUSHBUTTON)
        window.readyPushButton.setToolTip(getMessage("ready-tooltip"))
        window.listLayout.addWidget(window.readyPushButton, Qt.AlignRight)

        window.autoplayLayout = QtGui.QHBoxLayout()
        window.autoplayFrame = QtGui.QFrame()
        window.autoplayFrame.setVisible(False)
        window.autoplayLayout.setContentsMargins(0,0,0,0)
        window.autoplayFrame.setLayout(window.autoplayLayout)
        window.autoplayPushButton = QtGui.QPushButton()
        autoPlayFont = QtGui.QFont()
        autoPlayFont.setWeight(QtGui.QFont.Bold)
        window.autoplayPushButton.setText(getMessage("autoplay-guipushbuttonlabel"))
        window.autoplayPushButton.setCheckable(True)
        window.autoplayPushButton.setAutoExclusive(False)
        window.autoplayPushButton.toggled.connect(self.changeAutoplayState)
        window.autoplayPushButton.setFont(autoPlayFont)
        window.autoplayPushButton.setStyleSheet(constants.STYLE_AUTO_PLAY_PUSHBUTTON)
        window.autoplayPushButton.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        window.autoplayPushButton.setToolTip(getMessage("autoplay-tooltip"))
        window.autoplayLabel = QtGui.QLabel(getMessage("autoplay-minimum-label"))
        window.autoplayLabel.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        window.autoplayLabel.setMaximumWidth(window.autoplayLabel.minimumSizeHint().width())
        window.autoplayLabel.setToolTip(getMessage("autoplay-tooltip"))
        window.autoplayThresholdSpinbox = QtGui.QSpinBox()
        window.autoplayThresholdSpinbox.setMaximumWidth(window.autoplayThresholdSpinbox.minimumSizeHint().width())
        window.autoplayThresholdSpinbox.setMinimum(2)
        window.autoplayThresholdSpinbox.setMaximum(99)
        window.autoplayThresholdSpinbox.setToolTip(getMessage("autoplay-tooltip"))
        window.autoplayThresholdSpinbox.valueChanged.connect(self.changeAutoplayThreshold)
        window.autoplayLayout.addWidget(window.autoplayPushButton, Qt.AlignRight)
        window.autoplayLayout.addWidget(window.autoplayLabel, Qt.AlignRight)
        window.autoplayLayout.addWidget(window.autoplayThresholdSpinbox, Qt.AlignRight)

        window.listLayout.addWidget(window.autoplayFrame, Qt.AlignLeft)
        window.autoplayFrame.setMaximumHeight(window.autoplayFrame.sizeHint().height())
        window.mainLayout.addWidget(window.bottomFrame, Qt.AlignLeft)
        window.bottomFrame.setMaximumHeight(window.bottomFrame.minimumSizeHint().height())

    def addPlaybackLayout(self, window):
        window.playbackFrame = QtGui.QFrame()
        window.playbackFrame.setVisible(False)
        window.playbackFrame.setContentsMargins(0,0,0,0)
        window.playbackLayout = QtGui.QHBoxLayout()
        window.playbackLayout.setAlignment(Qt.AlignLeft)
        window.playbackLayout.setContentsMargins(0,0,0,0)
        window.playbackFrame.setLayout(window.playbackLayout)
        window.seekInput = QtGui.QLineEdit()
        window.seekInput.returnPressed.connect(self.seekFromButton)
        window.seekButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + u'clock_go.png'), "")
        window.seekButton.setToolTip(getMessage("seektime-menu-label"))
        window.seekButton.pressed.connect(self.seekFromButton)
        window.seekInput.setText("0:00")
        window.seekInput.setFixedWidth(60)
        window.playbackLayout.addWidget(window.seekInput)
        window.playbackLayout.addWidget(window.seekButton)
        window.unseekButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + u'arrow_undo.png'), "")
        window.unseekButton.setToolTip(getMessage("undoseek-menu-label"))
        window.unseekButton.pressed.connect(self.undoSeek)

        window.miscLayout = QtGui.QHBoxLayout()
        window.playbackLayout.addWidget(window.unseekButton)
        window.playButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + u'control_play_blue.png'), "")
        window.playButton.setToolTip(getMessage("play-menu-label"))
        window.playButton.pressed.connect(self.play)
        window.playbackLayout.addWidget(window.playButton)
        window.pauseButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + 'control_pause_blue.png'), "")
        window.pauseButton.setToolTip(getMessage("pause-menu-label"))
        window.pauseButton.pressed.connect(self.pause)
        window.playbackLayout.addWidget(window.pauseButton)
        window.playbackFrame.setMaximumHeight(window.playbackFrame.sizeHint().height())
        window.playbackFrame.setMaximumWidth(window.playbackFrame.sizeHint().width())
        window.outputLayout.addWidget(window.playbackFrame)

    def addMenubar(self, window):
        window.menuBar = QtGui.QMenuBar()

        # File menu

        window.fileMenu = QtGui.QMenu(getMessage("file-menu-label"), self)
        window.openAction = window.fileMenu.addAction(QtGui.QIcon(self.resourcespath + 'folder_explore.png'),
                                                      getMessage("openmedia-menu-label"))
        window.openAction.triggered.connect(self.browseMediapath)
        window.openAction = window.fileMenu.addAction(QtGui.QIcon(self.resourcespath + 'world_explore.png'),
                                                      getMessage("openstreamurl-menu-label"))
        window.openAction.triggered.connect(self.promptForStreamURL)
        window.openAction = window.fileMenu.addAction(QtGui.QIcon(self.resourcespath + 'film_folder_edit.png'),
                                                      getMessage("setmediadirectories-menu-label"))
        window.openAction.triggered.connect(self.openSetMediaDirectoriesDialog)


        window.exitAction = window.fileMenu.addAction(QtGui.QIcon(self.resourcespath + 'cross.png'),
                                                      getMessage("exit-menu-label"))
        window.exitAction.triggered.connect(self.exitSyncplay)
        window.menuBar.addMenu(window.fileMenu)

        # Playback menu

        window.playbackMenu = QtGui.QMenu(getMessage("playback-menu-label"), self)
        window.playAction = window.playbackMenu.addAction(QtGui.QIcon(self.resourcespath + 'control_play_blue.png'), getMessage("play-menu-label"))
        window.playAction.triggered.connect(self.play)
        window.pauseAction = window.playbackMenu.addAction(QtGui.QIcon(self.resourcespath + 'control_pause_blue.png'), getMessage("pause-menu-label"))
        window.pauseAction.triggered.connect(self.pause)
        window.seekAction = window.playbackMenu.addAction(QtGui.QIcon(self.resourcespath + 'clock_go.png'), getMessage("seektime-menu-label"))
        window.seekAction.triggered.connect(self.seekPositionDialog)
        window.unseekAction = window.playbackMenu.addAction(QtGui.QIcon(self.resourcespath + 'arrow_undo.png'), getMessage("undoseek-menu-label"))
        window.unseekAction.triggered.connect(self.undoSeek)

        window.menuBar.addMenu(window.playbackMenu)

        # Advanced menu

        window.advancedMenu = QtGui.QMenu(getMessage("advanced-menu-label"), self)
        window.setoffsetAction = window.advancedMenu.addAction(QtGui.QIcon(self.resourcespath + 'timeline_marker.png'),
                                                               getMessage("setoffset-menu-label"))
        window.setoffsetAction.triggered.connect(self.setOffset)
        window.setTrustedDomainsAction = window.advancedMenu.addAction(QtGui.QIcon(self.resourcespath + 'shield_edit.png'),
                                                      getMessage("settrusteddomains-menu-label"))
        window.setTrustedDomainsAction.triggered.connect(self.openSetTrustedDomainsDialog)
        window.createcontrolledroomAction = window.advancedMenu.addAction(
            QtGui.QIcon(self.resourcespath + 'page_white_key.png'), getMessage("createcontrolledroom-menu-label"))
        window.createcontrolledroomAction.triggered.connect(self.createControlledRoom)
        window.identifyascontroller = window.advancedMenu.addAction(QtGui.QIcon(self.resourcespath + 'key_go.png'),
                                                                    getMessage("identifyascontroller-menu-label"))
        window.identifyascontroller.triggered.connect(self.identifyAsController)

        window.menuBar.addMenu(window.advancedMenu)

        # Window menu

        window.windowMenu = QtGui.QMenu(getMessage("window-menu-label"), self)

        window.playbackAction = window.windowMenu.addAction(getMessage("playbackbuttons-menu-label"))
        window.playbackAction.setCheckable(True)
        window.playbackAction.triggered.connect(self.updatePlaybackFrameVisibility)

        window.autoplayAction = window.windowMenu.addAction(getMessage("autoplay-menu-label"))
        window.autoplayAction.setCheckable(True)
        window.autoplayAction.triggered.connect(self.updateAutoplayVisibility)
        window.menuBar.addMenu(window.windowMenu)


        # Help menu

        window.helpMenu = QtGui.QMenu(getMessage("help-menu-label"), self)
        window.userguideAction = window.helpMenu.addAction(QtGui.QIcon(self.resourcespath + 'help.png'),
                                                           getMessage("userguide-menu-label"))
        window.userguideAction.triggered.connect(self.openUserGuide)
        window.updateAction = window.helpMenu.addAction(QtGui.QIcon(self.resourcespath + 'application_get.png'),
                                                           getMessage("update-menu-label"))
        window.updateAction.triggered.connect(self.userCheckForUpdates)

        window.menuBar.addMenu(window.helpMenu)
        if not sys.platform.startswith('darwin'):
            window.mainLayout.setMenuBar(window.menuBar)

    def addMainFrame(self, window):
        window.mainFrame = QtGui.QFrame()
        window.mainFrame.setLineWidth(0)
        window.mainFrame.setMidLineWidth(0)
        window.mainFrame.setContentsMargins(0, 0, 0, 0)
        window.mainFrame.setLayout(window.mainLayout)

        window.setCentralWidget(window.mainFrame)

    def newMessage(self, message):
        self.outputbox.moveCursor(QtGui.QTextCursor.End)
        self.outputbox.insertHtml(message)
        self.outputbox.moveCursor(QtGui.QTextCursor.End)

    def resetList(self):
        self.listbox.setText("")

    def newListItem(self, item):
        self.listbox.moveCursor(QtGui.QTextCursor.End)
        self.listbox.insertHtml(item)
        self.listbox.moveCursor(QtGui.QTextCursor.End)

    def updatePlaybackFrameVisibility(self):
        self.playbackFrame.setVisible(self.playbackAction.isChecked())

    def updateAutoplayVisibility(self):
        self.autoplayFrame.setVisible(self.autoplayAction.isChecked())

    def changeReadyState(self):
        self.updateReadyIcon()
        if self._syncplayClient:
            self._syncplayClient.changeReadyState(self.readyPushButton.isChecked())
        else:
            self.showDebugMessage("Tried to change ready state too soon.")

    def changePlaylistEnabledState(self):
        self._syncplayClient.changePlaylistEnabledState(self.playlistGroup.isChecked())

    @needsClient
    def changeAutoplayThreshold(self, source=None):
        self._syncplayClient.changeAutoPlayThrehsold(self.autoplayThresholdSpinbox.value())

    def updateAutoPlayState(self, newState):
        oldState = self.autoplayPushButton.isChecked()
        if newState != oldState and newState != None:
            self.autoplayPushButton.blockSignals(True)
            self.autoplayPushButton.setChecked(newState)
            self.autoplayPushButton.blockSignals(False)
        self.updateAutoPlayIcon()

    @needsClient
    def changeAutoplayState(self, source=None):
        self.updateAutoPlayIcon()
        if self._syncplayClient:
            self._syncplayClient.changeAutoplayState(self.autoplayPushButton.isChecked())
        else:
            self.showDebugMessage("Tried to set AutoplayState too soon")

    def updateReadyIcon(self):
        ready = self.readyPushButton.isChecked()
        if ready:
            self.readyPushButton.setIcon(QtGui.QIcon(self.resourcespath + 'tick_checkbox.png'))
        else:
            self.readyPushButton.setIcon(QtGui.QIcon(self.resourcespath + 'empty_checkbox.png'))

    def updateAutoPlayIcon(self):
        ready = self.autoplayPushButton.isChecked()
        if ready:
            self.autoplayPushButton.setIcon(QtGui.QIcon(self.resourcespath + 'tick_checkbox.png'))
        else:
            self.autoplayPushButton.setIcon(QtGui.QIcon(self.resourcespath + 'empty_checkbox.png'))

    def automaticUpdateCheck(self):
        currentDateTime = datetime.utcnow()
        if not self.config['checkForUpdatesAutomatically']:
            return
        if self.config['lastCheckedForUpdates']:
            configLastChecked = datetime.strptime(self.config["lastCheckedForUpdates"], "%Y-%m-%d %H:%M:%S.%f")
            if self.lastCheckedForUpdates is None or configLastChecked > self.lastCheckedForUpdates:
                self.lastCheckedForUpdates = configLastChecked
        if self.lastCheckedForUpdates is None:
            self.checkForUpdates()
        else:
            timeDelta = currentDateTime - self.lastCheckedForUpdates
            if timeDelta.total_seconds() > constants.AUTOMATIC_UPDATE_CHECK_FREQUENCY:
                self.checkForUpdates()

    def userCheckForUpdates(self):
        self.checkForUpdates(userInitiated=True)

    @needsClient
    def checkForUpdates(self, userInitiated=False):
        self.lastCheckedForUpdates = datetime.utcnow()
        updateStatus, updateMessage, updateURL, self.publicServerList = self._syncplayClient.checkForUpdate(userInitiated)

        if updateMessage is None:
            if updateStatus == "uptodate":
                updateMessage = getMessage("syncplay-uptodate-notification")
            elif updateStatus == "updateavailale":
                updateMessage = getMessage("syncplay-updateavailable-notification")
            else:
                import syncplay
                updateMessage = getMessage("update-check-failed-notification").format(syncplay.version)
                if userInitiated == True:
                    updateURL = constants.SYNCPLAY_DOWNLOAD_URL
        if updateURL is not None:
            reply = QtGui.QMessageBox.question(self, "Syncplay",
                                        updateMessage, QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No)
            if reply == QtGui.QMessageBox.Yes:
                self.QtGui.QDesktopServices.openUrl(QUrl(updateURL))
        elif userInitiated:
            QtGui.QMessageBox.information(self, "Syncplay", updateMessage)
        else:
            self.showMessage(updateMessage)

    def dragEnterEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == 'file':
            event.acceptProposedAction()

    def dropEvent(self, event):
        rewindFile = False
        if QtGui.QDropEvent.proposedAction(event) == Qt.MoveAction:
            QtGui.QDropEvent.setDropAction(event, Qt.CopyAction)  # Avoids file being deleted
            rewindFile = True
        data = event.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == 'file':
            dropfilepath = os.path.abspath(unicode(event.mimeData().urls()[0].toLocalFile()))
            if rewindFile == False:
                self._syncplayClient._player.openFile(dropfilepath)
            else:
                self._syncplayClient.setPosition(0)
                self._syncplayClient._player.openFile(dropfilepath, resetPosition=True)
                self._syncplayClient.setPosition(0)

    def setPlaylist(self, newPlaylist, newIndexFilename=None):
        if self.updatingPlaylist:
            self.ui.showDebugMessage(u"Trying to set playlist while it is already being updated")
        if newPlaylist == self.playlistState:
            if newIndexFilename:
                self.playlist.setPlaylistIndexFilename(newIndexFilename)
            self.updatingPlaylist = False
            return
        self.updatingPlaylist = True
        if newPlaylist and len(newPlaylist) > 0:
            self.clearedPlaylistNote = True
        self.playlistState = newPlaylist
        self.playlist.updatePlaylist(newPlaylist)
        if newIndexFilename:
            self.playlist.setPlaylistIndexFilename(newIndexFilename)
        self.updatingPlaylist = False
        self._syncplayClient.fileSwitch.updateInfo()

    def setPlaylistIndexFilename(self, filename):
        self.playlist.setPlaylistIndexFilename(filename)

    def addFileToPlaylist(self, filePath, index = -1):
        if os.path.isfile(filePath):
            self.removePlaylistNote()
            filename = os.path.basename(filePath)
            if self.noPlaylistDuplicates(filename):
                if self.playlist == -1 or index == -1:
                    self.playlist.addItem(filename)
                else:
                    self.playlist.insertItem(index, filename)
                self._syncplayClient.fileSwitch.notifyUserIfFileNotInMediaDirectory(filename, filePath)
        elif isURL(filePath):
            self.removePlaylistNote()
            if self.noPlaylistDuplicates(filePath):
                if self.playlist == -1 or index == -1:
                    self.playlist.addItem(filePath)
                else:
                    self.playlist.insertItem(index, filePath)

    def openFile(self, filePath, resetPosition=False):
        self._syncplayClient._player.openFile(filePath, resetPosition)

    def noPlaylistDuplicates(self, filename):
        if self.isItemInPlaylist(filename):
            self.showErrorMessage(getMessage("cannot-add-duplicate-error").format(filename))
            return False
        else:
            return True

    def isItemInPlaylist(self, filename):
        for playlistindex in xrange(self.playlist.count()):
            if self.playlist.item(playlistindex).text() == filename:
                return True
        return False

    def addStreamToPlaylist(self, streamURI):
        self.removePlaylistNote()
        if self.noPlaylistDuplicates(streamURI):
            self.playlist.addItem(streamURI)

    def removePlaylistNote(self):
        if not self.clearedPlaylistNote:
            for index in xrange(self.playlist.count()):
                self.playlist.takeItem(0)
            self.clearedPlaylistNote = True

    def addFolderToPlaylist(self, folderPath):
        self.showErrorMessage(u"You tried to add the folder '{}' to the playlist. Syncplay only currently supports adding files to the playlist.".format(folderPath)) # TODO: Implement "add folder to playlist"
        
    def deleteSelectedPlaylistItems(self):
        self.playlist.remove_selected_items()

    def saveSettings(self):
        settings = QSettings("Syncplay", "MainWindow")
        settings.beginGroup("MainWindow")
        settings.setValue("size", self.size())
        settings.setValue("pos", self.pos())
        settings.setValue("showPlaybackButtons", self.playbackAction.isChecked())
        settings.setValue("showAutoPlayButton", self.autoplayAction.isChecked())
        settings.setValue("autoplayChecked", self.autoplayPushButton.isChecked())
        settings.setValue("autoplayMinUsers", self.autoplayThresholdSpinbox.value())
        settings.endGroup()
        settings = QSettings("Syncplay", "Interface")
        settings.beginGroup("Update")
        settings.setValue("lastChecked", self.lastCheckedForUpdates)
        settings.endGroup()
        settings.beginGroup("PublicServerList")
        if self.publicServerList:
            settings.setValue("publicServers", self.publicServerList)
        settings.endGroup()

    def loadSettings(self):
        settings = QSettings("Syncplay", "MainWindow")
        settings.beginGroup("MainWindow")
        self.resize(settings.value("size", QSize(700, 500)))
        self.move(settings.value("pos", QPoint(200, 200)))
        if settings.value("showPlaybackButtons", "false") == "true":
            self.playbackAction.setChecked(True)
            self.updatePlaybackFrameVisibility()
        if settings.value("showAutoPlayButton", "false") == "true":
            self.autoplayAction.setChecked(True)
            self.updateAutoplayVisibility()
        if settings.value("autoplayChecked", "false") == "true":
            self.updateAutoPlayState(True)
            self.autoplayPushButton.setChecked(True)
        self.autoplayThresholdSpinbox.blockSignals(True)
        self.autoplayThresholdSpinbox.setValue(int(settings.value("autoplayMinUsers", 2)))
        self.autoplayThresholdSpinbox.blockSignals(False)
        settings.endGroup()
        settings = QSettings("Syncplay", "Interface")
        settings.beginGroup("Update")
        self.lastCheckedForUpdates = settings.value("lastChecked", None)
        settings.endGroup()
        settings.beginGroup("PublicServerList")
        self.publicServerList = settings.value("publicServers", None)

    def __init__(self):
        super(MainWindow, self).__init__()
        self.newWatchlist = []
        self.publicServerList = []
        self.lastCheckedForUpdates = None
        self._syncplayClient = None
        self.folderSearchEnabled = True
        self.QtGui = QtGui
        if sys.platform.startswith('win'):
            self.resourcespath = utils.findWorkingDir() + u"\\resources\\"
        else:
            self.resourcespath = utils.findWorkingDir() + u"/resources/"
        self.setWindowFlags(self.windowFlags() & Qt.AA_DontUseNativeMenuBar)
        self.setWindowTitle("Syncplay v" + version)
        self.mainLayout = QtGui.QVBoxLayout()
        self.addTopLayout(self)
        self.addBottomLayout(self)
        self.addMenubar(self)
        self.addMainFrame(self)
        self.loadSettings()
        self.setWindowIcon(QtGui.QIcon(self.resourcespath + u"syncplay.png"))
        self.setWindowFlags(self.windowFlags() & Qt.WindowCloseButtonHint & Qt.AA_DontUseNativeMenuBar & Qt.WindowMinimizeButtonHint & ~Qt.WindowContextHelpButtonHint)
        self.show()
        self.setAcceptDrops(True)
        self.clearedPlaylistNote = False

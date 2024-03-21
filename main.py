import sys
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QAbstractItemView, QStyledItemDelegate, QToolBar, QAction, QApplication, QWidget, QVBoxLayout, QFileDialog, QLineEdit, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QLabel, QStyle, QMenu, QDialog, QPushButton, QInputDialog
from PyQt5.QtGui import QBrush, QColor, QIcon, QPen
from nbt import nbt
import gzip
import os
from io import BytesIO

class CustomDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        if index.column() == 1:
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            else:
                color = index.data(Qt.BackgroundRole)
                if color is not None:
                    painter.fillRect(option.rect, color.color())
                else:
                    painter.fillRect(option.rect, QColor("#313244"))
            rect = QRect(option.rect)
            rect.adjust(10, 0, 0, 0)
            textColor = index.data(Qt.ForegroundRole)
            if textColor is not None:
                painter.setPen(QPen(textColor.color()))
            painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, index.data())
        else:
            super().paint(painter, option, index)
        painter.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        if index.column() == 1:
            size.setWidth(size.width() + 10)
        return size

class SearchLineEdit(QLineEdit):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if not self.text():
                return
        super().keyPressEvent(event)

class NBTViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.setStyleSheet("font-size: 12px;")
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QPushButton {
                background-color: #181825;
                border: none;
                color: #89dceb;
                padding: 10px;
                padding-left: 15px;
                padding-right: 15px;
            }
            QPushButton:hover {
                background-color: #313244;
                padding: 10px;
                padding-left: 15px;
                padding-right: 15px;
                color: #89dceb;
            }
            QTreeWidget {
                background-color: #181825;
                color: #bac2de;
                border: 0px;
                padding: 5px;
            }
            QLineEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                padding: 5px;
                height: 30px;
            }
        """)
        self.toolbar = QToolBar()
        self.layout.addWidget(self.toolbar)

        openAction = QAction(QIcon('open.png'), 'Open', self)
        openAction.triggered.connect(self.openFile)
        self.toolbar.addAction(openAction)

        saveAction = QAction(QIcon('save.png'), 'Save', self)
        saveAction.triggered.connect(self.saveFile)
        self.toolbar.addAction(saveAction)

        closeAction = QAction(QIcon('close.png'), 'Close', self)
        closeAction.triggered.connect(self.closeFile)
        self.toolbar.addAction(closeAction)
        self.toolbar.addSeparator()

        expandAllButton = QAction(QIcon('expandall.png'), 'Close', self)
        expandAllButton.triggered.connect(self.expandAll)
        self.toolbar.addAction(expandAllButton)
        self.toolbar.addSeparator()

        self.searchField = SearchLineEdit()
        self.searchField.setPlaceholderText('Search...')
        self.searchField.textChanged.connect(self.onSearchInputChanged)
        self.searchField.returnPressed.connect(self.search) 
        self.toolbar.addWidget(self.searchField)
        self.toolbar.addSeparator()
        self.searchResultLabel = QLabel()
        self.toolbar.addWidget(self.searchResultLabel)

        searchAction = QAction(QIcon('search.png'), 'Search', self)
        searchAction.triggered.connect(self.search)
        self.toolbar.addAction(searchAction)

        self.prevAction = QAction(QIcon('prev.png'), 'Previous', self)
        self.prevAction.triggered.connect(self.prevSearchResult)
        self.prevAction.setEnabled(False)
        self.toolbar.addAction(self.prevAction)

        self.nextAction = QAction(QIcon('next.png'), 'Next', self)
        self.nextAction.triggered.connect(self.nextSearchResult)
        self.nextAction.setEnabled(False)
        self.toolbar.addAction(self.nextAction)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Name", "Value"])
        self.tree.itemChanged.connect(self.updateNBT)
        self.tree.setItemDelegate(CustomDelegate())
        self.tree.setAnimated(True)
        self.tree.setStyleSheet("""
            font-size: 14px;
            QTreeView::item {
                height: 30px;
            }
        """)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.showContextMenu)

        self.layout.addWidget(self.tree)
        self.setLayout(self.layout)

    def openFile(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "NBT Files (*.nbt *.dat)", options=options)
        if fileName:
            self.nbtFile = None
            self.tree.clear()
            fileExtension = os.path.splitext(fileName)[1]
            if fileExtension == '.dat':
                with gzip.open(fileName, 'rb') as f:
                    self.nbtFile = nbt.NBTFile(buffer=f)
            else:
                self.nbtFile = nbt.NBTFile(fileName,'rb')
            self.populateTree(self.nbtFile, self.tree)

    def closeFile(self):
        self.nbtFile = None
        self.tree.clear()

    def expandAll(self):
        self.tree.expandAll()

    def onSearchInputChanged(self, text):
        if text:
            self.nextAction.setEnabled(True)
            self.prevAction.setEnabled(True)
            self.searchResultLabel.show()
        else:
            self.nextAction.setEnabled(False)
            self.prevAction.setEnabled(False)
            self.searchResultLabel.clear() 
            self.searchResultLabel.hide()

    def populateTree(self, nbtFile, parent):
        if isinstance(nbtFile, nbt.TAG_Compound):
            for tag_name in nbtFile:
                tag = nbtFile[tag_name]
                item = QTreeWidgetItem(parent)
                if isinstance(tag, (nbt.TAG_Compound, nbt.TAG_List)):
                    item.setText(0, f"[{len(tag)}] {tag_name}")
                    self.populateTree(tag, item)
                else:
                    item.setText(0, f"\u00A0{tag_name}")
                    item.setText(1, str(tag))
                item.setData(0, Qt.UserRole, tag)
        elif isinstance(nbtFile, nbt.TAG_List):
            for i, tag in enumerate(nbtFile):
                item = QTreeWidgetItem(parent)
                if isinstance(tag, (nbt.TAG_Compound, nbt.TAG_List)):
                    item.setText(0, f"[{len(tag)}] {i}")
                    self.populateTree(tag, item)
                else:
                    item.setText(0, f"\u00A0{i}")
                    item.setText(1, str(tag))
                item.setData(0, Qt.UserRole, tag)
        else:
            item = QTreeWidgetItem(parent)
            item.setText(0, f"\u00A0{nbtFile.name}")
            item.setText(1, str(nbtFile.value))
            item.setData(0, Qt.UserRole, nbtFile)

    def saveFile(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "QFileDialog.getSaveFileName()", "", "NBT Files (*.nbt *.dat)", options=options)
        if fileName:
            fileExtension = os.path.splitext(fileName)[1]
            if fileExtension == '.dat':
                with gzip.open(fileName, 'wb') as f:
                    byte_io = BytesIO()
                    self.nbtFile.write_file(buffer=byte_io)
                    f.write(byte_io.getvalue())
            else:
                self.nbtFile.write_file(fileName)

    def search(self):
        self.searchResults = []
        search_text = self.searchField.text()
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if search_text in item.text(0) or search_text in item.text(1):
                self.searchResults.append(item)
            iterator += 1
        self.searchResultIndex = 0
        self.updateSearchResultLabel()
        self.showCurrentSearchResult()
        self.prevAction.setEnabled(True)
        self.nextAction.setEnabled(True)

    def showCurrentSearchResult(self):
        if self.searchResults:
            for item in self.searchResults:
                item.setBackground(0, QBrush(QColor(24, 24, 37)))
                item.setBackground(1, QBrush(QColor(49, 50, 68)))
                item.setForeground(0, QBrush(QColor(186, 194, 222)))
                item.setForeground(1, QBrush(QColor(186, 194, 222)))
            item = self.searchResults[self.searchResultIndex]
            item.setBackground(0, QBrush(QColor(116, 199, 236)))
            item.setBackground(1, QBrush(QColor(116, 199, 236)))
            item.setForeground(0, QBrush(QColor(17, 17, 27)))
            item.setForeground(1, QBrush(QColor(17, 17, 27)))
            self.tree.expandItem(item)
            self.tree.scrollToItem(item)
            index = self.tree.indexFromItem(item)
            self.tree.scrollTo(index, QAbstractItemView.PositionAtCenter)

    def nextSearchResult(self):
        if self.searchResults:
            self.searchResultIndex = (self.searchResultIndex + 1) % len(self.searchResults)
            self.updateSearchResultLabel()
            self.showCurrentSearchResult()

    def prevSearchResult(self):
        if self.searchResults:
            self.searchResultIndex = (self.searchResultIndex - 1) % len(self.searchResults)
            self.updateSearchResultLabel()
            self.showCurrentSearchResult()

    def updateSearchResultLabel(self):
        if self.searchResults:
            self.searchResultLabel.setText(f"{self.searchResultIndex + 1}/{len(self.searchResults)}")
        else:
            self.searchResultLabel.setText("0/0")

    def updateNBT(self, item, column):
        if column == 1:
            tag = item.data(0, Qt.UserRole)
            if tag is not None:
                tag.value = item.text(1)

    def showContextMenu(self, position):
        menu = QMenu()
        deleteAction = menu.addAction("Delete")
        editAction = menu.addAction("Edit")
        action = menu.exec_(self.tree.viewport().mapToGlobal(position))
        if action == deleteAction:
            self.deleteItem()
        elif action == editAction:
            self.editItem()

    def deleteItem(self):
        item = self.tree.currentItem()
        (item.parent() or self.tree).removeChild(item)

    def editItem(self):
        item = self.tree.currentItem()
        dialog = QDialog()
        layout = QVBoxLayout()
        nameLabel = QLabel("Name")
        nameEdit = QLineEdit(item.text(0))
        valueLabel = QLabel("Value")
        valueEdit = QLineEdit(item.text(1))
        okButton = QPushButton("OK")
        cancelButton = QPushButton("Cancel")
        okButton.clicked.connect(dialog.accept)
        cancelButton.clicked.connect(dialog.reject)
        layout.addWidget(nameLabel)
        layout.addWidget(nameEdit)
        layout.addWidget(valueLabel)
        layout.addWidget(valueEdit)
        layout.addWidget(okButton)
        layout.addWidget(cancelButton)
        dialog.setLayout(layout)
        if dialog.exec_() == QDialog.Accepted:
            item.setText(0, nameEdit.text())
            item.setText(1, valueEdit.text())

def main():
    app = QApplication(sys.argv)
    viewer = NBTViewer()
    viewer.show()
    sys.exit(app.exec_())
if __name__ == '__main__':
    main()
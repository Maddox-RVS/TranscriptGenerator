import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLabel, QListWidget, QLineEdit, QFileDialog
)
from PySide6.QtCore import QThread, Signal
from transcript_generator import GenTranscript

class FileListWidget(QListWidget):
    '''
    A widget for displaying a list of input files.

    This widget does not support drag and drop and only allows adding files that exist.
    '''
    def __init__(self, parent=None):
        '''
        Initialize the FileListWidget.
        '''
        super().__init__(parent)
        self.setAcceptDrops(False)
        self.setStyleSheet('border: 2px solid #aaa;')
        self.setMinimumHeight(200)

    def hasFile(self, filePath):
        '''
        Determine if a file is already present in the list.

        Args:
            filePath (str): The path of the file to check.

        Returns:
            bool: True if the file is already in the list, False otherwise.
        '''
        for i in range(self.count()):
            if self.item(i).text() == filePath:
                return True
        return False

class TranscriptionWorker(QThread):
    '''
    A worker thread for handling the transcription process.

    Emits errorSignal with error messages or finishedSignal upon completion.
    '''
    errorSignal = Signal(str)
    finishedSignal = Signal()

    def __init__(self, files, outputDir, modelSize, parent=None):
        '''
        Initialize the TranscriptionWorker.

        Args:
            files (list): List of input file paths.
            outputDir (str): The output directory.
            modelSize (str): The model size to use for transcription.
            parent (QObject, optional): Parent object.
        '''
        super().__init__(parent)
        self.files = files
        self.outputDir = outputDir
        self.modelSize = modelSize

    def run(self):
        '''
        Run the transcription process in a separate thread.
        '''
        try:
            for filePath in self.files:
                GenTranscript.transcribe(filePath, self.outputDir, self.modelSize)
            self.finishedSignal.emit()
        except MemoryError:
            self.errorSignal.emit('The selected model is too large for the available system memory.')
        except Exception as e:
            if 'Killed' in str(e):
                self.errorSignal.emit('The selected model is too large for the available system memory.')
            else:
                self.errorSignal.emit(str(e))

class MainWindow(QWidget):
    '''
    The main application window for the transcription application.
    '''
    def __init__(self):
        '''
        Initialize the MainWindow and set up the user interface.
        '''
        super().__init__()
        self.setWindowTitle('Transcription Application')
        self.resize(600, 500)
        self.worker = None
        self.setupUi()

    def setupUi(self):
        '''
        Set up the user interface elements.
        '''
        mainLayout = QVBoxLayout(self)

        self.messageLabel = QLabel('')
        self.messageLabel.setStyleSheet('color: red; font-weight: bold;')
        self.messageLabel.hide()
        mainLayout.addWidget(self.messageLabel)

        inputLabel = QLabel('Input Files:')
        mainLayout.addWidget(inputLabel)

        self.fileList = FileListWidget()
        mainLayout.addWidget(self.fileList)

        fileButtonsLayout = QHBoxLayout()
        self.addFilesButton = QPushButton('Add Files')
        self.addFilesButton.clicked.connect(self.browseInputFiles)
        fileButtonsLayout.addWidget(self.addFilesButton)

        self.removeFilesButton = QPushButton('Remove Selected')
        self.removeFilesButton.clicked.connect(self.removeSelectedFiles)
        fileButtonsLayout.addWidget(self.removeFilesButton)
        mainLayout.addLayout(fileButtonsLayout)

        conversionLayout = QHBoxLayout()
        self.convertButton = QPushButton('Convert')
        self.convertButton.setStyleSheet('background-color: blue; color: white; font-weight: bold;')
        self.convertButton.setFixedHeight(40)
        self.convertButton.clicked.connect(self.startConversion)

        self.modelDropdown = QComboBox()
        self.modelDropdown.setFixedHeight(40)
        options = [
            ('tiny.en', '~1 GB'),
            ('tiny', '~1 GB'),
            ('base.en', '~1 GB'),
            ('base', '~1 GB'),
            ('small.en', '~2 GB'),
            ('small', '~2 GB'),
            ('medium.en', '~5 GB'),
            ('medium', '~5 GB'),
            ('large-v1', '~10 GB'),
            ('large-v2', '~10 GB'),
            ('large-v3', '~10 GB'),
            ('large', '~10 GB'),
            ('large-v3-turbo', '~6 GB'),
            ('turbo', '~6 GB')
        ]
        for option, mem in options:
            self.modelDropdown.addItem(f'{option} ({mem})', option)
        index = self.modelDropdown.findData('small')
        if index != -1:
            self.modelDropdown.setCurrentIndex(index)

        conversionLayout.addWidget(self.convertButton)
        conversionLayout.addWidget(self.modelDropdown)
        mainLayout.addLayout(conversionLayout)

        outputLayout = QHBoxLayout()
        outputLabel = QLabel('Output Directory:')
        outputLayout.addWidget(outputLabel)

        self.outputLineEdit = QLineEdit()
        self.outputLineEdit.setPlaceholderText('Select output directory (required)')
        outputLayout.addWidget(self.outputLineEdit)

        self.outputBrowseButton = QPushButton('Browse')
        self.outputBrowseButton.setFixedHeight(30)
        self.outputBrowseButton.clicked.connect(self.browseOutputDirectory)
        outputLayout.addWidget(self.outputBrowseButton)
        mainLayout.addLayout(outputLayout)

    def browseInputFiles(self):
        '''
        Open a file dialog to select audio/video files and add them to the file list.
        '''
        files, _ = QFileDialog.getOpenFileNames(
            self,
            'Select Audio/Video Files',
            '',
            'Audio/Video Files (*.mp3 *.mp4)'
        )
        if files:
            for filePath in files:
                if not os.path.exists(filePath):
                    self.showMessage(f'File does not exist:\n{filePath}', error=True)
                    continue
                if GenTranscript.isValidFileType(filePath) and not self.fileList.hasFile(filePath):
                    self.fileList.addItem(os.path.normpath(filePath))

    def removeSelectedFiles(self):
        '''
        Remove selected items from the file list.
        '''
        for item in self.fileList.selectedItems():
            self.fileList.takeItem(self.fileList.row(item))

    def browseOutputDirectory(self):
        '''
        Open a directory dialog to select an output directory.
        '''
        directory = QFileDialog.getExistingDirectory(self, 'Select Output Directory')
        if directory:
            self.outputLineEdit.setText(os.path.normpath(directory))

    def startConversion(self):
        '''
        Start the transcription process after validating inputs.
        '''
        self.hideMessage()

        outputText = self.outputLineEdit.text().strip()
        if not outputText:
            self.showMessage('Output directory is required and must exist.', error=True)
            return

        outputDir = os.path.normpath(outputText)
        if not os.path.isdir(outputDir):
            self.showMessage('Output directory does not exist.', error=True)
            return

        files = [os.path.normpath(self.fileList.item(i).text()) for i in range(self.fileList.count())]
        if not files:
            self.showMessage('Please add some files.', error=True)
            return

        for filePath in files:
            if not os.path.exists(filePath):
                self.showMessage(f'Input file does not exist:\n{filePath}', error=True)
                return

        modelSize = self.modelDropdown.currentData()

        self.convertButton.setText('Transcribing audio...')
        self.convertButton.setEnabled(False)

        self.worker = TranscriptionWorker(files, outputDir, modelSize)
        self.worker.errorSignal.connect(self.handleError)
        self.worker.finishedSignal.connect(self.conversionFinished)
        self.worker.start()

    def handleError(self, message):
        '''
        Handle errors emitted by the transcription worker.

        Args:
            message (str): The error message.
        '''
        self.showMessage(message, error=True)
        self.convertButton.setText('Convert')
        self.convertButton.setEnabled(True)

    def conversionFinished(self):
        '''
        Handle the successful completion of the transcription process.
        '''
        self.convertButton.setText('Convert')
        self.convertButton.setEnabled(True)
        self.fileList.clear()
        self.showMessage('Transcription successful!', error=False)

    def showMessage(self, message, error=True):
        '''
        Display a message to the user.

        Args:
            message (str): The message to display.
            error (bool): True to display an error message, False for a success message.
        '''
        if error:
            self.messageLabel.setStyleSheet('color: red; font-weight: bold;')
        else:
            self.messageLabel.setStyleSheet('color: green; font-weight: bold;')
        self.messageLabel.setText(message)
        self.messageLabel.show()

    def hideMessage(self):
        '''
        Hide the message display.
        '''
        self.messageLabel.hide()
        self.messageLabel.setText('')

    def closeEvent(self, event):
        '''
        Handle the window close event by ensuring that any running worker thread is terminated.
        '''
        if self.worker is not None and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        QApplication.instance().quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec())

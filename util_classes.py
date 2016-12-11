"""Utility classes that are used both in the GUI and the CMD."""

import os
import re
import zipfile
import tarfile

import config
import utils

from PySide import QtGui, QtCore
from PySide.QtCore import Qt

class FileItem(QtGui.QTreeWidgetItem):
    def __init__(self, parent=None, path=None):
        super(FileItem, self).__init__(parent)
        self.path = path

class TreeBrowser(QtGui.QWidget):
    def __init__(self, directory=None, checked_files=None,
                 whitelist=None, blacklist=None, parent=None):
        super(TreeBrowser, self).__init__(parent=parent)
        self.root = QtGui.QTreeWidget()
        self.root.setHeaderLabel('Included files')
        self.root.itemChanged.connect(self.item_changed)
        self.files = {}

        self.paths = []

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.root)
        self.setLayout(layout)

        self.watcher = QtCore.QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self.directory_changed)
        self.watcher.fileChanged.connect(self.file_changed)

        self.directoryChanged = self.watcher.directoryChanged
        self.fileChanged = self.watcher.fileChanged

        self.init(directory, checked_files, whitelist, blacklist)

    def init(self, directory=None, checked_files=None,
             whitelist=None, blacklist=None):

        if directory:
            self.directory = directory + os.sep
        else:
            self.directory = directory

        self.checked_files = checked_files or []

        self.whitelist = whitelist or []
        self.blacklist = blacklist or []

        self.watcher.removePaths(self.watcher.files())

        self.files = {}

        self.root.clear()

        self.generate_directory_widget()

    def file_changed(self, path):
        print(path)
        pass

    def directory_changed(self, path):
        print(path)
        pass

    def get_abs_file_list(self):
        return [os.path.join(self.directory, path) for path in self.files.keys()]

    def get_checked_files(self):
        pass

    def item_changed(self, item, column):
        self.files[item.path] = item.checkState(column)

    def generate_directory_widget(self):
        if self.directory is None:
            return

        parent_map = {'': self.root}

        for root, dirs, files in os.walk(self.directory):
            for directory in dirs:

                proj_path = root.replace(self.directory, '')

                parent = parent_map[proj_path]

                path = os.path.join(proj_path, directory)

                checked = Qt.Unchecked

                for checked_file in self.checked_files:
                    match = re.match('^'+checked_file, path)
                    if match:
                        checked = Qt.Checked

                child = FileItem(parent, path)
                child.setFlags(child.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
                child.setText(0, directory)
                child.setCheckState(0, checked)

                self.files[path] = checked

                parent_map[path] = child

            for file in files:
                proj_path = root.replace(self.directory, '')

                parent = parent_map[proj_path]

                path = os.path.join(proj_path, file)

                checked = Qt.Unchecked

                for checked_file in self.checked_files:
                    match = re.match(checked_file, path)
                    if match:
                        checked = Qt.Checked

                child = FileItem(parent, path)
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setText(0, file)
                child.setCheckState(0, checked)

                self.files[path] = checked

        self.watcher.addPaths(self.get_abs_file_list())


class ExistingProjectDialog(QtGui.QDialog):
    def __init__(self, recent_projects, directory_callback, parent=None):
        super(ExistingProjectDialog, self).__init__(parent)
        self.setWindowTitle('Open Project Folder')
        self.setWindowIcon(QtGui.QIcon(config.get_file('files/images/icon.png')))
        self.setMinimumWidth(500)

        group_box = QtGui.QGroupBox('Existing Projects')
        gbox_layout = QtGui.QVBoxLayout()
        self.project_list = QtGui.QListWidget()

        gbox_layout.addWidget(self.project_list)
        group_box.setLayout(gbox_layout)

        self.callback = directory_callback

        self.projects = recent_projects

        for project in recent_projects:
            text = '{} - {}'.format(os.path.basename(project), project)
            self.project_list.addItem(text)

        self.project_list.itemClicked.connect(self.project_clicked)

        self.cancel = QtGui.QPushButton('Cancel')
        self.open = QtGui.QPushButton('Open Selected')
        self.open_readonly = QtGui.QPushButton('Open Read-only')
        self.browse = QtGui.QPushButton('Browse...')

        self.open.setEnabled(False)
        self.open.clicked.connect(self.open_clicked)

        self.open_readonly.setEnabled(False)
        self.open_readonly.clicked.connect(self.open_readonly_clicked)

        self.browse.clicked.connect(self.browse_clicked)

        buttons = QtGui.QWidget()

        button_layout = QtGui.QHBoxLayout()
        button_layout.addWidget(self.cancel)
        button_layout.addWidget(QtGui.QWidget())
        button_layout.addWidget(self.browse)
        button_layout.addWidget(self.open_readonly)
        button_layout.addWidget(self.open)

        buttons.setLayout(button_layout)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(group_box)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.cancel.clicked.connect(self.cancelled)

    def browse_clicked(self):

        default = self.parent().project_dir() or self.parent().last_project_dir

        directory = QtGui.QFileDialog.getExistingDirectory(self, 'Find Project Directory',
                                                           default)

        if directory:
            self.callback(directory)
            self.close()

    def open_clicked(self):
        pos = self.project_list.currentRow()
        self.callback(self.projects[pos])
        self.close()

    def open_readonly_clicked(self):
        pos = self.project_list.currentRow()
        self.callback(self.projects[pos], readonly=True)
        self.close()

    def project_clicked(self, _):
        self.open.setEnabled(True)
        self.open_readonly.setEnabled(True)

    def cancelled(self):
        self.close()


class Validator(QtGui.QRegExpValidator):
    def __init__(self, regex, action, parent=None):
        self.exp = regex
        self.action = str
        if hasattr(str, action):
            self.action = getattr(str, action)
        reg = QtCore.QRegExp(regex)
        super(Validator, self).__init__(reg, parent)

    def validate(self, text, pos):
        result = super(Validator, self).validate(text, pos)
        return result

    def fixup(self, text):
        return ''.join(re.findall(self.exp, self.action(text)))


class BackgroundThread(QtCore.QThread):
    def __init__(self, widget, method_name, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.widget = widget
        self.method_name = method_name

    def run(self):
        if hasattr(self.widget, self.method_name):
            func = getattr(self.widget, self.method_name)
            func()

class Setting(object):
    """Class that describes a setting from the setting.cfg file"""
    def __init__(self, name='', display_name=None, value=None,
                 required=False, type=None, file_types=None, *args, **kwargs):
        self.name = name
        self.display_name = (display_name
                             if display_name
                             else name.replace('_', ' ').capitalize())
        self.value = value
        self.last_value = None
        self.required = required
        self.type = type
        self.url = kwargs.pop('url', '')
        self.copy = kwargs.pop('copy', True)
        self.file_types = file_types
        self.scope = kwargs.pop('scope', 'local')

        self.default_value = kwargs.pop('default_value', None)
        self.button = kwargs.pop('button', None)
        self.button_callback = kwargs.pop('button_callback', None)
        self.description = kwargs.pop('description', '')
        self.values = kwargs.pop('values', [])
        self.filter = kwargs.pop('filter', '.*')
        self.filter_action = kwargs.pop('filter_action', 'None')
        self.check_action = kwargs.pop('check_action', 'None')
        self.action = kwargs.pop('action', None)

        self.set_extra_attributes_from_keyword_args(**kwargs)

        if self.value is None:
            self.value = self.default_value

        self.save_path = kwargs.pop('save_path', '')

        self.get_file_information_from_url()

    def filter_name(self, text):
        """Use the filter action to filter out invalid text"""
        if hasattr(self.filter_action, text):
            action = getattr(self.filter_action, text)
            return action(text)
        return text

    def get_file_information_from_url(self):
        """Extract the file information from the setting url"""
        if hasattr(self, 'url'):
            self.file_name = self.url.split('/')[-1]
            self.full_file_path = utils.path_join(self.save_path, self.file_name)
            self.file_ext = os.path.splitext(self.file_name)[1]
            if self.file_ext == '.zip':
                self.extract_class = zipfile.ZipFile
                self.extract_args = ()
            elif self.file_ext == '.gz':
                self.extract_class = tarfile.TarFile.open
                self.extract_args = ('r:gz',)

    def save_file_path(self, version, location=None, sdk_build=False):
        """Get the save file path based on the version"""
        if location:
            self.save_path = location
        else:
            self.save_path = self.save_path or config.DEFAULT_DOWNLOAD_PATH


        self.get_file_information_from_url()

        if self.full_file_path:

            path = self.full_file_path.format(version)

            if sdk_build:
                path = utils.replace_right(path, 'nwjs', 'nwjs-sdk', 1)

            return path

        return ''

    def set_extra_attributes_from_keyword_args(self, **kwargs):
        for undefined_key, undefined_value in kwargs.items():
            setattr(self, undefined_key, undefined_value)

    def extract(self, ex_path, version, sdk_build=False):
        if os.path.exists(ex_path):
            utils.rmtree(ex_path, ignore_errors=True)

        path = self.save_file_path(version, sdk_build=sdk_build)

        file = self.extract_class(path,
                                  *self.extract_args)
        # currently, python's extracting mechanism for zipfile doesn't
        # copy file permissions, resulting in a binary that
        # that doesn't work. Copied from a patch here:
        # http://bugs.python.org/file34873/issue15795_cleaned.patch
        if path.endswith('.zip'):
            members = file.namelist()
            for zipinfo in members:
                minfo = file.getinfo(zipinfo)
                target = file.extract(zipinfo, ex_path)
                mode = minfo.external_attr >> 16 & 0x1FF
                os.chmod(target, mode)
        else:
            file.extractall(ex_path)

        if path.endswith('.tar.gz'):
            dir_name = utils.path_join(ex_path, os.path.basename(path).replace('.tar.gz', ''))
        else:
            dir_name = utils.path_join(ex_path, os.path.basename(path).replace('.zip', ''))

        if os.path.exists(dir_name):
            for p in os.listdir(dir_name):
                abs_file = utils.path_join(dir_name, p)
                utils.move(abs_file, ex_path)
            utils.rmtree(dir_name, ignore_errors=True)

    def __repr__(self):
        url = ''
        if hasattr(self, 'url'):
            url = self.url
        return (
            'Setting: (name={}, '
            'display_name={}, '
            'value={}, required={}, '
            'type={}, url={})'
        ).format(self.name,
                 self.display_name,
                 self.value,
                 self.required,
                 self.type,
                 url)

class CompleterLineEdit(QtGui.QLineEdit):

    def __init__(self, tag_dict, *args):
        QtGui.QLineEdit.__init__(self, *args)

        self.pref = ''
        self.tag_dict = tag_dict

    def text_changed(self, text):
        all_text = str(text)
        text = all_text[:self.cursorPosition()]
        prefix = re.split(r'(?<=\))(.*)(?=%\()', text)[-1].strip()
        self.pref = prefix
        if prefix.strip() != prefix:
            self.pref = ''

    def complete_text(self, text):
        cursor_pos = self.cursorPosition()
        before_text = str(self.text())[:cursor_pos]
        after_text = str(self.text())[cursor_pos:]
        prefix_len = len(re.split(r'(?<=\))(.*)(?=%\()', before_text)[-1].strip())
        tag_text = self.tag_dict.get(text)

        if tag_text is None:
            tag_text = text

        new_text = '{}{}{}'.format(before_text[:cursor_pos - prefix_len],
                                   tag_text,
                                   after_text)
        self.setText(new_text)
        self.setCursorPosition(len(new_text))

class TagsCompleter(QtGui.QCompleter):

    def __init__(self, parent, all_tags):
        self.keys = sorted(all_tags.keys())
        self.vals = sorted([val for val in all_tags.values()])
        self.tags = list(sorted(self.vals+self.keys))
        QtGui.QCompleter.__init__(self, self.tags, parent)
        self.editor = parent

    def update(self, text):
        obj = self.editor
        completion_prefix = obj.pref
        model = QtGui.QStringListModel(self.tags, self)
        self.setModel(model)

        self.setCompletionPrefix(completion_prefix)
        if completion_prefix.strip() != '':
            self.complete()

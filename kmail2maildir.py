#!/usr/bin/env python3

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = 'Boris Wachtmeister'

import argparse
import glob
import os

from os import path

HIDDEN_FILE_PREFIX = '.'
KMAIL_SUBDIR_PREFIX = '.'
KMAIL_SUBDIR_SUFFIX = '.directory'
DEFAULT_HIERARCHY_SEPARATOR = '.'
MAILDIR_SPECIAL_DIRS = ('cur', 'new', 'tmp')


class Maildir:
    """
    This class represents a maildir with the information about parent directories etc
    """
    def __init__(self, options, directory):
        self.args = options
        self.name = path.basename(directory)
        self.directory = directory
        path_components = path.relpath(directory, options.folder).split(path.sep)
        # remove the leading dot and the trailing .directory
        self.path_list = list()
        for p in path_components:
            if p.startswith(KMAIL_SUBDIR_PREFIX) and p.endswith(KMAIL_SUBDIR_SUFFIX):
                p = p[len(KMAIL_SUBDIR_PREFIX):len(p) - len(KMAIL_SUBDIR_SUFFIX)]
            self.path_list.append(p)

    def get_folder_path(self):
        """ Get the path of the folder in maildir-format """
        folder_path = HIDDEN_FILE_PREFIX + self.args.hierarchy_separator.join(self.path_list)
        return path.join(self.args.folder, folder_path)

    def get_parent_maildir(self):
        """ Get the parent maildir directory of this maildir """
        if len(self.path_list) == 1:
            return None  # this was a root folder
        return path.dirname(self.directory)


class FileSystemAction:
    """
    A helper class that does all os.* operations and allows do a "dry run" which doesn't actually modify anything
    """
    def __init__(self, dry_run, quiet=False):
        self.dry_run = dry_run
        self.quiet = quiet

    def rename(self, src, dst):
        """ Rename a folder from src to dst. This always checks if dst already exists, even in "dry runs" """
        if path.exists(dst):
            raise Exception("Destination %s already exists" % dst)
        self.__run('Moving %s -> %s' % (src, dst), lambda: os.rename(src, dst))

    def delete(self, file):
        """ Delete a file """
        self.__run('Removing file %s' % file, lambda: os.remove(file))

    def rmdir(self, directory):
        """ remove a directory """
        self.__run('Removing folder %s' % directory, lambda: os.rmdir(directory))

    def __run(self, message, function):
        if not self.quiet:
            print(message)
        if not self.dry_run:
            function()


class Kmail2Maildir:
    def __init__(self, args, fs_action):
        self.args = args
        self.fs_action = fs_action

    def move_kmail_folders(self):
        subdir_containers = self.__get_subfolders_containers_recursive(self.args.folder)
        maildirs_paths = self.__get_maildirs_from_subfoldercontainers(subdir_containers)
        maildirs = [Maildir(self.args, p) for p in maildirs_paths]
        maildirs.sort(key=lambda d: d.get_folder_path(), reverse=True)
        for maildir in maildirs:
            self.fs_action.rename(maildir.directory, maildir.get_folder_path())

            parent_maildir = maildir.get_parent_maildir()

            if self.args.remove_index_files:
                self.remove_index_files(maildir)

            # these will only be deleted if --remove-index-files is used, because otherwise the folder will not be empty
            if parent_maildir and self.__is_empty_dir(parent_maildir):
                self.fs_action.rmdir(parent_maildir)

        # kmail treats the inbox as yet another folder, but that's not how dovecot works -> move them to the base folder
        kmail_inbox = path.join(self.args.folder, HIDDEN_FILE_PREFIX + 'inbox')
        for maildir_dir in MAILDIR_SPECIAL_DIRS:
            self.fs_action.rename(path.join(kmail_inbox, maildir_dir), path.join(self.args.folder, maildir_dir))
        self.fs_action.rmdir(kmail_inbox)

    @staticmethod
    def __is_empty_dir(directory):
        """
        checks if a directory is empty

        :param directory: the directory to check
        :return: True is the directory is empty
        """
        return not os.listdir(directory)

    @staticmethod
    def __is_maildir(directory):
        """
        checks if a directory is (most likely) a maildir.

         This basically checks if all special subdirectories of a maildir a present ("cur", "tmp", "new")

        :param directory: the directory to check
        :return: True if the directory seems to be a maildir
        """
        dirs_exist = [path.isdir(path.join(directory, d)) for d in MAILDIR_SPECIAL_DIRS]
        return all(dirs_exist)

    @staticmethod
    def __get_subfolders_containers_recursive(directory):
        """
        Recursively gets all of kmail's containers for subdirectories.

         Kmail puts subfolders into a special directory named ".foo.directory".
         This method gets every directory that matches this description

        :param directory: The root of the tree that should be searched
        :return: a list of the directories that where found
        """
        result = [directory]
        directories = glob.glob(path.join(directory, KMAIL_SUBDIR_PREFIX + '*' + KMAIL_SUBDIR_SUFFIX))
        maildir_subdirectory_containers = [d for d in directories if path.isdir(d)]
        for subdir in maildir_subdirectory_containers:
            result.extend(Kmail2Maildir.__get_subfolders_containers_recursive(subdir))
        return result

    @staticmethod
    def __get_maildirs_from_subfoldercontainers(subfolder_containers):
        """
        This gets all maildirs from a list of containers as described in "get_subfolders_containers_recursive"

        :param subfolder_containers: The list of container directories that should be searched
        :return: a list of maildirs
        """
        result = list()
        for subdir_container in subfolder_containers:
            files = glob.glob(path.join(subdir_container, "*"))
            directories = [f for f in files if path.isdir(f)]
            potential_maildirs = [d for d in directories if d[0] != HIDDEN_FILE_PREFIX]
            maildirs = [d for d in potential_maildirs if Kmail2Maildir.__is_maildir(d)]
            result.extend(maildirs)
        return result

    def remove_index_files(self, maildir):
        """
        This removes all index files that where written by kmail for a maildir

        :param maildir: The maildir that should be cleaned
        """
        index_file_glob = HIDDEN_FILE_PREFIX + maildir.name + '.index*'
        index_files = glob.glob(path.join(path.dirname(maildir.directory), index_file_glob))
        for index_file in index_files:
            self.fs_action.delete(index_file)


def kmail2maildir(args):
    # first make a dry run to check if every dir can be moved (the maildir shouldn't be changed concurrently of course)
    if not args.dry_run:
        print('Checking if everything should work')
        Kmail2Maildir(args, FileSystemAction(dry_run=True, quiet=True)).move_kmail_folders()

    Kmail2Maildir(args, FileSystemAction(args.dry_run)).move_kmail_folders()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert from kmail\'s maildir variant to plain maildir')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='only print what would be done, don\'t change anything yet')
    parser.add_argument('--remove-index-files', action='store_true', default=False,
                        help='remove kmail\'s index files')
    # courierimaps maildir++ documentation is vague about this separator.
    # It uses ':', but only as an example. dovecot uses '.' which is the default here
    parser.add_argument('--hierarchy-separator', default=DEFAULT_HIERARCHY_SEPARATOR,
                        help='Separator that should be used for maildir++ subfolders '
                             '(defaults to "%s")' % DEFAULT_HIERARCHY_SEPARATOR)
    parser.add_argument('folder')

    kmail2maildir(parser.parse_args())

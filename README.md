# kmail2maildir

This is a small script that I used to convert my kmail1 maildir-structure to the "normal" maildir++ format. The script
 is only tested with my kmail1-directory and with dovecot as a  target so currently it may be something more like a
 "kmail2dovecot" tool, but it may work for other targets too.

Important note: **ALWAYS** make a *backup* before you run the script, even if you only use `--dry-run` (which should not
 make any changes to the folder, but just print what would be done)


## License
GPLv3, see "COPYING" for details


## Sources
* [http://www.inter7.com/courierimap/README.maildirquota.html](README for Maildir++)
* [http://wiki2.dovecot.org/MailboxFormat/Maildir#Directory_Structure](Dovecot Directory Structure)


## Usage
    usage: kmail2maildir.py \[-h\] \[--dry-run\] \[--remove-index-files\]
                            \[--hierarchy-separator HIERARCHY_SEPARATOR\]
                            folder
    
    Convert from kmail's maildir variant to plain maildir
    
    positional arguments:
      folder
    
    optional arguments:
      -h, --help            show this help message and exit
      --dry-run             only print what would be done, don't change anything
                            yet
      --remove-index-files  remove kmail's index files
      --hierarchy-separator HIERARCHY_SEPARATOR
                            Separator that should be used for maildir++ subfolders
                            (defaults to ".")

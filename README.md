# plain_inc_bak

Simple but fast incremental backup script with optional encrypted upload to Amazon S3. Based on the method explained in [this excellent article by Mike Rubel](http://www.mikerubel.org/computers/rsync_snapshots/).

```
$ python3 plain_inc_bak.py --help

usage: plain_inc_bak.py [-h] [-o ORIGIN_DIR] [-B BACKUPS_DIR]
                        [-n BACKUP_BASENAME] [-m MAX_BACKUPS]
                        [-x EXCLUDE_DIRS] [-u] [-b S3_BUCKET] [-e]
                        [-p S3_GPG_PASS] [-a S3_AKEY] [-s S3_SECRET] [-E]
                        [-P EMAIL_PROGRAM] [-f EMAIL_FROM] [-d EMAIL_DEST]
                        [-D]

Incremental backup utility with optional upload to Amazon S3

optional arguments:
  -h, --help            show this help message and exit
  -o ORIGIN_DIR, --origin_dir ORIGIN_DIR
                        Origin directory to backup (will include subdirs
  -B BACKUPS_DIR, --backups_dir BACKUPS_DIR
                        Directory where the backups will be stored
  -n BACKUP_BASENAME, --backup_basename BACKUP_BASENAME
                        First part of the backup directory names (numbers will
                        be appended to it)
  -m MAX_BACKUPS, --max_backups MAX_BACKUPS
                        Maximum number of incremental backups to keep
  -x EXCLUDE_DIRS, --exclude_dirs EXCLUDE_DIRS
                        Comma separated list of directories to exclude from
                        the backup.This option will remove any other
                        configured exclude diretories
  -u, --upload_s3       Enable uploading to Amazon S3 of the most recent
                        backup
  -b S3_BUCKET, --s3_bucket S3_BUCKET
                        Name of the S3 bucket to upload
  -e, --s3_gpg_encrypt  Encrypt the backup with GPG before uploading to S3
  -p S3_GPG_PASS, --s3_gpg_pass S3_GPG_PASS
                        GPG passphrase to use for encrypted uploads
  -a S3_AKEY, --s3_akey S3_AKEY
                        S3 Access Key
  -s S3_SECRET, --s3_secret S3_SECRET
                        S3 Secret Key
  -E, --email_report    Send an email report
  -P EMAIL_PROGRAM, --email_program EMAIL_PROGRAM
                        Sendmail-style program to use for sending the email
  -f EMAIL_FROM, --email_from EMAIL_FROM
                        "From" field to use in the report email
  -d EMAIL_DEST, --email_dest EMAIL_DEST
                        Address where the report email will be sent
  -D, --dry_run         Dont really compress or upload anything
```

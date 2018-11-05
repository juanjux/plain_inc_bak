#!/usr/bin/env python3
__desc__ = "Incremental backup utility with optional upload to Amazon S3"
__autor__ = "Juanjo Alvarez <juanjo@juanjoalvarez.net>"
__license__ = "MIT"

import os, shutil, sys, subprocess, shlex
from traceback import format_exc
from typing import List, Any, Optional, Union

from functools import wraps
from time import time

"""
TODO:
    - Support for mounting and unmounting devices before/after the backup
    - Bandwith and IO limiting options, check:
          http://unix.stackexchange.com/questions/48138/how-to-throttle-per-process-i-o-to-a-max-limit0/
    - setup.py
    - Some examples of usage and integration on the README.md
"""

EMAIL_TEXTS = [] # type: List[str]


def config_error() -> None:
    print("No config.py file found in the script path or:")
    print("\t~/.config/plain_inc_bak/config.py")
    print("\t~/.plain_inc_bak_config.py")
    print("\t/etc/plain_inc_bak/config.py")
    print()
    print("If it's the first time running the script you should copy the ")
    print("config.example.py file to config.py in one of these directories ")
    print("and configure it")
    sys.exit(1)


config_file_path = find_config()
if config_file_path:
    import importlib.util as imputil
    spec = imputil.spec_from_file_location("c", config_file_path)
    if spec is None or spec.loader is None:
        config_error()
    else:
        c = imputil.module_from_spec(spec)
        spec.loader.exec_module(c)
else:
    config_error()


def message(text: str, email: bool = True) -> None:
    global EMAIL_TEXTS

    print(text)
    sys.stdout.flush()

    if c.EMAIL_REPORT and email:
        EMAIL_TEXTS.append(text)


def timeit(text: str):
    def decorator(func: Any) -> Any:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time()
            res = func(*args, **kwargs)
            seconds = int(time() - start)
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            elapsed = "%d:%02d:%02d" % (h, m, s)
            message('Time for {name}: {time}'.format(name=text, time=elapsed))
            return res
        return wrapper
    return decorator


def find_config() -> Optional[str]:
    """
    Find the path to the configuration files. Priority order is:
    1. (this file dir)
    2. ~/.config/plain_inc_bak/config.py
    3. ~/.plain_inc_bak_config.py
    3. /etc/plain_inc_bak/config.py
    Config files are *not* flattened, only one will be parsed
    """
    op = os.path

    curdir     = op.join(op.dirname(op.abspath(__file__)), 'config.py')
    userconfig = op.expanduser('~/.config/plain_inc_bak/config.py')
    userroot   = op.expanduser('~/.plain_inc_bak_config.py')
    etc        = '/etc/plain_inc_bak/config.py'

    for d in (curdir, userconfig, userroot, etc):
        if op.exists(d):
            return d
    return None


def parse_arguments() -> Any:
    def get_best_compressor() -> str:
        from shutil import which

        # I'm only considering relatively fast compressors. pigz
        # is fast and uses a lot less memory so its my favorite
        for compressor in ('pigz', 'pbzip2', 'plzip', 'gzip'):
            path = which(compressor)
            if path:
                return path
        else:
            raise Exception('Could not find any suitable compressor')
    # end inner function

    import argparse

    parser = argparse.ArgumentParser(description=__desc__)
    parser.add_argument('-o', '--origin_dir', default=getattr(c,'ORIGIN', None),
            help='Origin directory to backup (will include subdirs')
    parser.add_argument('-B', '--backups_dir', default=getattr(c,'BACKUPS_DIR', None),
            help='Directory where the backups will be stored')
    parser.add_argument('-n', '--backup_basename', default=getattr(c,'BACKUP_BASENAME', None),
            help='First part of the backup directory names (numbers will be appended to it)')
    parser.add_argument('-m', '--max_backups', type=int, default=getattr(c,'MAX_BACKUPS', 7),
            help='Maximum number of incremental backups to keep')
    parser.add_argument('-x', '--exclude_dirs', type=list, default=getattr(c,'EXCLUDE', []),
            help='Comma separated list of directories to exclude from the backup.' +
                 'This option will remove any other configured exclude diretories')
    parser.add_argument('-u', '--upload_s3', action='store_true',
            help='Enable uploading to Amazon S3 of the most recent backup')
    parser.add_argument('-b', '--s3_bucket', default=getattr(c, 'S3_BUCKET', None),
            help='Name of the S3 bucket to upload')
    parser.add_argument('-e', '--s3_gpg_encrypt', action='store_true',
            help='Encrypt the backup with GPG before uploading to S3')
    parser.add_argument('-p', '--s3_gpg_pass', default=getattr(c, 'S3_GPG_PASSPHRASE', None),
            help='GPG passphrase to use for encrypted uploads')
    parser.add_argument('-a', '--s3_akey', default=getattr(c,'S3_ACCESS_KEY', None),
            help='S3 Access Key')
    parser.add_argument('-s', '--s3_secret', default=getattr(c,'S3_SECRET_KEY', None),
            help='S3 Secret Key')
    parser.add_argument('-E', '--email_report', action='store_true',
            help='Send an email report')
    parser.add_argument('-P', '--email_program',
            default=getattr(c,'EMAIL_PROGRAM', '/usr/sbin/sendmail'),
            help='Sendmail-style program to use for sending the email')
    parser.add_argument('-f', '--email_from', default=getattr(c,'EMAIL_FROM', None),
            help='"From" field to use in the report email')
    parser.add_argument('-d', '--email_dest', default=getattr(c,'EMAIL_DEST', None),
            help='Address where the report email will be sent')
    parser.add_argument('-D', '--dry_run', action='store_true',
            help='Dont really compress or upload anything')
    parser.add_argument('-C', '--compressor', default=get_best_compressor(),
            help='Program for compressing backups before uploading. If missing a ' +
                 'program will be automatically selected')
    parser.add_argument('--nogpg', action='store_true',
        help='Avoid doing GPG compression when it would normally be configured to do so')
    parser.add_argument('--norotate', action='store_true',
        help='Avoid rotating the backups when it would normally be configured to do so')
    parser.add_argument('--norsync', action='store_true',
        help='Avoid doing the rsync to the .0 backup directory when it would normally '
             'be configured to do so')

    args = parser.parse_args()

    c.S3_UPLOAD_ENABLED = args.upload_s3 or c.S3_UPLOAD_ENABLED
    c.S3_BUCKET         = args.s3_bucket
    c.S3_ACCESS_KEY     = args.s3_akey
    c.S3_SECRET_KEY     = args.s3_secret
    c.S3_GPG_ENCRYPT    = args.s3_gpg_encrypt or c.S3_GPG_ENCRYPT
    c.EMAIL_REPORT      = args.email_report or c.EMAIL_REPORT
    c.EMAIL_PROGRAM     = args.email_program
    c.EMAIL_FROM        = args.email_from
    c.EMAIL_DEST        = args.email_dest
    c.DRY_RUN           = args.dry_run or c.DRY_RUN
    c.ORIGIN            = args.origin_dir
    c.BACKUPS_DIR       = args.backups_dir
    c.BACKUP_BASENAME   = args.backup_basename or 'backup'
    c.MAX_BACKUPS       = args.max_backups
    c.EXCLUDE           = args.exclude_dirs
    c.COMPRESSOR        = args.compressor
    c.NOGPG             = args.nogpg
    c.NOROTATE          = args.norotate
    c.NORSYNC           = args.norsync

    def printerror(msg):
        print('Error: {}'.format(msg), file=sys.stderr)
        parser.print_help()
        exit(1)

    if c.S3_UPLOAD_ENABLED and not (c.S3_BUCKET or c.S3_ACCESS_KEY or c.S3_SECRET_KEY):
        printerror('enabled S3 uploads require the bucket, access_key and secret_key options',)

    if c.S3_GPG_ENCRYPT and not c.S3_GPG_PASSPHRASE:
        printerror('gpg encrypting needs a gpg passphrase')

    if c.EMAIL_REPORT and not (c.EMAIL_PROGRAM or c.EMAIL_FROM or c.EMAIL_DEST):
        printerror('enabled email reports require the program, from and destination')

    if not c.ORIGIN:
        printerror('you need to configure an origin directory')

    if not c.BACKUPS_DIR:
        printerror('you need to configure a backups destination direcory')


@timeit(text='RSync to the most recent directory')
def rsync_first(zerodir):
    # Now do the real backup with rsync
    excludeparams = ['--exclude={}/*'.format(i) for i in c.EXCLUDE]
    rsynccmd = ['/usr/bin/rsync', '-azAXSH', '--delete', *excludeparams, c.ORIGIN, zerodir]
    message('Running rsync with:\n{}'.format(' '.join(rsynccmd)))

    subprocess.check_call(rsynccmd)
    message('Rsync completed successfully')


@timeit(text='Backup compression for upload')
def compress_backup(dirpath: str) -> str:
    outpath = dirpath + '.tar.gz'
    message('Compressing directory {} to {}'.format(dirpath, outpath))

    # Remove the leading '/'; we'll instruct tar to change to the root directory
    # with the -C / option thus avoiding the "removing leading /" message
    if dirpath.startswith('/'):
        dirpath = dirpath[1:]

    compressor = c.COMPRESSOR
    cmd = "tar c --warning='no-file-ignored' --directory=/ {dirpath}|{compressor} > {outpath}"\
            .format(**locals())
    print(cmd)

    if not c.DRY_RUN:
        output = subprocess.check_output(cmd, shell=True).decode()
        message(output)

    return outpath

@timeit(text='GPG encrypting the backup for upload')
def gpg_encrypt_file(filepath: str) -> str:
    gpgpath = filepath + '.gpg'
    if os.path.exists(gpgpath):
        message('Warning: deleting previously existing GPG file: {}'.format(gpgpath))
        os.unlink(gpgpath)

    cmd = 'gpg --batch --symmetric --cipher-algo AES256 --passphrase-fd 0 {}'.format(filepath)
    message('Encrypting backup with command: {}'.format(cmd))
    if not c.DRY_RUN:
        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE,
                stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate(c.S3_GPG_PASSPHRASE.encode())

        if p.returncode != 0:
            raise Exception('Could not encrypt file: {}'.format(stdout + stderr))

    message('File encrypted successfully')
    return gpgpath

@timeit(text='Uploading to S3')
def upload_s3(dirpath: str) -> None:
    import boto3, time

    real_filepath = ''
    compressed_filepath = compress_backup(dirpath)

    if c.S3_GPG_ENCRYPT and not c.NOGPG:
        real_filepath = gpg_encrypt_file(compressed_filepath)

    real_filepath = compressed_filepath if not real_filepath else real_filepath
    datepart = time.strftime("%Y%m%d%H%M%S")
    remote_filename = os.path.split(real_filepath)[1] + '.' + datepart

    with open(real_filepath, 'rb') as data:
        message('Uploading file to Amazon S3')

        if not c.DRY_RUN:
            s3 = boto3.client('s3', aws_access_key_id=c.S3_ACCESS_KEY,
                    aws_secret_access_key=c.S3_SECRET_KEY)
            s3.upload_fileobj(data, c.S3_BUCKET, remote_filename)

    if not c.DRY_RUN:
        if c.S3_GPG_ENCRYPT:
            # Remove the local encrupted file
            os.unlink(real_filepath)
        os.unlink(compressed_filepath)

    message('File uploaded to S3 bucket "{}" as key "{}"'.
            format(c.S3_BUCKET, remote_filename))


def send_mail(subject: str, content: str) -> None:
    # The machine wont have a real smtp server, only a MDA, and the script wont have access to
    # external SMTP servers, so a sendmail-style binary will be used for delivery

    from textwrap import dedent

    from_ = c.EMAIL_FROM
    to = c.EMAIL_DEST

    real_content = dedent('''\
        From: {from_}
        To: {to}
        Subject: {subject}

        {content}

    '''.format(**locals()))

    sendmail = subprocess.Popen([c.EMAIL_PROGRAM, to], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, bufsize=1)
    stdout, stderr = sendmail.communicate(bytearray(real_content, 'utf-8'))


@timeit(text='Rotating backups')
def rotate_backups(backup_dirs: List[str]) -> None:
    backup_nums = sorted([int(i.split('.')[1]) for i in backup_dirs])
    backup_nums.reverse()

    for i in backup_nums:
        full_dirname = os.path.join(c.BACKUPS_DIR, '{}.{}'.format(c.BACKUP_BASENAME, i))

        if i >= c.MAX_BACKUPS:
            # Delete the oldest ones
            message('Deleting {}'.format(full_dirname))
            if not c.DRY_RUN:
                shutil.rmtree(full_dirname)
        else:
            # Rename to the greater number except for the 0 which will be
            # copied with hard links
            inc_dirname = os.path.join(c.BACKUPS_DIR, '{}.{}'.format(c.BACKUP_BASENAME, i+1))
            dir_params = (full_dirname, inc_dirname) # DRY

            if i == 0:
                message('Hardlink-copying "{}" => "{}"'.format(*dir_params))
                if not c.DRY_RUN:
                    ret = os.system('cp -al {} {}'.format(*dir_params))
                    if ret != 0:
                        raise Exception('cp -al returned error {}!'.format(ret))
            else:
                message('Moving "{}" => "{}"'.format(*dir_params))
                if not c.DRY_RUN:
                    shutil.move(*dir_params)


def main() -> int:
    try:
        parse_arguments()

        if not os.path.exists(c.BACKUPS_DIR):
            raise Exception('Missing backups dir: {}'.format(c.BACKUPS_DIR))

        backup_dirs = [i for i in os.listdir(c.BACKUPS_DIR)
                       if i.startswith(c.BACKUP_BASENAME) and
                           os.path.isdir(os.path.join(c.BACKUPS_DIR, i))]
        if backup_dirs and not c.NOROTATE:
            rotate_backups(backup_dirs)

        zerodir = os.path.join(c.BACKUPS_DIR, '{}.0'.format(c.BACKUP_BASENAME))
        if not c.DRY_RUN and not c.NORSYNC:
            rsync_first(zerodir)

        if c.S3_UPLOAD_ENABLED:
            upload_s3(zerodir)

    except Exception as e:
        backup_completed = False
        message(format_exc())

        if hasattr(e, 'output'):
            message(e.output) # type: ignore
    else:
        backup_completed = True

    if backup_completed :
        email_subject = '[BACKUP SUCESS] Backup completed'
    else:
        email_subject = '[BACKUP FAILED] Backup problems!'

    if c.EMAIL_REPORT:
        send_mail(email_subject, '\n'.join(EMAIL_TEXTS))

    return 0 if backup_completed else 1


if __name__ == '__main__':
    sys.exit(main())

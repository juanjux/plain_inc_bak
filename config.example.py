DRY_RUN         = False
# The base or root directory to backup. Subdirectories will be included,
# except the ones in EXCLUDE
ORIGIN          = '/'
# Directory where the backups will be stored
BACKUPS_DIR     = '/backups'
# Name of the backup directories. A .# with a number will be appended, with 0 being
# the most recent one
BACKUP_BASENAME = 'backup'
# Maximum number of incremental backups to keep. When this number is reached, the
# oldest backup will be deleted before rotating the others
MAX_BACKUPS     = 5
# Exclude directories. Please include BACKUPS_DIR or funny things could happen
EXCLUDE         = [
        '/dev', '/proc', '/sys', '/tmp', '/run', '/mnt', '/media',
        '/lost+found', '/cdrom', '/var/cache/apt/archives', '/var/crash',
        '/var/lib/lxcfs',
        BACKUPS_DIR
]

# Email settings - pretty self explanatory
EMAIL_REPORT  = False
# Currently the program uses a sendmail style binary to send the emails. SMTP is not supported
EMAIL_PROGRAM = '/usr/sbin/sendmail'
EMAIL_FROM    = 'Backup System <noreply@example.com>'
EMAIL_DEST    = 'your@email.com'

# S3 Upload settings

# Note: this wont delete old files. Use the bucket Property Lifecycle->Rules to add
# a rule to delete the files after a certain time (like 30 days).
S3_UPLOAD_ENABLED = False
S3_BUCKET = "bucket-name"
# AWS access and secret keys. Please dont use your root credentials if you
# have them but create an IAM user with read/write access to S3 only.
S3_ACCESS_KEY = 'YOURKEY'
S3_SECRET_KEY = 'YOURSECRET'
# This will enable gpg encryption of the backup before uploading
S3_GPG_ENCRYPT = True
# Passphrase to use for encrypting. Choose a strong one and dont lose it
S3_GPG_PASSPHRASE = 'some_strong_password'

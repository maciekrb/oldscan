#!/bin/sh

# This script is started by scanbuttond whenever a scanner button has been pressed.
# Scanbuttond passes the following parameters to us:
# $1 ... the button number
# $2 ... the scanner's SANE device name, which comes in handy if there are two or 
#        more scanners. In this case we can pass the device name to SANE programs 
#        like scanimage.
# vendor="Genius (KYE)", product="ColorPage-HR6 V2"


# daemon's name
DAEMON=scanbuttond

# securely create temporary file to avoid race condition attacks
TMP_TIFF_FILE=`mktemp /tmp/$DAEMON.XXXXXX.tiff`
TMP_JPEG_FILE=`mktemp /tmp/$DAEMON.XXXXXX.jpg`
TMP_PDF_FILE=`mktemp /tmp/$DAEMON.XXXXXX.pdf`

# lock file
LOCKFILE="/tmp/$DAEMON.lock"

# device name
DEVICE="$2"

# remove temporary file on abort
trap 'rm -f $TMP_TIFF_FILE' 0 1 15
trap 'rm -f $TMP_JPEG_FILE' 0 1 15
trap 'rm -f $TMP_PDF_FILE' 0 1 15

# function: create lock file with scanbuttond's PID
mk_lock() {
  pidof $DAEMON > $LOCKFILE
}

# function: check if lock file exists and print an error message with zenity (if it's installed)
chk_lock() {
  if [ -e $LOCKFILE ]; then
    exit 1
  fi
}


# function: remove temporary and lock files
clean_up () {
  test -e $LOCKFILE && rm -f $LOCKFILE
  rm -f $TMP_TIFF_FILE $TMP_JPEG_FILE $TMP_PDF_FILE
}

# function: the actual scan command (modify to match your setup)
scanColor() {
  scanimage --format tiff --mode Color \
    --resolution 150 --depth 14 -x 215 -y 297 > $TMP_TIFF_FILE
}

scanGray() {
  scanimage --format tiff --mode Gray \
    --resolution 150 --depth 14 -x 215 -y 297 --brightness -3 > $TMP_TIFF_FILE
}

case $1 in
  1)
    # button 1 (gray scan): scan the picture and send it to Google Drive
    chk_lock; mk_lock; 
    scanGray
    convert $TMP_TIFF_FILE -quality 85 -quiet -format JPEG $TMP_JPEG_FILE
    #tiff2ps -z -w 8.5 -h 11 $TMPFILE | lpr
    sendto gdrive --attachment=$TMP_JPEG_FILE "Some Folder" $TMP_JPEG_FILE
    clean_up
  ;;
  2)
    # button 2 (color scan): scan the picture & sendit to Google Drive
    chk_lock; mk_lock
    scanColor
    convert $TMP_TIFF_FILE -quality 85 -quiet -format JPEG $TMP_JPEG_FILE
    sendto gdrive --attachment=$TMP_JPEG_FILE "Some Folder" $TMP_JPEG_FILE
    clean_up
  ;;
  3)
    # button 3 (evernote): scan picture and send it to Evernote
    chk_lock; mk_lock
    scanColor
    #convert $TMP_TIFF_FILE -quality 85 -quiet -format PDF $TMP_PDF_FILE
    convert $TMP_TIFF_FILE -quality 30 -compress jpeg2000 -quiet $TMP_PDF_FILE
    sendto evernote --attachment=$TMP_PDF_FILE --  "-INBOX" "I need a name"
    clean_up
  ;;
  4)
  # button 4 (web): 
  ;;
esac


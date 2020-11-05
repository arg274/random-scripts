import argparse
import logging
import os
import re
import shutil
import sys
from pprint import pprint

import mutagen
from mutagen.mp3 import BitrateMode

logger = logging.getLogger('filetransfer')
logfilehandler = logging.FileHandler('music_library_namer.log', encoding='utf-8')
logformatter = logging.Formatter(u'%(asctime)s %(name)-10s %(levelname)-8s %(message)s')
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.addHandler(logfilehandler)
logger.setLevel(logging.INFO)
logfilehandler.setFormatter(logformatter)


class TagChalice(dict):

    audiofile = None

    def __init__(self):
        super().__init__()

    def populate(self, audiofile):

        self.audiofile = audiofile
        self['title'] = tagchooser(self.audiofile, 'TIT2', 'TITLE', '©nam')
        self['artist'] = tagchooser(self.audiofile, 'TPE1', 'ARTIST', '©ART')
        self['album'] = tagchooser(self.audiofile, 'TALB', 'ALBUM', '©alb')
        self['albumartist'] = tagchooser(self.audiofile, 'STDALBUMARTIST', '----:com.apple.iTunes:STDALBUMARTIST',
                                         'TPE2', 'ALBUMARTIST', 'aART')
        self['tracknumber'] = tagchooser(self.audiofile, 'TRCK', 'TRACKNUMBER', 'trkn')
        self['totaltracks'] = tagchooser(self.audiofile, 'TRACKTOTAL', 'TOTALTRACKS')
        self['discnumber'] = tagchooser(self.audiofile, 'TPOS', 'DISCNUMBER', 'disk')
        self['totaldiscs'] = tagchooser(self.audiofile, 'DISCTOTAL', 'TOTALDISCS')
        self['discsubtitle'] = tagchooser(self.audiofile, 'TSST', 'DISCSUBTITLE', '----:com.apple.iTunes:DISCSUBTITLE')
        self['date'] = tagchooser(self.audiofile, 'TDRC', 'TYER', 'DATE', '©day')
        self['originaldate'] = tagchooser(self.audiofile, 'TDOR', 'TORY', 'ORIGINALDATE',
                                          '----:com.apple.iTunes:originaldate')
        self['year'] = '0000'
        self['media'] = tagchooser(self.audiofile, 'TMED', 'MEDIA', '----:com.apple.iTunes:MEDIA')
        self['pretty_media'] = 'OTHER'
        self['catalog'] = tagchooser(self.audiofile, 'TXXX:CATALOGNUMBER', 'CATALOGNUMBER',
                                     '----:com.apple.iTunes:CATALOGNUMBER', 'BARCODE', '----:com.apple.iTunes:BARCODE')
        self['musicbrainz_albumid'] = tagchooser(self.audiofile, 'TXXX:MusicBrainz Album Id', 'MUSICBRAINZ_ALBUMID',
                                                 '----:com.apple.iTunes:MusicBrainz Album Id')
        self['displayartist'] = 'Unknown Artist'

        self.fixmapping()

    def fixmapping(self):

        if 'mp3' in self.audiofile.mime[0]:
            if self['tracknumber'] is not None and '/' in self['tracknumber']:
                temp = self['tracknumber'].split('/', 2)
                # print(temp)
                self['tracknumber'] = int(temp[0])
                self['totaltracks'] = int(temp[1])
            if self['discnumber'] is not None and '/' in self['discnumber']:
                temp = self['discnumber'].split('/', 2)
                # print(temp)
                self['discnumber'] = int(temp[0])
                self['totaldiscs'] = int(temp[1])

            if self['originaldate'] is not None:
                self['year'] = str(self['originaldate'])[0:4]
            elif self['date'] is not None:
                self['year'] = str(self['date'])[0:4]

        elif 'flac' in self.audiofile.mime[0] or 'ogg' in self.audiofile.mime[0]:
            self['tracknumber'] = 0 if self['tracknumber'] is None else int(self['tracknumber'])
            self['totaltracks'] = 0 if self['totaltracks'] is None else int(self['totaltracks'])
            self['discnumber'] = 0 if self['discnumber'] is None else int(self['discnumber'])
            self['totaldiscs'] = 0 if self['totaldiscs'] is None else int(self['totaldiscs'])

            if self['date'] is not None:
                self['year'] = str(self['date'])[0:4]

        elif 'mp4' in self.audiofile.mime[0]:
            custom_tags = ['originaldate', 'media', 'musicbrainz_albumid', 'catalog']

            if self['discnumber'] is not None:
                # print(self['discnumber'])
                self['totaldiscs'] = int(self['discnumber'][1])
                self['discnumber'] = int(self['discnumber'][0])
            if self['tracknumber'] is not None:
                # print(self['tracknumber'])
                self['totaltracks'] = int(self['tracknumber'][1])
                self['tracknumber'] = int(self['tracknumber'][0])

            if self['originaldate'] is not None:
                self['year'] = bytetostr(self['originaldate'])[0:4]
            elif self['date'] is not None:
                self['year'] = bytetostr(self['date'])[0:4]

            for custom_tag in custom_tags:
                if self[custom_tag] is not None:
                    self[custom_tag] = self[custom_tag].decode('utf-8')

        if self['albumartist'] is not None or self['artist'] is not None:
            self['displayartist'] = self['albumartist'] if self['albumartist'] is not None else self['artist']

        if self['media'] is not None:
            if 'CD' in self['media']:
                self['pretty_media'] = 'CD'
            elif 'Digital' in self['media']:
                self['pretty_media'] = 'WEB'
            elif 'Vinyl' in self['media']:
                self['pretty_media'] = 'VNL'
            elif 'Cassette' in self['media']:
                self['pretty_media'] = 'CST'
            elif 'DVD' in self['media']:
                self['pretty_media'] = 'DVD'
            elif 'Blu-ray' in self['media']:
                self['pretty_media'] = 'BD'
            elif 'GameRip' in self['media']:
                self['pretty_media'] = 'VGR'

        if not self['catalog'] or self['catalog'] == '[none]':
            self['catalog'] = 'No Cat#'
        else:
            self['catalog'] = self['catalog'].upper()

        for tag in ['tracknumber', 'totaltracks', 'discnumber', 'totaldiscs']:
            if self[tag] is None:
                self[tag] = 0


class InfoChalice(dict):

    audiofile = None

    def __init__(self):
        super().__init__()

    def populate(self, audiofile):

        self.audiofile = audiofile
        self['mime'] = self.audiofile.mime[0]
        self['pretty_mime'] = None
        self['bitrate'] = None
        self['pretty_bitrate'] = None
        self['samplerate'] = None
        self['pretty_samplerate'] = None
        self['encoder_settings'] = None
        self['bitrate_mode'] = None
        self['pretty_bitrate_mode'] = None
        self['bps'] = None

        self.fixmapping()

    def fixmapping(self):

        if 'mp3' in self['mime']:
            self['pretty_mime'] = 'mp3'
            self['bitrate'] = self.audiofile.info.bitrate
            self['pretty_bitrate'] = bitrateformatter(self['bitrate'] / 1000)
            self['bitrate_mode'] = self.audiofile.info.bitrate_mode
            self['samplerate'] = float(self.audiofile.info.sample_rate)
            self['pretty_samplerate'] = sampleformatter(self['samplerate'])
            self['encoder_settings'] = self.audiofile.info.encoder_settings
            if self['bitrate_mode'] == BitrateMode.CBR \
                    or (self['bitrate_mode'] == BitrateMode.UNKNOWN and self['pretty_bitrate'] % 32 == 0):
                self['pretty_bitrate_mode'] = 'CBR'
            elif self['bitrate_mode'] == BitrateMode.VBR:
                quality = re.search('-V (\d{1})', self['encoder_settings'])
                if quality:
                    logger.debug('Encoder settings: V' + quality.group(1))
                    self['pretty_bitrate_mode'] = 'V' + quality.group(1)
                else:
                    self['pretty_bitrate_mode'] = 'VBR'
            elif self['bitrate_mode'] == BitrateMode.ABR:
                self['pretty_bitrate_mode'] = 'ABR'

        elif 'flac' in self['mime']:
            self['pretty_mime'] = 'flac'
            self['bitrate'] = self.audiofile.info.bitrate
            self['pretty_bitrate'] = bitrateformatter(self['bitrate'] / 1000)
            self['samplerate'] = float(self.audiofile.info.sample_rate)
            self['pretty_samplerate'] = sampleformatter(self['samplerate'])
            self['bps'] = self.audiofile.info.bits_per_sample

        elif 'mp4' in self['mime']:
            self['pretty_mime'] = self.audiofile.info.codec if self.audiofile.info.codec != 'mp4a.40.2' else 'aac-lc'
            self['bitrate'] = self.audiofile.info.bitrate
            self['pretty_bitrate'] = bitrateformatter(self['bitrate'] / 1000)
            self['bps'] = self.audiofile.info.bits_per_sample
            self['samplerate'] = float(self.audiofile.info.sample_rate)
            self['pretty_samplerate'] = sampleformatter(self['samplerate'])
            self['encoder_settings'] = tagchooser(self.audiofile, '©too')
            if self['encoder_settings'] is not None:
                parse_encoder = self['encoder_settings'].upper()
                if 'TVBR' in parse_encoder:
                    self['pretty_bitrate_mode'] = 'TVBR'
                elif 'CONSTRAINED VBR' in parse_encoder:
                    self['pretty_bitrate_mode'] = 'CVBR'
                elif 'NERO' in parse_encoder and self['pretty_bitrate'] % 32 != 0:
                    self['pretty_bitrate_mode'] = 'NeroVBR'

        elif 'ogg' in self['mime']:
            if str(type(self.audiofile).__name__) == 'OggOpus':
                self['pretty_mime'] = 'opus'
            else:
                self['pretty_mime'] = 'ogg'


def sanitise(node):

    invalidpattern = '[<>:"|?*]'
    invaliddevicenames = '^(CON|PRN|AUX|NUL|COM1|COM2|COM3|COM4|COM5|COM6|' \
                         'COM7|COM8|COM9|LPT1|LPT2|LPT3|LPT4|LPT5|LPT6|LPT7|LPT8|LPT9)$'
    invalidtrail = r'\.+$'
    subchar = '_'

    phase_one = re.sub(invalidpattern, subchar, node)
    phase_two = re.sub(invaliddevicenames, subchar, phase_one)
    phase_three = phase_two.replace('/', '_').replace('\\', '_')
    phase_four = re.sub(invalidtrail, '', phase_three.strip(' '))

    return phase_four.strip(' ')


def truncate(node, charlimit):

    if len(node) > charlimit:
        if ' ' in node:
            trunc = node.rsplit(' ', 1)[0]
        else:
            trunc = node[0:charlimit]
        return truncate(trunc, charlimit)

    return node


def tagchooser(audiofile, *args):

    value = None

    for val in args:
        try:
            if audiofile.get(val) is not None:
                value = audiofile.get(val)[0]
                break
        except ValueError:
            pass

    return value


def bytetostr(data):

    try:
        data = data.decode()
    except (UnicodeDecodeError, AttributeError):
        pass

    return data


def bitrateformatter(bitrate):

    roundedbitrate = int(round(bitrate))

    if roundedbitrate % 32 == 0:
        return roundedbitrate

    elif roundedbitrate > 10:
        for x in range(int(round(bitrate - 10)), int(round(bitrate + 11))):
            if x % 32 == 0:
                roundedbitrate = x
                break

    return roundedbitrate


def sampleformatter(samplerate):

    if round(samplerate) % 1000 == 0:
        return str(int(samplerate / 1000))
    else:
        return str(float(samplerate / 1000))


def formatter(filetags, fileinfo):

    artistdir = filetags['displayartist']
    albumdir = ''
    trackpath = ''

    catalog = ''
    encoding = ''
    track = ''
    disc = ''

    trunc_charlimit = 80

    # MP3 specific settings
    if fileinfo['pretty_mime'] == 'mp3':
        bitrate_mode = ''
        if fileinfo['pretty_bitrate_mode'] is None:
            bitrate_mode = 'UNDEFINED'
        elif fileinfo['pretty_bitrate_mode'] == 'CBR':
            bitrate_mode = str(fileinfo['pretty_bitrate'])
        else:
            bitrate_mode = fileinfo['pretty_bitrate_mode']
        encoding = '{} - {}'.format(fileinfo['pretty_mime'].upper(), bitrate_mode)

    # FLAC/ALAC specific settings
    elif fileinfo['pretty_mime'] == 'flac' or fileinfo['pretty_mime'] == 'alac':
        encoding = '{} - {}-{}'.format(fileinfo['pretty_mime'].upper(),
                                       str(fileinfo['bps']), fileinfo['pretty_samplerate'])
        catalog = ' {{{}}}'.format(filetags['catalog'])

    # AAC specific settings
    elif fileinfo['pretty_mime'] == 'aac-lc':
        if fileinfo['pretty_bitrate_mode'] is not None:
            encoding = '{} - {}'.format(fileinfo['pretty_mime'].upper(), fileinfo['pretty_bitrate_mode'])
        else:
            encoding = '{} - {}'.format(fileinfo['pretty_mime'].upper(), fileinfo['pretty_bitrate'])

    # Opus specific settings
    elif fileinfo['pretty_mime'] == 'opus':
        encoding = '{}'.format(fileinfo['pretty_mime'].upper())

    # Disc handling
    if filetags['discsubtitle'] is not None:
        disc = '{} - {}'.format(filetags['discnumber'], truncate(bytetostr(filetags['discsubtitle']), trunc_charlimit))
    elif filetags['totaldiscs'] > 5:
        disc = 'Disc ' + str(filetags['discnumber'])
    else:
        disc = str(filetags['discnumber'])

    # Track number handling
    if filetags['tracknumber'] != 0:
        if filetags['totaltracks'] != 0:
            padnum = 2 if len(str(filetags['totaltracks'])) <= 2 else len(str(filetags['totaltracks']))
            track = str(filetags['tracknumber']).zfill(padnum)
        else:
            track = str(filetags['tracknumber'])
    else:
        track = '00'

    # Extension determining
    ext = ''

    if 'audio' in fileinfo['mime']:
        tempext = fileinfo['mime'].split('/')[1]
        if tempext == 'mp4':
            ext = '.m4a'
        elif tempext == 'ogg':
            ext = '.' + fileinfo['pretty_mime']
        else:
            ext = '.' + tempext

    # File path merge
    artistdir = sanitise(truncate(artistdir, trunc_charlimit))
    albumdirpre = '{} - {}'.format(artistdir, truncate(filetags['album'], trunc_charlimit))
    albumdir = "{} ({}) [{} - {}]{}".format(albumdirpre, filetags['year'], filetags['pretty_media'], encoding, catalog)
    tracknodisc = "{} - {}".format(track, truncate(filetags['title'], trunc_charlimit))

    while len(artistdir + albumdir + disc + tracknodisc) > 230:

        words = tracknodisc.split(' - ', maxsplit=1)[1].split(r'\w')
        if len(words) == 1 and len(words[0]) <= 10:
            break

        trunc_charlimit = trunc_charlimit - 5
        tracknodisc = truncate(tracknodisc, trunc_charlimit)

    if disc == '0' or filetags['totaldiscs'] == 1:
        trackpath = sanitise(tracknodisc)
        albumdir = sanitise(albumdir)
    elif 'Disc' in disc or filetags['discsubtitle'] is not None:
        disc = sanitise(disc)
        albumdir = os.path.join(sanitise(albumdir), sanitise(disc))
        trackpath = sanitise(tracknodisc)
    else:
        trackpath = sanitise("{}.{}".format(disc, tracknodisc))
        albumdir = sanitise(albumdir)

    return artistdir, albumdir, trackpath + ext


def trackparser(filepath, destroot, dryflag):

    filetags = TagChalice()
    fileinfo = InfoChalice()
    audiofile = mutagen.File(filepath)
    fileinfo.populate(audiofile)
    filetags.populate(audiofile)
    # pprint(fileinfo)
    # pprint(filetags)
    filepathroot = os.path.dirname(__file__).replace('/', '\\')
    filepath = os.path.join(filepathroot, filepath)
    artistdir, albumdir, filename = formatter(filetags, fileinfo)
    dest = os.path.join(filepathroot, destroot, artistdir, albumdir, filename)

    if os.path.isfile(dest):
        logger.warning('File already exists: ' + dest)
    else:
        try:
            if dryflag is False:
                os.makedirs(os.path.join(filepathroot, destroot, artistdir, albumdir), exist_ok=True)
                shutil.move(filepath, dest)
            logger.info('File transferred to: ' + dest)
        except OSError as e:
            logger.error('File transfer failed: ' + str(e))


def rootiterator(rootpath, dest, dryflag):

    allowedexts = ['mp3', 'flac', 'm4a', 'opus']

    for root, subdirs, files in os.walk(rootpath):
        for filename in files:
            for ext in allowedexts:
                if filename.endswith(ext):
                    filepath = os.path.join(root, filename)
                    trackparser(filepath, dest, dryflag)
                    break


def main():

    parser = argparse.ArgumentParser(description='Tool for library structuring')
    parser.add_argument('src', type=str, help='Source dir')
    parser.add_argument('dest', type=str, help='Destination dir')
    parser.add_argument('--dry', action='store_true', help='Dry run without transferring the files')
    args = parser.parse_args()
    rootiterator(args.src, args.dest, args.dry)


if __name__ == '__main__':
    main()

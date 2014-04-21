import os
import logging
from django.core.management.base import BaseCommand, CommandError
from progressbar import ProgressBar
from analysis.models import MusicData, MusicXMLScore
import music21
from music21.musedata.base40 import pitchToBase40
from music21.interval import notesToInterval, notesToChromatic

logging.basicConfig(filename='importmusic.log',level=logging.ERROR)


def all_notes(score):
    # FIXME: is this still valid?
    # For some reason Stream([n for n in score.flat.notes]) accumulate
    # notes in the wrong order, so we append them explicitly.

    stream = music21.stream.Stream()
    for n in score.flat.notes.stripTies():
        if n.isChord:
            stream.append(n[-1])
        else:
            stream.append(n)
    return stream


def intervals_without_direction(notes):
    size = len(notes)
    pos = zip(range(size-1), range(1, size))
    return [notesToInterval(notes[x], notes[y]).name for x, y in pos]


def intervals_with_direction(notes):
    size = len(notes)
    pos = zip(range(size-1), range(1, size))
    return [notesToInterval(notes[x], notes[y]).directedName for x, y in pos]


def intervals_midi(notes):
    size = len(notes)
    pos = zip(range(size-1), range(1, size))
    return [notesToChromatic(notes[x], notes[y]).semitones for x, y in pos]


def make_music_data(music_stream, musicdata):
    notes = all_notes(music_stream)
    musicdata.notes_midi = [note.midi for note in notes]
    musicdata.notes = [pitchToBase40(note) for note in notes]
    musicdata.intervals = intervals_without_direction(notes)
    musicdata.intervals_midi = intervals_midi(notes)
    musicdata.intervals_with_direction = intervals_with_direction(notes)
    musicdata.durations = [note.duration.quarterLength for note in notes]

    _key = music_stream.analyze("key")
    musicdata.mode = _key.mode
    musicdata.key = _key.tonic.name
    musicdata.key_midi = _key.tonic.midi

    _measures = music_stream.parts[0].getElementsByClass("Measure")
    musicdata.time_signature = _measures[0].timeSignature.ratioString
    musicdata.ambitus = music_stream.analyze("ambitus").chromatic.directed

    # FIXME: add Contour and total_duration
    musicdata.contour = [1, 3, 4]
    musicdata.total_duration = 39.5


def import_xml_file(filename, options):
    base_filename = os.path.basename(filename)
    code = os.path.splitext(base_filename)[0]

    # Don't create a new MusicXMLScore unless it's necessary
    try:
        score = MusicXMLScore.objects.get(code=code)
    except MusicXMLScore.DoesNotExist:
        with open(filename) as text_score:
            score = MusicXMLScore(filename=base_filename, code=code, score=text_score)
            score.save()

    # Don't create a new MusicData unless it's necessary
    try:
        MusicData.objects.get(score=score)
        return 0
    except MusicData.DoesNotExist:
        musicdata = MusicData(score=score)
        try:
            music = music21.converter.parse(filename)
            make_music_data(music, musicdata)
            musicdata.save()
            return 0
        except Exception as error:
            logging.error("Couldn't parse music file: %s, %s" % (error, base_filename))
            return 1


class Command(BaseCommand):
    args = '<file1 [file2 ...]>'
    help = 'Import music data from MusicXML files'

    def handle(self, *args, **options):
        progress = ProgressBar()
        results = 0

        for filename in progress(args):
            result = import_xml_file(filename, options)
            results += result

        if results > 0:
            self.stdout.write("\nERROR: There are parsing errors, please check the log file.")

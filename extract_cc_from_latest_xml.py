from os import listdir, path
from subprocess import call
import FileReaders as FR

# Data
sourceFiles = [
    # FR.TouchOSCReader(latest_file_of_type_in_dir('/Users/jonnie/My Drive/Documents/Music Production/Peripherals/TouchOSC','xml')),
    # FR.AbletonReader(latest_file_of_type_in_dir('/Users/jonnie/My Drive/Documents/Music Production/Ableton user library/Templates','als')),
    # FR.MIDIFighterTwisterReader(latest_file_of_type_in_dir('/Users/jonnie/My Drive/Documents/Music Production/Peripherals/MIDI Fighter Twister','mfs')),
    FR.S49Reader('/Users/jonnie/Library/Application Support/Native Instruments/Komplete Kontrol/Komplete Kontrol MK2 Settings.dat'),
]
outputFileName = 'Extracted MIDI.csv'

def latest_file_of_type_in_dir(directory, extension):
    sourceFiles = [f for f in listdir(directory) if path.isfile(path.join(directory, f))]
    fileName = max(list(filter(lambda x: f'.{extension}' in x, sourceFiles)))
    return path.join(directory, fileName)
    
# Get messages from source files
for file in sourceFiles:
    file.read()
# Save messages to file
FR.writeFileReadersToFile(sourceFiles, outputFileName)
# Open saved file
call(('open', outputFileName))
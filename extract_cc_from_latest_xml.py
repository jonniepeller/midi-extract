from os import listdir, path
import FileReaders as FR

def latest_file_of_type_in_dir(directory, extension):
    files = [f for f in listdir(directory) if path.isfile(path.join(directory, f))]
    fileName = max(list(filter(lambda x: f'.{extension}' in x, files)))
    return path.join(directory, fileName)
    
files = [
    FR.TouchOSCReader(latest_file_of_type_in_dir('/Users/jonnie/My Drive/Documents/Music Production/Peripherals/TouchOSC','xml')),
    FR.AbletonReader(latest_file_of_type_in_dir('/Users/jonnie/My Drive/Documents/Music Production/Ableton user library/Templates','als')),
    # FR.MIDIFighterTwisterReader(latest_file_of_type_in_dir('/Users/jonnie/My Drive/Documents/Music Production/Peripherals/MIDI Fighter Twister','mfs')),
]

for file in files:
    file.read()

FR.writeFileReadersToFile(files, 'Extracted MIDI.csv')
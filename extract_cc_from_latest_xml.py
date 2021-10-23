from os import listdir, linesep, path, remove
from lxml import etree
import shutil
import gzip

def latest_file_of_type_in_dir(directory, extension):
    files = [f for f in listdir(directory) if path.isfile(path.join(directory, f))]
    fileName = max(list(filter(lambda x: f'.{extension}' in x, files)))
    return path.join(directory, fileName)

class MIDICCMessage:
    def __init__(self, source, name, channel, cc) -> None:
        self.source = source
        self.name = name
        self.channel = channel
        self.cc = cc

class FileReader:
    def __init__(self, filePath) -> None:
        self.filePath = filePath
        self.messages = []
    def __str__(self) -> str:
        strang = ''
        for message in self.messages:
            strang += f"{message.source}\t{message.name}\t{message.channel}\t{message.cc}{linesep}"
        return strang

class TouchOSCReader(FileReader):
    def __init__(self, filePath) -> None:
        super().__init__(filePath)

    def extract_node_data(self, node):
        name = node.xpath('properties/property[contains(key/text(),"name")]/value/text()')[0].strip()
        midi_message = node.find('messages/midi/message')
        # Channels are recorded as 0 base, but UI is 1 base
        midi_message_channel = int(midi_message.find('channel').text) + 1
        # Data1 is 1 base both in XML and in UI
        midi_message_cc = midi_message.find('data1').text
        return MIDICCMessage(
            source = 'TouchOSC',
            name = name,
            channel = midi_message_channel,
            cc = midi_message_cc
        )

    def read(self):
        # Get nodes with enabled MIDI messages
        nodes_sending_midi = etree.parse(self.filePath).xpath('//node[messages/midi/enabled="1"]')
        for node in nodes_sending_midi:
            nodeData = self.extract_node_data(node)
            self.messages.append(nodeData)

class AbletonReader(FileReader):
    def __init__(self, filePath) -> None:
        super().__init__(filePath)
    
    def extract_tree(self):
        with gzip.open(self.filePath) as f:
            xml = f.read()
        return etree.fromstring(xml)

    def extract_node_data(self, node):
        name = None
        channel = None
        # TODO Get name from somewhere... Might not actually be possible
        for property in node.iterchildren():
            if property.tag == 'Channel':
                channel = property.xpath('@Value')[0]
            elif property.tag == 'NoteOrController':
                cc = property.xpath('@Value')[0]
        
        return MIDICCMessage(
            source = 'Ableton',
            name = None,
            channel = channel,
            cc = cc
        )

    def read(self):
        tree = self.extract_tree()
        nodes = tree.xpath('//KeyMidi[IsNote/@Value="false" and Channel/@Value>0 and NoteOrController/@Value>0]')
        for node in nodes:
            nodeData = self.extract_node_data(node)
            self.messages.append(nodeData)
            
    
files = [
    TouchOSCReader(latest_file_of_type_in_dir('/Users/jonnie/My Drive/Documents/Music Production/Peripherals/TouchOSC','xml')),
    AbletonReader(latest_file_of_type_in_dir('/Users/jonnie/My Drive/Documents/Music Production/Ableton user library/Templates','als')),
]

for file in files:
    file.read()
    print(file)
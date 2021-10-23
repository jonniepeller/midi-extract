from os import listdir, linesep, path, remove
from lxml import etree
import shutil
from gzip import GzipFile

def latest_file_of_type_in_dir(directory, extension):
    files = [f for f in listdir(directory) if path.isfile(path.join(directory, f))]
    fileName = max(list(filter(lambda x: f'.{extension}' in x, files)))
    return path.join(directory, fileName)

class FileReader:
    def __init__(self, filePath) -> None:
        self.filePath = filePath
        self.namesAndCC = []
    def __str__(self) -> str:
        strang = ''
        if hasattr(self, 'filePath'):
            strang += linesep + self.filePath + linesep + linesep
        if hasattr(self, 'namesAndCC'):
            for name_and_cc in self.namesAndCC:
                strang += f"{name_and_cc['name']}\t{name_and_cc['channel']}\t{name_and_cc['cc']}{linesep}"
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
        return {
            'name': name,
            'channel': midi_message_channel,
            'cc': midi_message_cc
        }

    def read(self):
        # Get nodes with enabled MIDI messages
        nodes_sending_midi = etree.parse(self.filePath).xpath('//node[messages/midi/enabled="1"]')
        for node in nodes_sending_midi:
            nodeData = self.extract_node_data(node)
            self.namesAndCC.append(nodeData)

class AbletonReader(FileReader):
    def __init__(self, filePath) -> None:
        super().__init__(filePath)
    
    def extract_xml(self):
        zipCopyName = f'{path.splitext(self.filePath)[0]} DELETE MEEEEEE.zip'
        try:
            shutil.copy(self.filePath, zipCopyName)
            with GzipFile(zipCopyName) as myzip:
                xml = myzip.read()
            remove(zipCopyName)
            return xml
        except:
            remove(zipCopyName)
            raise

    def read(self):
        xml = self.extract_xml()
        print(xml)
    
files = [
    TouchOSCReader(latest_file_of_type_in_dir('/Users/jonnie/My Drive/Documents/Music Production/Peripherals/TouchOSC','xml')),
    AbletonReader(latest_file_of_type_in_dir('/Users/jonnie/My Drive/Documents/Music Production/Ableton user library/Templates','als')),
]

for file in files:
    file.read()
    print(file)
from os import linesep
from lxml import etree
import gzip

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
    def xmlGetPath(self, node):
        pathString = ''
        if hasattr(node, 'tag'):
            # Try to get the user facing name if it has one, otherwise use the tag
            try:
                pathString += node.xpath('Name/EffectiveName/@Value')[0]
            except:
                pathString += node.tag
        if hasattr(node, 'getparent'):
            parent = self.xmlGetPath(node.getparent())
            if len(parent) > 0:
                pathString = parent + ' > ' + pathString
        return pathString

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
                # Channels are recorded as 0 base, but UI is 1 base
                channel = int(property.xpath('@Value')[0]) + 1
            elif property.tag == 'NoteOrController':
                cc = property.xpath('@Value')[0]
        
        path = self.xmlGetPath(node)
        return MIDICCMessage(
            source = 'Ableton',
            name = path,
            channel = channel,
            cc = cc
        )

    def read(self):
        tree = self.extract_tree()
        nodes = tree.xpath('//KeyMidi[IsNote/@Value="false" and NoteOrController/@Value>0]')
        for node in nodes:
            nodeData = self.extract_node_data(node)
            self.messages.append(nodeData)
            
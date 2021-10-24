from os import linesep
from lxml import etree
import gzip
import csv

class MIDICCMessage:
    def __init__(self, source, name, channel, cc) -> None:
        self.source = source
        self.name = name
        self.channel = channel
        self.cc = cc

    def toCsvRow(self):
        return [self.source, self.name, self.channel, self.cc]

def writeFileReadersToFile(fileReaders, filePath):
    with open(filePath, 'w') as f:
        writer = csv.writer(f)
        for fileReader in fileReaders:
            fileReader.writeToWriter(writer)

class FileReader:
    def __init__(self, filePath) -> None:
        self.filePath = filePath
        self.messages = []

    def __str__(self) -> str:
        strang = ''
        for message in self.messages:
            strang += f"{message.source}\t{message.name}\t{message.channel}\t{message.cc}{linesep}"
        return strang
        
    def writeToWriter(self, writer):
        writer.writerows([m.toCsvRow() for m in self.messages])

    def read(self):
        nodes = self.extractNodes()
        if nodes:
            for node in nodes:
                nodeData = self.extractDataFromNode(node)
                self.messages.append(nodeData)

class TouchOSCReader(FileReader):
    def __init__(self, filePath) -> None:
        super().__init__(filePath)

    def extractNodes(self):
        return etree.parse(self.filePath).xpath('//node[messages/midi/enabled="1"]')

    def extractDataFromNode(self, node):
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

class AbletonReader(FileReader):
    def __init__(self, filePath) -> None:
        super().__init__(filePath)
    
    def extractNodes(self):
        with gzip.open(self.filePath) as f:
            xml = f.read()
        tree = etree.fromstring(xml)
        nodes = tree.xpath('//KeyMidi[IsNote/@Value="false" and NoteOrController/@Value>0]')
        return nodes

    def getPath(self, node, stopBefore=None, ignoreList=[None]):
        # Try to get the user facing name if it has one, otherwise use the tag
        if hasattr(node, 'tag'):
            try:
                if 'MacroControls' in node.tag:
                    elementName = node.xpath('../MacroDisplayNames.0/@Value')[0]
                else:
                    elementName = node.xpath('Name/EffectiveName/@Value')[0]
            except:
                elementName = node.tag

        # If this element has been flagged to stop here, stop crawling up the tree
        if stopBefore is not None and stopBefore == elementName:
            return None

        # If this element has been flagged to ignore, ignore this one and continue up the tree
        elif elementName in ignoreList:
            elementName = None
        if hasattr(node, 'getparent'):
            parent = self.getPath(node.getparent(), stopBefore, ignoreList)
            if parent is not None:
                if elementName is not None:
                    return parent + ' > ' + elementName
                else:
                    return parent
            else:
                return elementName

    def extractDataFromNode(self, node):
        channel = None
        for property in node.iterchildren():
            if property.tag == 'Channel':
                # Channels are recorded as 0 base, but UI is 1 base
                channel = int(property.xpath('@Value')[0]) + 1
            elif property.tag == 'NoteOrController':
                cc = property.xpath('@Value')[0]
    
        path = self.getPath(node, 'LiveSet', [
            'KeyMidi',
            'Devices',
            'DeviceChain',
            'InstrumentGroupDevice',
            'Branches',
            'MidiToAudioDeviceChain',
            'AudioToAudioDeviceChain',
            'AudioEffectGroupDevice',
            'Chain'])
        return MIDICCMessage(
            source = 'Ableton',
            name = path,
            channel = channel,
            cc = cc
        )

class MIDIFighterTwisterReader(FileReader):
    # TODO: Implement this!
    def __init__(self, filePath) -> None:
        super().__init__(filePath)
    
    def extractNodes(self):
        pass

    def extractDataFromNode(self, node):
        pass


class S49Reader(FileReader):
    def __init__(self, filePath) -> None:
        super().__init__(filePath)
    
    def extractNodes(self):
        pass

    def extractDataFromNode(self, node):
        pass


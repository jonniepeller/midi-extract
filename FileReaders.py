from os import linesep, path
from lxml import etree
import gzip
import csv
import json

class MIDICCMessage:
    def __init__(self, function, source, name, channel, cc) -> None:
        self.function = function
        self.source=source
        self.name = name
        self.channel = channel
        self.cc = cc

    def toCsvRow(self):
        return [self.function, self.source, self.name, self.channel, self.cc]

def writeFileReadersToFile(fileReaders, filePath):
    with open(filePath, 'w') as f:
        writer = csv.writer(f)
        for fileReader in fileReaders:
            fileReader.writeToWriter(writer)

class FileReader:
    def __init__(self, filePath) -> None:
        self.filePath = filePath
        self.fileName = path.basename(self.filePath)
        self.messages = []

    def __str__(self) -> str:
        strang = ''
        for message in self.messages:
            strang += f"{message.source}\t{message.name}\t{message.channel}\t{message.cc}{linesep}"
        return strang
        
    def writeToWriter(self, writer):
        writer.writerows([m.toCsvRow() for m in self.messages])

    def jsonFind(self, path, json):
        for key in path.split('.'):
            if hasattr(json, 'keys') and key in json.keys():
                json = json[key]
            else:
                return None
        return json

    def readXML(self):
        nodes = self.extractNodes()
        if nodes:
            for node in nodes:
                nodeData = self.extractDataFromNode(node)
                self.messages.append(nodeData)
            
    def readJSON(self):
        nodes = self.extractDict()
        dataFromNodes = self.extractDataFromDict(nodes)

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
            function='Source',
            source=f'TouchOSC export, {self.fileName}',
            name = name,
            channel = midi_message_channel,
            cc = midi_message_cc
        )
    
    def read(self):
        self.readXML()

class AbletonReader(FileReader):
    def __init__(self, filePath) -> None:
        super().__init__(filePath)
    
    def extractNodes(self):
        with gzip.open(self.filePath) as f:
            xml = f.read()
        tree = etree.fromstring(xml)
        nodes = tree.xpath('//KeyMidi[IsNote/@Value="false" and Channel/@Value<=15 and NoteOrController/@Value>0]')
        return nodes

    def getPath(self, node, stopBefore=None, ignoreList=[None]):
        # Try to get the user facing name if it has one, otherwise use the tag
        if hasattr(node, 'tag'):
            try:
                if 'MacroControls' in node.tag:
                    macroNumber = node.tag.split('.')[1]
                    elementName = node.xpath(f'../MacroDisplayNames.{macroNumber}/@Value')[0]
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
            function='Destination',
            source=f'Ableton file, {self.fileName}',
            name = path,
            channel = channel,
            cc = cc
        )
    
    def read(self):
        self.readXML()

class S49Reader(FileReader):
    def __init__(self, filePath) -> None:
        super().__init__(filePath)

    def extractDict(self):
        with open(self.filePath, 'r') as f:
            return json.loads(f.read())

    def extractDataFromDict(self, dict):
        if hasattr(dict, 'keys'):
            for key in dict.keys():
                childDict = dict[key]
                if hasattr(childDict, 'keys'):
                    if 'MIDIId' in childDict.keys() and childDict.get('MIDIType') == '3':
                        # Get name if there is one, otherwise use the key
                        name = childDict.get('Name')
                        if name is None:
                            name = key
                        msg = MIDICCMessage(
                            function='Source',
                            source=f'Komplete Kontrol settings file, {self.fileName}',
                            name = name,
                            # Channels are recorded as 0 base, but UI is 1 base
                            channel = int(childDict.get('Channel')) + 1,
                            cc = childDict.get('MIDIId')
                        )
                        self.messages.append(msg)
                    else:
                        self.extractDataFromDict(childDict)
    
    def read(self):
        self.readJSON()

class UAMIDIControlReader(FileReader):
    def __init__(self, filePath) -> None:
        super().__init__(filePath)

    def extractDict(self):
        with open(self.filePath, 'r') as f:
            return json.loads(f.read())

    def extractDataFromDict(self, dict):
        if hasattr(dict, 'keys'):
            for key in dict.keys():
                childDict = dict[key]
                if hasattr(childDict, 'keys'):
                    printStr = self.jsonFind('midiMessage.printStr', childDict)
                    originDeviceName = self.jsonFind('midiMessage.midiDeviceInfo.name', childDict)
                    # If it has path to message, and that type is CC, then we want this one. Otherwise keep digging.
                    if printStr is not None and 'CC' in printStr:
                        msg = MIDICCMessage(
                            function='Destination',
                            source=f'UADMIDIControl file, {self.fileName}',
                            name = f'{originDeviceName} to {key}',
                            channel = int(printStr.split(' ')[0]),
                            cc = self.jsonFind('midiMessage.nr', childDict)
                        )
                        self.messages.append(msg)
                    else:
                        self.extractDataFromDict(childDict)
    
    def read(self):
        self.readJSON()

class MIDIFighterTwisterReader(FileReader):
    # TODO: Implement this!
    def __init__(self, filePath) -> None:
        super().__init__(filePath)
    
    def extractNodes(self):
        pass

    def extractDataFromNode(self, node):
        pass
    
    def read(self):
        self.readXML()

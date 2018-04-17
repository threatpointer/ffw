#!/usr/bin/env python2

import os
import logging
import pickle
import pyinotify
import time
import random
import glob

from . import corpusfile


class CorpusIterator(object):
    """The iter() of CorpusManager class."""

    def __init__(self, corpuses):
        self.corpuses = corpuses
        self.current = 0

    def __iter__(self):
        return self

    def next(self):
        if self.current >= len(self.corpuses):
            raise StopIteration
        else:
            self.current += 1
            return self.corpuses[self.current - 1].getData()


class CorpusManager(object):
    """
    Manage the corpus files for the fuzzer.
    """

    def __init__(self, config):
        self.corpus = []  # type: Array[CorpusFile]
        self.config = config
        self.fileWatcher = FileWatcher(config, self)


    def __iter__(self):
        return CorpusIterator(self.corpus)


    def getRandomCorpus(self):
        c = random.randint(0, len(self.corpus) - 1)
        return self.corpus[c]


    def addNewCorpus(self, data, seed):
        """Add new corpus file (identified by fuzzer."""
        logging.info("CorpusManager: addNewCorpus: " + str(seed))

        # add as file
        filename = self.config["inputs"] + "/" + str(seed) + ".corpus"
        with open(filename, 'wb') as f:
            pickle.dump(data, f)

        # add locally
        corpusFile = corpusfile.CorpusFile(filename, data)
        self.corpus.append(corpusFile)


    def getCorpusCount(self):
        return len(self.corpus)


    def initialLoad(self):
        """
        Load initial recorded pickle files.

        Load the initial recorded data files, plus the added corpus
        files.
        """
        inputFiles = glob.glob(os.path.join(self.config["inputs"], '*'))

        for inputFile in inputFiles:
            self.loadFile(inputFile, False)


    def loadFile(self, fileName, isExternal):
        logging.debug("Load Corpus file: " + fileName)
        if not os.path.isfile(fileName):
            logging.error("Could not read input file: " + fileName)
            return False

        if self._findCorpusByFilename(fileName):
            # the new corpus is generated by us - ignore it
            logging.debug("Corpus added by us, ignore: " + fileName)
            return

        logging.info("Load external corpus: " + fileName)
        try:
            with open(fileName, 'rb') as f:
                data = pickle.load(f)

            # we'll have to send this new corpus once, but ignore
            # resulting "New!" from fuzzer. therefore processed=False
            corpusFile = corpusfile.CorpusFile(fileName, data, processed=False, isExternal=True)
            self.corpus.append(corpusFile)

        except Exception as e:
            #logging.error("E: " + str(e))
            pass


    def hasNewExternalCorpus(self):
        for corpus in self.corpus:
            if not corpus.isProcessed():
                return True

        return False


    def getNewExternalCorpus(self):
        for corpus in self.corpus:
            if not corpus.isProcessed():
                return corpus

        return None


    def _findCorpusByFilename(self, filename):
        # filename is like "/bla/in/1234.corpus"
        #seed = os.path.basename(filename).partition(".")[0]
        for corpus in self.corpus:
            if corpus.filename == filename:
                return True

        return False


    def startWatch(self):
        self.fileWatcher.start()


    def checkForNewFiles(self):
        self.fileWatcher.checkForEvents()


    def newFileHandler(self, filename):
        self.loadFile(filename, True)


    def printStats(self):
        for idx, corpus in enumerate(self.corpus):
            print "  Corpus %d: Children: %d  Crashes: %d" % ( idx, corpus.stats["new"], corpus.stats["crashes"])


class FileWatcher(object):
    """
    Abstract pyinotify away.

    Watches directory, will call corpusManager.newFileHandler() if any new.
    """

    def __init__(self, config, corpusManager):
        self.wm = pyinotify.WatchManager()
        self.mask = pyinotify.IN_CREATE
        self.handler = FileWatcherEventHandler(corpusManager)
        self.wdd = None
        self.config = config


    def start(self):
        watchPath = self.config["inputs"]
        self.notifier = pyinotify.Notifier(self.wm, self.handler, timeout=10)
        self.wdd = self.wm.add_watch(watchPath, self.mask, rec=False)


    def checkForEvents(self):
        self.notifier.process_events()
        while self.notifier.check_events():
            self.notifier.read_events()
            self.notifier.process_events()


class FileWatcherEventHandler(pyinotify.ProcessEvent):
    """
    File handler for pyinotify.

    Calls corpusManager.newFileHandler() if new file appears.
    """

    def __init__(self, corpusManager):
        self.corpusManager = corpusManager


    def process_IN_CREATE(self, event):
        self.corpusManager.newFileHandler(event.pathname)


if __name__ == "__main__":
    corpusManager = CorpusManager()
    corpusManager.start()
    while True:
        time.sleep(1)
        corpusManager.checkForNewFiles()

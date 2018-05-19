#!/usr/bin/env python

import unittest
import os

from common.corpusdata import CorpusData
from common.networkdata import NetworkData
from mutator.mutatorinterface import MutatorInterface, testMutatorConfig
import testutils

from mutator.mutator_dictionary import MutatorDictionary


class DictionaryFuzzerTest(unittest.TestCase):
    def _getConfig(self):
        config = {
            "input_dir": "/tmp/ffw-test/in",
            "temp_dir": "/tmp/ffw-test/temp",
            "basedir": os.path.dirname(os.path.realpath(__file__)) + "/..",
            "processes": 1,
        }

        return config


    def _getNetworkData(self, config):
        networkMessages = [
            {
                'data': 'msg 1 cli test1',
                'from': 'cli',
                'index': 0,
            },
            {
                'data': 'msg 1 cli test1 test2 test2',
                'from': 'cli',
                'index': 1,
            },
        ]

        networkData = NetworkData(config,
                                  networkMessages)
        return networkData


    def _getCorpusData(self, config):
        networkData = self._getNetworkData(config)
        corpusData = CorpusData(config, 'data0', networkData)
        return corpusData


    def test_dictionaryfuzzer(self):
        config = self._getConfig()
        config['mutator'] = 'Dictionary'
        self.assertTrue(testMutatorConfig(config, 'basic'))
        mutatorInterface = MutatorInterface(config, 0)

        corpusData = self._getCorpusData(config)

        fuzzedCorpusData1 = mutatorInterface.fuzz(corpusData)
        fuzzedCorpusData2 = mutatorInterface.fuzz(corpusData)
        fuzzedCorpusData3 = mutatorInterface.fuzz(corpusData)
        fuzzedCorpusData4 = mutatorInterface.fuzz(corpusData)
        fuzzedCorpusData5 = mutatorInterface.fuzz(corpusData)

        #print("1: " + fuzzedCorpusData1.networkData.messages[0]['data'])
        self.assertEqual(
            fuzzedCorpusData1.networkData.messages[0]['data'],
            'msg 1 cli test2'
        )
        self.assertIsNotNone(
            fuzzedCorpusData1.networkData.fuzzMsgIdx
        )
        self.assertIsNotNone(
            fuzzedCorpusData1.networkData.fuzzMsgChoice
        )
        self.assertEqual(
            fuzzedCorpusData2.networkData.messages[1]['data'],
            'msg 1 cli test2 test2 test2'
        )
        self.assertEqual(
            fuzzedCorpusData3.networkData.messages[1]['data'],
            'msg 1 cli test1 test1 test2'
        )
        self.assertEqual(
            fuzzedCorpusData4.networkData.messages[1]['data'],
            'msg 1 cli test1 test2 test1'
        )
        self.assertTrue(
            fuzzedCorpusData5 == None
        )


if __name__ == '__main__':
    unittest.main()

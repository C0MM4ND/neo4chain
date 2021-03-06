# MIT License
#
# Copyright (c) 2018 Evgeny Medvedev, evge.medvedev@gmail.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from hexbytes.main import HexBytes
from ethereumetl.utils import chunk_string, hex_to_dec, to_normalized_address
from builtins import map
import logging


# https://ethereum.stackexchange.com/questions/12553/understanding-logs-and-log-blooms
TRANSFER_EVENT_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
logger = logging.getLogger(__name__)

class EthTokenTransfer(object):
    def __init__(self):
        self.token_address = None
        self.from_address = None
        self.to_address = None
        self.value = None
        self.transaction_hash = None
        self.log_index = None
        self.block_number = None
        self.value_raw = None

class EthTokenTransferExtractor(object):
    def extract_transfer_from_log(self, receipt_log):
        topics = receipt_log.get('topics')
        if topics is None or len(topics) < 1:
            # This is normal, topics can be empty for anonymous events
            return None

        # fix datatype of HexBytes
        if type(topics[0]) is str and topics[0] == TRANSFER_EVENT_TOPIC:
            return self._parse_transfer(topics, receipt_log)
        elif type(topics[0]) is HexBytes:
            return self._parse_transfer(topics, receipt_log)
        return None

    def _parse_transfer(self, topics, receipt_log):
        # Handle unindexed event fields
        topics_with_data = topics + split_to_words(receipt_log.data)

        transaction_hash = receipt_log.get(
            'transaction_hash', receipt_log.get('transactionHash'))
        if type(transaction_hash) is HexBytes:
            transaction_hash = transaction_hash.hex()
        log_index = receipt_log.get('log_index', receipt_log.get('logIndex'))

        # if the number of topics and fields in data part != 4, then it's a weird event
        if len(topics_with_data) != 4:
            # logger.warning("The number of topics and data parts is not equal to 4 in log {} of transaction {}"
            #                .format(log_index, transaction_hash))
            return None

        token_transfer = EthTokenTransfer()
        token_transfer.token_address = to_normalized_address(
            receipt_log.address)
        token_transfer.from_address = word_to_address(topics_with_data[1])
        token_transfer.to_address = word_to_address(topics_with_data[2])
        token_transfer.value_raw = topics_with_data[3]
        try: 
            token_transfer.value = hex_to_dec(topics_with_data[3])
        except ValueError:
            logger.info(f'{topics_with_data[3]} is not a hex-encoded dec value')
            logger.info('so this event is not a transfer')
            return None
        # fix data read on web3 AttributeDict
        token_transfer.transaction_hash = transaction_hash
        token_transfer.log_index = log_index
        token_transfer.block_number = receipt_log.get(
            'block_number', receipt_log.get('blockNumber'))
        return token_transfer


def split_to_words(data):
    if data and len(data) > 2:
        data_without_0x = data[2:]
        words = list(chunk_string(data_without_0x, 64))
        words_with_0x = list(map(lambda word: '0x' + word, words))
        return words_with_0x
    return []


def word_to_address(param):
    if param is None:
        return None
    if type(param) is HexBytes:
        param = param.hex()

    if len(param) >= 40:
        return to_normalized_address('0x' + param[-40:])
    else:
        return to_normalized_address(param)

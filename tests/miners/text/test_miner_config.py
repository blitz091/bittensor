import os, sys
from unittest.mock import MagicMock
import unittest.mock as mock
import bittensor
import torch
import numpy
import pathlib

from miners.text.template_miner import Miner

def test_run_template_config():

    magic = MagicMock(return_value = 1)
    def test_forward(cls,inputs_x):
        return magic(inputs_x)

    # mimic the get block function
    class block():
        def __init__(self):
            self.i = 0
        def blocks(self):
            self.i += 1
            return self.i

    block_check = block()

    PATH = '/tests/miners/text/test_config.yml'
    sys.argv = [sys.argv[0], '--config', PATH]
    config = Miner.config()
    assert config['miner']['n_epochs'] == 1
    assert config['miner']['epoch_length'] == 1

    config.wallet.path = '/tmp/pytest'
    config.wallet.name = 'pytest'
    config.wallet.hotkey = 'pytest'
    wallet = bittensor.wallet(
        path = '/tmp/pytest',
        name = 'pytest',
        hotkey = 'pytest',
    )
    with mock.patch.object(Miner,'forward_text',new=test_forward):
        miner = Miner( config = config )
        with mock.patch.object(miner.neuron.subtensor, 'get_current_block', new=block_check.blocks):

            miner = Miner( config = config )
            miner.neuron.wallet = wallet.create(coldkey_use_password = False)

            bittensor.neuron.subtensor.connect = MagicMock(return_value = True)  
            bittensor.neuron.subtensor.is_connected = MagicMock(return_value = True)
            bittensor.neuron.subtensor.subscribe = MagicMock(return_value = True)  
            
            miner.run()

            assert magic.call_count == 1
            assert torch.is_tensor(magic.call_args[0][0])

if __name__ == "__main__":
    test_run_template_config()
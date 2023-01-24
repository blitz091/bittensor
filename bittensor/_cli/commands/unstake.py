# The MIT License (MIT)
# Copyright © 2021 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, 
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of 
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL 
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION 
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.

import sys
import bittensor
from tqdm import tqdm
from rich.prompt import Confirm, Prompt
from bittensor.utils.balance import Balance
from typing import List, Union, Optional, Dict, Tuple
from .utils import get_hotkey_wallets_for_wallet
console = bittensor.__console__

class UnStakeCommand:

    @classmethod   
    def check_config( cls, config: 'bittensor.Config' ):
        if config.subtensor.get('network') == bittensor.defaults.subtensor.network and not config.no_prompt:
            config.subtensor.network = Prompt.ask("Enter subtensor network", choices=bittensor.__networks__, default = bittensor.defaults.subtensor.network)
        
        if config.wallet.get('name') == bittensor.defaults.wallet.name and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default = bittensor.defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if config.wallet.get('hotkey') == bittensor.defaults.wallet.hotkey and not config.no_prompt and not config.wallet.get('all_hotkeys') and not config.wallet.get('hotkeys'):
            hotkey = Prompt.ask("Enter hotkey name", default = bittensor.defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)
                    
        # Get amount.
        if not config.get('amount') and not config.get('unstake_all') and not config.get('max_stake'):
            hotkeys: str = ''
            if config.wallet.get('all_hotkeys'):
                hotkeys = "all hotkeys"
            elif config.wallet.get('hotkeys'):
                hotkeys = str(config.wallet.hotkeys).replace('[', '').replace(']', '')
            else:
                hotkeys = str(config.wallet.hotkey)
            if not Confirm.ask("Unstake all Tao from: [bold]'{}'[/bold]?".format(hotkeys)):
                amount = Prompt.ask("Enter Tao amount to unstake")
                config.unstake_all = False
                try:
                    config.amount = float(amount)
                except ValueError:
                    console.print(":cross_mark:[red] Invalid Tao amount[/red] [bold white]{}[/bold white]".format(amount))
                    sys.exit()
            else:
                config.unstake_all = True

    @staticmethod
    def add_args( command_parser ):
        unstake_parser = command_parser.add_parser(
            'unstake', 
            help='''Unstake from hotkey accounts.'''
        )
        unstake_parser.add_argument( 
            '--no_version_checking', 
            action='store_true', 
            help='''Set false to stop cli version checking''', 
            default = False 
        )
        unstake_parser.add_argument(
            '--all', 
            dest="unstake_all", 
            action='store_true',
            default=False,
        )
        unstake_parser.add_argument(
            '--amount', 
            dest="amount", 
            type=float, 
            required=False
        )
        unstake_parser.add_argument(
            '--max_stake', 
            dest="max_stake",
            type=float,
            required=False,
            action='store',
            default=None,
            help='''Specify the maximum amount of Tao to have staked in each hotkey.'''
        )
        unstake_parser.add_argument(
            '--no_prompt', 
            dest='no_prompt', 
            action='store_true', 
            help='''Set true to avoid prompting the user.''',
            default=False,
        )
        bittensor.wallet.add_args( unstake_parser )
        bittensor.subtensor.add_args( unstake_parser )

    @staticmethod
    def run( cli ):
        r""" Unstake token of amount from hotkey(s).
        """        
        config = cli.config.copy()
        wallet = bittensor.wallet( config = config )
        subtensor: bittensor.Subtensor = bittensor.subtensor( config = cli.config )
        
        # Get the hotkey_names (if any) and the hotkey_ss58s.
        hotkeys_to_unstake_from: List[Tuple[Optional[str], str]] = []
        if cli.config.wallet.get('all_hotkeys'):
            # Stake to all hotkeys.
            all_hotkeys: List[bittensor.wallet] = get_hotkey_wallets_for_wallet( wallet = wallet )
            # Exclude hotkeys that are specified.
            hotkeys_to_unstake_from = [
                (wallet.hotkey_str, wallet.hotkey.ss58_address) for wallet in all_hotkeys if wallet.hotkey_str not in cli.config.wallet.get('hotkeys', [])
            ] # definitely wallets

        elif cli.config.wallet.get('hotkeys'):
            # Stake to specific hotkeys.
            for hotkey_ss58_or_hotkey_name in cli.config.wallet.get('hotkeys'):
                if bittensor.utils.is_valid_ss58_address( hotkey_ss58_or_hotkey_name ):
                    # If the hotkey is a valid ss58 address, we add it to the list.
                    hotkeys_to_unstake_from.append( (None, hotkey_ss58_or_hotkey_name ) )
                else:
                    # If the hotkey is not a valid ss58 address, we assume it is a hotkey name.
                    #  We then get the hotkey from the wallet and add it to the list.
                    wallet_ = bittensor.wallet( config = cli.config, hotkey = hotkey_ss58_or_hotkey_name )
                    hotkeys_to_unstake_from.append( (wallet_.hotkey_str, wallet_.hotkey.ss58_address ) )
        elif cli.config.wallet.get('hotkey'):
            # Only cli.config.wallet.hotkey is specified.
            #  so we stake to that single hotkey.
            hotkey_ss58_or_name = cli.config.wallet.get('hotkey')
            if bittensor.utils.is_valid_ss58_address( hotkey_ss58_or_name ):
                hotkeys_to_unstake_from = [ (None, hotkey_ss58_or_name) ]
            else:
                # Hotkey is not a valid ss58 address, so we assume it is a hotkey name.
                wallet_ = bittensor.wallet( config = cli.config, hotkey = hotkey_ss58_or_name )
                hotkeys_to_unstake_from = [ (wallet_.hotkey_str, wallet_.hotkey.ss58_address ) ]
        else:
            # Only cli.config.wallet.hotkey is specified.
            #  so we stake to that single hotkey.
            assert cli.config.wallet.hotkey is not None
            hotkeys_to_unstake_from = [ (None, bittensor.wallet( config = cli.config ).hotkey.ss58_address) ]
        
        final_hotkeys: List[Tuple[str, str]] = [] 
        final_amounts: List[Union[float, Balance]] = []
        for hotkey in tqdm(hotkeys_to_unstake_from):
            hotkey: Tuple[Optional[str], str] # (hotkey_name (or None), hotkey_ss58)
            if not subtensor.is_hotkey_registered_any( hotkey_ss58 = hotkey ):
                # Hotkey is not registered.
                if (len(hotkeys_to_unstake_from) == 1):
                    # Only one hotkey, error
                    bittensor.__console__.print(f"[red]Hotkey [bold]{hotkey}[/bold] is not registered. Aborting.[/red]")
                    return None
                else:
                    # Otherwise, print warning and skip
                    bittensor.__console__.print(f"[yellow]Hotkey [bold]{hotkey}[/bold] is not registered. Skipping.[/yellow]")
                    continue
        
            unstake_amount_tao: float = cli.config.get('amount') # The amount specified to unstake.
            hotkey_stake: Balance = subtensor.get_stake_for_coldkey_and_hotkey( hotkey_ss58 = hotkey[1], coldkey_ss58 = wallet.coldkey.ss58_address )
            if unstake_amount_tao == None:
                unstake_amount_tao = hotkey_stake.tao
            if cli.config.get('max_stake'):
                # Get the current stake of the hotkey from this coldkey.
                unstake_amount_tao: float = hotkey_stake.tao - cli.config.get('max_stake')   
                cli.config.amount = unstake_amount_tao  
                if unstake_amount_tao < 0:
                    # Skip if max_stake is greater than current stake.
                    continue
            else:
                if unstake_amount_tao is not None:
                    # There is a specified amount to unstake.
                    if unstake_amount_tao > hotkey_stake.tao:
                        # Skip if the specified amount is greater than the current stake.
                        continue
            
            final_amounts.append(unstake_amount_tao)
            final_hotkeys.append(hotkey) # add both the name and the ss58 address.

        if len(final_hotkeys) == 0:
            # No hotkeys to unstake from.
            bittensor.__console__.print("Not enough stake to unstake from any hotkeys or max_stake is more than current stake.")
            return None

        # Ask to unstake
        if not cli.config.no_prompt:
            if not Confirm.ask(f"Do you want to unstake from the following keys to {wallet.name}:\n" + \
                    "".join([
                        f"    [bold white]- {hotkey[0] + ':' if hotkey[0] else ''}{hotkey[1]}: {amount}𝜏[/bold white]\n" for hotkey, amount in zip(final_hotkeys, final_amounts)
                    ])
                ):
                return None
        
        if len(final_hotkeys) == 1:
            # do regular unstake
            return subtensor.unstake( 
                wallet=wallet, 
                hotkey_ss58 = final_hotkeys[0][1], 
                amount = None if cli.config.get('unstake_all') else final_amounts[0], 
                wait_for_inclusion = True, 
                prompt = not cli.config.no_prompt 
            )

        subtensor.unstake_multiple( wallet = wallet, hotkey_ss58s=[hotkey_ss58 for _, hotkey_ss58 in final_hotkeys], amounts =  None if cli.config.get('unstake_all') else final_amounts, wait_for_inclusion = True, prompt = False )

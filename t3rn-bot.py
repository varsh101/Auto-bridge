from web3 import Web3
from eth_account import Account
import time
import os
from data_bridge import data_bridge
from keys_and_addresses import private_keys, my_addresses, labels
from network_config import networks
import codecs

# Fungsi untuk memusatkan teks
def center_text(text):
    terminal_width = os.get_terminal_size().columns
    lines = text.splitlines()
    centered_lines = [line.center(terminal_width) for line in lines]
    return "\n".join(centered_lines)

# Fungsi untuk membersihkan terminal
def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

ascii_art = """

\033[38;5;214m

  T3RN  AUTO  BRIDGE  BOT
  =====================
  Optimized for OP-Base

\033[0m
"""

description = """
Automated Bridge Bot for https://bridge.t1rn.io/
"""

chain_symbols = {
    'OP Sepolia': '\033[91m',
    'Base Sepolia': '\033[96m'
}

green_color = '\033[92m'
reset_color = '\033[0m'
menu_color = '\033[95m'

explorer_urls = {
    'OP Sepolia': 'https://sepolia-optimism.etherscan.io/tx/',
    'Base Sepolia': 'https://sepolia.basescan.org/tx/',
    'BRN': 'https://brn.explorer.caldera.xyz/tx/'
}

def get_brn_balance(web3, my_address):
    balance = web3.eth.get_balance(my_address)
    return web3.from_wei(balance, 'ether')

def send_bridge_transaction(web3, account, my_address, data, network_name):
    nonce = web3.eth.get_transaction_count(my_address, 'pending')
    value_in_ether = 0.1
    value_in_wei = web3.to_wei(value_in_ether, 'ether')

    try:
        gas_estimate = web3.eth.estimate_gas({
            'to': networks[network_name]['contract_address'],
            'from': my_address,
            'data': data,
            'value': value_in_wei
        })
        gas_limit = gas_estimate + 1
    except Exception as e:
        print(f"\n{chain_symbols[network_name]}❌ Error estimating gas: {e}{reset_color}")
        return None

    base_fee = web3.eth.get_block('latest')['baseFeePerGas']
    priority_fee = web3.to_wei(1, 'gwei')  
    max_fee = base_fee + priority_fee

    transaction = {
        'nonce': nonce,
        'to': networks[network_name]['contract_address'],
        'value': value_in_wei,
        'gas': gas_limit * 2,
        'maxFeePerGas': max_fee,
        'maxPriorityFeePerGas': priority_fee,
        'chainId': networks[network_name]['chain_id'],
        'data': data
    }

    try:
        signed_txn = web3.eth.account.sign_transaction(transaction, account.key)
    except Exception as e:
        print(f"\n{chain_symbols[network_name]}❌ Error signing transaction: {e}{reset_color}")
        return None

    try:
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        balance = web3.eth.get_balance(my_address)
        formatted_balance = web3.from_wei(balance, 'ether')

        brn_web3 = Web3(Web3.HTTPProvider('https://brn.rpc.caldera.xyz/http'))
        brn_balance = get_brn_balance(brn_web3, my_address)

        explorer_link = f"{explorer_urls[network_name]}{web3.to_hex(tx_hash)}"

        print(f"\n{chain_symbols[network_name]}Transaction Details:")
        print(f"📍 From: {account.address}")
        print(f"💰 Amount Bridged: {value_in_ether} ETH")
        print(f"⛽ Gas Used: {tx_receipt['gasUsed']}")
        print(f"🔢 Block Number: {tx_receipt['blockNumber']}")
        print(f"💳 Remaining Balance: {formatted_balance:.6f} ETH")
        print(f"🪙 BRN Balance: {brn_balance:.6f} BRN")
        print(f"🔍 Explorer: {explorer_link}{reset_color}")

        return web3.to_hex(tx_hash), value_in_ether
    except Exception as e:
        print(f"\n{chain_symbols[network_name]}❌ Error sending transaction: {e}{reset_color}")
        return None, None

def process_network_transactions(network_name, bridges, chain_data, successful_txs, max_txs, current_tx, tx_pause):
    web3 = Web3(Web3.HTTPProvider(chain_data['rpc_url']))
    if not web3.is_connected():
        raise Exception(f"Cannot connect to network {network_name}")

    for tx_num in range(int(max_txs) if max_txs != 'infinite' else float('inf')):
        if max_txs != 'infinite' and current_tx >= int(max_txs):
            return successful_txs, current_tx
            
        for bridge in bridges:
            for i, private_key in enumerate(private_keys):
                account = Account.from_key(private_key)
                data = data_bridge[bridge]
                result = send_bridge_transaction(web3, account, my_addresses[i], data, network_name)
                if result:
                    tx_hash, value_sent = result
                    successful_txs += 1
                    current_tx += 1
                    if value_sent is not None:
                        print(f"\n{chain_symbols[network_name]}✅ Bridge #{successful_txs} | {labels[i]} | {bridge} | Amount: {value_sent:.5f} ETH | TX {current_tx}/{max_txs if max_txs != 'infinite' else '∞'}{reset_color}")
                    else:
                        print(f"\n{chain_symbols[network_name]}✅ Bridge #{successful_txs} | {labels[i]} | {bridge} | TX {current_tx}/{max_txs if max_txs != 'infinite' else '∞'}{reset_color}")
                    print(f"\n{'='*100}\n")
                
                if tx_num < int(max_txs)-1 if max_txs != 'infinite' else True:
                    print(f"\n⏳ Waiting {tx_pause} seconds before next transaction...")
                    time.sleep(tx_pause)

    return successful_txs, current_tx

def display_menu():
    print(f"{menu_color}Configure Bridge Parameters:{reset_color}")
    print("")
    
    while True:
        txs_per_chain = input("Number of transactions per chain (number or 'infinite'): ").strip()
        if txs_per_chain.lower() == 'infinite' or txs_per_chain.isdigit():
            break
        print("Please enter a number or 'infinite'")
    
    while True:
        try:
            tx_pause = int(input("Pause time between transactions (seconds): "))
            break
        except ValueError:
            print("Please enter a valid number")
    
    while True:
        try:
            chain_pause = int(input("Pause time between chain switches (seconds): "))
            break
        except ValueError:
            print("Please enter a valid number")
    
    while True:
        loops = input("Number of complete loops (number or 'infinite'): ").strip()
        if loops.lower() == 'infinite' or loops.isdigit():
            break
        print("Please enter a number or 'infinite'")
    
    return txs_per_chain, tx_pause, chain_pause, loops

def main():
    print("\033[92m" + center_text(ascii_art) + "\033[0m")
    print(center_text(description))
    print("\n\n")

    successful_txs = 0
    current_loop = 1

    while True:
        txs_per_chain, tx_pause, chain_pause, total_loops = display_menu()
        clear_terminal()
        print("\033[92m" + center_text(ascii_art) + "\033[0m")
        print(center_text(description))
        print("\n\n")

        try:
            while True:
                if total_loops != 'infinite' and current_loop > int(total_loops):
                    break
                    
                print(f"{menu_color}🔄 Loop {current_loop}" + (f"/{total_loops}" if total_loops != 'infinite' else '') + f"{reset_color}")
                
                # OP -> BASE
                print(f"\n{menu_color}🔄 Running OP -> BASE transactions...{reset_color}")
                current_tx = 0
                successful_txs, current_tx = process_network_transactions('OP Sepolia', ["OP - BASE"], networks['OP Sepolia'], successful_txs, txs_per_chain, current_tx, tx_pause)
                
                print(f"\n⏳ Waiting {chain_pause} seconds before switching chains...")
                time.sleep(chain_pause)
                
                # BASE -> OP
                print(f"\n{menu_color}🔄 Running BASE -> OP transactions...{reset_color}")
                current_tx = 0
                successful_txs, current_tx = process_network_transactions('Base Sepolia', ["BASE - OP"], networks['Base Sepolia'], successful_txs, txs_per_chain, current_tx, tx_pause)
                
                if total_loops == 'infinite' or current_loop < int(total_loops):
                    print(f"\n⏳ Waiting {chain_pause} seconds before next loop...")
                    time.sleep(chain_pause)
                
                current_loop += 1
                
            print(f"\n{green_color}✨ All loops completed! Total successful transactions: {successful_txs}{reset_color}")
            break
            
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(3)
            continue

if __name__ == "__main__":
    main()

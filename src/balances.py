from typing import Dict, DefaultDict, List, Optional, Tuple
import collections
import dataclasses
import hashlib

from cryptography.hazmat.primitives.asymmetric import ec

import blocks
import crypto
import transactions as transacts


Keychain = Dict[transacts.Hash, ec.EllipticCurvePublicKey]
Accounts = DefaultDict[transacts.Hash, List[transacts.Hash]]


@dataclasses.dataclass
class Balance:
    """ """

    latest_hash: transacts.Hash
    keychain: Optional[Keychain]
    accounts: Accounts


def update_accounts(accounts: Accounts, block: blocks.Block) -> Accounts:
    """ """
    for transaction in block.transactions:
        if transaction.sender != transacts.REWARD_SENDER:
            accounts[transaction.sender].remove(transaction.reference_hash)

        reference_hash = hashlib.sha256(transaction.encode()).digest()
        accounts[transaction.receiver].append(reference_hash)

    return accounts


def init_balance(
    blockchain: blocks.Blockchain, keychain: Optional[Keychain] = None
) -> Balance:
    """ """
    accounts: Accounts = collections.defaultdict(list)

    for block_hash in blockchain.chain:
        block = blockchain.blocks[block_hash]
        accounts = update_accounts(accounts, block)

    return Balance(latest_hash=block_hash, keychain=keychain, accounts=accounts)


def update_balance(balance: Balance, block: blocks.Block) -> Balance:
    """ """
    block_hash = hashlib.sha256(hashlib.sha256(block.header.encode()).digest()).digest()
    balance.latest_hash = block_hash

    balance.accounts = update_accounts(balance.accounts, block)

    return balance


def init_transfer(
    balance: Balance, sender: transacts.Hash, receiver: transacts.Hash, signature: bytes
) -> Tuple[Optional[Balance], Optional[transacts.Transaction]]:
    """ """
    if sender not in balance.accounts or len(balance.accounts[sender]) == 0:
        return None, None

    reference_hash = balance.accounts[sender].pop(0)
    transaction = transacts.Transaction(
        reference_hash=reference_hash,
        sender=sender,
        receiver=receiver,
        signature=signature,
    )

    return balance, transaction


def validate_transaction(balance: Balance, transaction: transacts.Transaction) -> bool:
    """ """
    sender = transaction.sender

    if sender == transacts.REWARD_SENDER:
        return transacts.validate_reward(transaction)

    if sender not in balance.accounts or len(balance.accounts[sender]) == 0:
        return False

    if balance.keychain is None or sender not in balance.keychain:
        return False

    is_not_spent = transaction.reference_hash in balance.accounts[transaction.sender]
    is_valid_signature = crypto.verify(
        transaction.signature,
        balance.keychain[sender],
        transaction.reference_hash + transaction.receiver,
    )

    return is_not_spent and is_valid_signature


def validate_block(
    block: blocks.Block,
    previous_hash: transacts.Hash,
    previous_timestamp: int,
    balance: Balance,
) -> Tuple[bool, Optional[transacts.Hash], Optional[int]]:
    """ """
    is_valid_header, current_hash, current_timestamp = blocks.validate_header(
        block.header, previous_hash, previous_timestamp
    )

    if not is_valid_header:
        return False, None, None

    for transaction in block.transactions:
        is_valid_transaction = validate_transaction(balance, transaction)

        if not is_valid_transaction:
            return False, None, None

    return True, current_hash, current_timestamp


def validate_blockchain(
    blockchain: blocks.Blockchain, balance: Balance
) -> Tuple[bool, Optional[Balance]]:
    """Check that all headers in the blockchain satisfy proof-of-work and indeed form a chain."""
    previous_hash = balance.latest_hash
    block_index = blockchain.chain.index(previous_hash)

    previous_block = blockchain.blocks[blockchain.chain[block_index - 1]]
    previous_timestamp = previous_block.header.timestamp

    for block_hash in blockchain.chain[block_index + 1 :]:
        block = blockchain.blocks[block_hash]
        is_valid_block, current_hash, current_timestamp = validate_block(
            block, previous_hash, previous_timestamp, balance
        )

        if not is_valid_block:
            return False, None

        assert current_hash is not None and current_timestamp is not None
        previous_hash = current_hash
        previous_timestamp = current_timestamp

        balance = update_balance(balance, block)

    return True, balance


def replace_blockchain(
    potential_blockchain: blocks.Blockchain,
    current_blockchain: blocks.Blockchain,
    current_balance: Balance,
) -> Tuple[bool, Optional[Balance]]:
    """Compare blockchains and replace if potential blockchain is longer and valid."""
    current_chain = current_blockchain.chain

    if len(potential_blockchain.chain) <= len(current_chain):
        return False, None

    for i, block_hash in enumerate(potential_blockchain.chain):
        if i == len(current_chain) or block_hash != current_chain[i]:
            break

    latest_index = current_chain.index(current_balance.latest_hash)

    if latest_index <= i:
        return validate_blockchain(potential_blockchain, current_balance)

    genesis_chain = current_blockchain.chain[:1]
    genesis_blockchain = blocks.Blockchain(
        chain=genesis_chain, blocks=current_blockchain.blocks
    )
    genesis_balance = init_balance(genesis_blockchain, current_balance.keychain)

    return validate_blockchain(potential_blockchain, genesis_balance)

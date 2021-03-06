from typing import Dict, Generator, List, Optional, Tuple
import dataclasses
import hashlib

import transactions as transacts


VERSION: int = 2

HEADER_SIZE: int = 101  # i.e. 1 + 32 + 32 + 4 + 32


@dataclasses.dataclass
class Header:
    """ """

    version: int
    previous_hash: transacts.Hash
    merkle_root: transacts.Hash
    timestamp: int
    nonce: int

    def encode(self):
        """ """
        return (
            self.version.to_bytes(1, byteorder="big")
            + self.previous_hash
            + self.merkle_root
            + self.timestamp.to_bytes(4, byteorder="big")
            + self.nonce.to_bytes(32, byteorder="big")
        )


def decode_header(header_bytes: bytes) -> Header:
    """ """
    version = header_bytes[0]
    previous_hash = header_bytes[1 : 1 + transacts.HASH_SIZE]
    merkle_root = header_bytes[1 + transacts.HASH_SIZE : 1 + 2 * transacts.HASH_SIZE]
    timestamp = int.from_bytes(
        header_bytes[1 + 2 * transacts.HASH_SIZE : 1 + 2 * transacts.HASH_SIZE + 4],
        byteorder="big",
    )
    nonce = int.from_bytes(
        header_bytes[1 + 2 * transacts.HASH_SIZE + 4 :], byteorder="big"
    )

    return Header(
        version=version,
        previous_hash=previous_hash,
        merkle_root=merkle_root,
        timestamp=timestamp,
        nonce=nonce,
    )


@dataclasses.dataclass
class Block:
    """ """

    header: Header
    transactions: List[transacts.Transaction]

    def encode(self):
        """ """
        header_bytes, transactions_bytes = self.header.encode(), b""

        for transaction in self.transactions:
            transactions_bytes += transaction.encode()

        transaction_counter_bytes = len(self.transactions).to_bytes(1, byteorder="big")

        block_size = (
            2
            + len(header_bytes)
            + len(transaction_counter_bytes)
            + len(transactions_bytes)
        )

        return (
            block_size.to_bytes(2, byteorder="big")
            + header_bytes
            + transaction_counter_bytes
            + transactions_bytes
        )


def decode_block(block_bytes: bytes) -> Block:
    """ """
    header_bytes = block_bytes[2 : 2 + HEADER_SIZE]
    transaction_counter = int.from_bytes(
        block_bytes[2 + HEADER_SIZE : 2 + HEADER_SIZE + 1], byteorder="big"
    )
    transactions_bytes = block_bytes[2 + HEADER_SIZE + 1 :]

    header = decode_header(header_bytes)
    transactions = transacts.decode_transactions(
        transaction_counter, transactions_bytes
    )

    return Block(header=header, transactions=transactions)


@dataclasses.dataclass
class Blockchain:
    """ """

    chain: List[transacts.Hash]
    blocks: Dict[transacts.Hash, Block]

    def encode(self):
        """ """
        blockchain_bytes = b""

        for block_hash in self.chain:
            blockchain_bytes += self.blocks[block_hash].encode()

        return blockchain_bytes


def iterate_blockchain(blockchain_bytes: bytes) -> Generator:
    """ """
    message_size = len(blockchain_bytes)
    byte_index = 0

    while True:
        if byte_index == message_size:
            break

        block_size = int.from_bytes(
            blockchain_bytes[byte_index : byte_index + 2], byteorder="big"
        )
        yield block_size, blockchain_bytes[byte_index : byte_index + block_size]

        byte_index += block_size

    yield None, None


def decode_blockchain(blockchain_bytes: bytes) -> Blockchain:
    """ """
    chain: List[transacts.Hash] = []
    blocks: Dict[transacts.Hash, Block] = {}

    for block_size, block_bytes in iterate_blockchain(blockchain_bytes):
        if block_size is None:
            break

        block = decode_block(block_bytes)
        header = block.header
        block_hash = hashlib.sha256(hashlib.sha256(header.encode()).digest()).digest()

        chain.append(block_hash)
        blocks[block_hash] = block

    return Blockchain(chain=chain, blocks=blocks)


def init_genesis_block(receiver: transacts.Hash) -> Block:
    """ """
    reward = transacts.init_reward(receiver)
    transaction_hash = hashlib.sha256(reward.encode()).digest()
    merkle_tree = transacts.init_merkle_tree([transaction_hash])

    assert merkle_tree is not None
    merkle_root = merkle_tree.tree_hash

    previous_hash = (0).to_bytes(transacts.HASH_SIZE, byteorder="big")
    header = Header(
        version=VERSION,
        previous_hash=previous_hash,
        merkle_root=merkle_root,
        timestamp=1634700000,
        nonce=48705,
    )

    guess = hashlib.sha256(hashlib.sha256(header.encode()).digest())
    assert guess.hexdigest()[:4] == "0000"

    return Block(header=header, transactions=[reward])


def init_blockchain(receiver: transacts.Hash) -> Blockchain:
    """ """
    genesis_block = init_genesis_block(receiver)

    header = genesis_block.header
    genesis_hash = hashlib.sha256(hashlib.sha256(header.encode()).digest()).digest()

    return Blockchain(chain=[genesis_hash], blocks={genesis_hash: genesis_block})


def run_proof_of_work(
    previous_hash: transacts.Hash,
    merkle_root: transacts.Hash,
    timestamp: int,
    nonce: int = 0,
    iterations: Optional[int] = None,
) -> Tuple[bool, int, Optional[transacts.Hash], Optional[Header]]:
    """Find nonce that makes the first 4 bytes of twice-hashed header all zeroes. Maximum number of
    iterations can be specified."""
    iteration_counter = 0

    while True:
        if iterations is not None and iteration_counter == iterations:
            return False, nonce, None, None

        header = Header(
            version=VERSION,
            previous_hash=previous_hash,
            merkle_root=merkle_root,
            timestamp=timestamp,
            nonce=nonce,
        )
        guess = hashlib.sha256(hashlib.sha256(header.encode()).digest())

        if guess.hexdigest()[:4] == "0000":
            break

        nonce += 1
        iteration_counter += 1

    return True, nonce, guess.digest(), header


def validate_header(
    header: Header, previous_hash: transacts.Hash, previous_timestamp: int
) -> Tuple[bool, Optional[transacts.Hash], Optional[int]]:
    """ """
    if header.previous_hash != previous_hash or header.timestamp < previous_timestamp:
        return False, None, None

    guess = hashlib.sha256(hashlib.sha256(header.encode()).digest())

    if guess.hexdigest()[:4] != "0000":
        return False, None, None

    return True, guess.digest(), header.timestamp

use sha2::{Digest, Sha256};
use std::convert::TryInto;
use std::time::Instant;

const VERSION: u8 = 0;

fn init_header(previous_hash: &[u8], timestamp: u32, nonce: u64) -> Vec<u8> {
    let timestamp_bytes: &[u8; 4] = &timestamp.to_be_bytes();
    let nonce_bytes: &[u8; 8] = &nonce.to_be_bytes();
    let padding: &[u8; 24] = &[0x00u8; 24];

    return [
        &[VERSION],
        previous_hash,
        timestamp_bytes,
        padding,
        nonce_bytes,
    ]
    .concat();
}

fn sha256_2x(bytes: &Vec<u8>) -> Vec<u8> {
    let mut intermediate;
    let mut hash = &bytes[..];

    for _ in 0..2 {
        intermediate = Sha256::digest(&hash);
        hash = &intermediate[..];
    }

    return hash.to_vec();
}

fn has_leading_zeroes(header: &Vec<u8>, difficulty: usize) -> (bool, Vec<u8>) {
    let hash = sha256_2x(header);

    for i in 0..difficulty {
        if hash[i] != 0 {
            return (false, hash);
        }
    }

    return (true, hash);
}

fn run_proof_of_work(previous_hash: &[u8], timestamp: u32) -> (u64, Vec<u8>, Vec<u8>) {
    let mut nonce: u64 = 0;
    let mut header: Vec<u8>;

    loop {
        header = init_header(previous_hash, timestamp, nonce);
        let (is_target_header, current_hash) = has_leading_zeroes(&header, 2);

        if is_target_header {
            return (nonce, current_hash, header);
        }

        nonce += 1;
    }
}

fn vec_to_array<T, const N: usize>(v: Vec<T>) -> [T; N] {
    v.try_into()
        .unwrap_or_else(|v: Vec<T>| panic!("Expected vector of length {}, got {}", N, v.len()))
}

fn main() {
    let mut previous_hash: [u8; 32] = [0x00u8; 32];
    let mut timestamp: u32 = 1634700000;

    let start = Instant::now();

    for i in 0..10 {
        let (nonce, current_hash, _) = run_proof_of_work(&previous_hash, timestamp);
        println!("Block {} with nonce of {}...", i, nonce);

        previous_hash = vec_to_array(current_hash);
        timestamp += 600;
    }

    let duration = start.elapsed();
    println!("Time elapsed: {:?}.", duration);
}

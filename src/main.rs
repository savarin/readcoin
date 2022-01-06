use std::time::Instant;

use readcoin::{block_number_to_nonce, run_proof_of_work, vec_to_array};

fn main() {
    let mut previous_hash: [u8; 32] = [0x00u8; 32];
    let mut timestamp: u32 = 1634700000;

    let mut start = Instant::now();

    for i in 0..3 {
        let (nonce, current_hash, _) = run_proof_of_work(&previous_hash, timestamp);
        println!("Block {} with nonce of {}...", i, nonce);

        previous_hash = vec_to_array(current_hash);
        timestamp += 600;
    }

    let mut duration = start.elapsed();
    println!("Time elapsed: {:?}.\n", duration);

    start = Instant::now();

    for i in 0..3 {
        let result = block_number_to_nonce(i);
        println!("Block {} with nonce of {}...", i, result);
    }

    duration = start.elapsed();
    println!("Time elapsed: {:?}.", duration);
}

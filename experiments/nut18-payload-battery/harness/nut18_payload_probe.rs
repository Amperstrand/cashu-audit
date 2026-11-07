use std::fs;

use cashu::nuts::PaymentRequestPayload;

/// Battery cell: NUT-18 payload parse (cdk column).
/// Same call as wallet/payment_request.rs:1839 (nostr receive) and cdk-ffi from_string.
/// Build: cargo build -p cashu --example nut18_payload_probe (debug, -j2 on constrained hosts)
fn main() {
    let mut fail = false;
    for path in std::env::args().skip(1) {
        let body = fs::read_to_string(&path).expect("read file");
        let name = path.rsplit('/').next().unwrap_or(&path);
        match serde_json::from_str::<PaymentRequestPayload>(&body) {
            Ok(p) => println!("{}\tPASS\tproofs={}", name, p.proofs.len()),
            Err(e) => {
                fail = true;
                println!("{}\tFAIL\t{}", name, e);
            }
        }
    }
    std::process::exit(if fail { 1 } else { 0 });
}

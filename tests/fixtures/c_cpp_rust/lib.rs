use std::io;

pub fn greet() -> io::Result<()> {
    println!("Hello from Rust");
    Ok(())
}

pub mod utils;

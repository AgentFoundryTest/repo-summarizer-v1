pub fn helper_function() {
    println!("Helper function");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_helper() {
        helper_function();
    }
}

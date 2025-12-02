import Foundation

struct User {
    let id: Int
    let username: String
    let email: String
}

class UserManager {
    private var users: [User] = []
    
    func addUser(_ user: User) {
        users.append(user)
    }
    
    func getUserById(_ id: Int) -> User? {
        return users.first { $0.id == id }
    }
}

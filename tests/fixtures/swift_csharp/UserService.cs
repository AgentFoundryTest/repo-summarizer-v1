using System;

namespace SampleApp.Services
{
    public interface IUserService
    {
        void CreateUser(string username);
        void DeleteUser(int userId);
    }

    public class UserService : IUserService
    {
        public void CreateUser(string username)
        {
            // FIXME: Add validation
            Console.WriteLine($"User created: {username}");
        }

        public void DeleteUser(int userId)
        {
            Console.WriteLine($"User deleted: {userId}");
        }
    }
}

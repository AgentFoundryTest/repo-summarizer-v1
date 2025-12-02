// Copyright (c) 2025 John Brosnihan
//
// This source code is licensed under the MIT license found in the
// LICENSE file in the root directory of this source tree.
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

// Copyright (c) 2025 John Brosnihan
//
// This source code is licensed under the MIT license found in the
// LICENSE file in the root directory of this source tree.
#include <vector>
#include <iostream>

class VectorOps {
public:
    void process() {
        std::vector<int> data = {1, 2, 3};
        // FIXME: Optimize this loop
        for (const auto& item : data) {
            std::cout << item << std::endl;
        }
    }
};

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

#include <cccr/rdf/load.hpp>

#include <iostream>

int main() {
  constexpr std::string_view kNtriples =
      "<http://example.org/s> <http://example.org/p> \"o\" .\n";
  auto result = cccr::rdf::LoadNTriples(kNtriples);
  if (!result) {
    std::cerr << "failed to load N-Triples\n";
    return 1;
  }
  std::cout << "cccr core linked\n";
  return 0;
}

#include <pybind11/pybind11.h>

#include "content_diff_native/diff_engine.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_native, module) {
  module.doc() = "Native diff engine for portfolio content bundles.";

  module.def(
      "compare_documents_json",
      [](const std::string& left_json, const std::string& right_json) {
        return content_diff_native::compare_documents_json(left_json, right_json).summary_json;
      },
      py::arg("left_json"),
      py::arg("right_json"));
}

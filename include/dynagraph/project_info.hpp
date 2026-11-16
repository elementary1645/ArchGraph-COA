#pragma once

#include <string_view>

namespace dynagraph {

// Build metadata for the imported graph engine.
[[nodiscard]] std::string_view version() noexcept;
[[nodiscard]] int openmp_spec_date() noexcept;

} // namespace dynagraph

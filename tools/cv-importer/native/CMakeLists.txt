cmake_minimum_required(VERSION 3.20)
project(portfolio_cv_importer_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(WIN32 AND NOT DEFINED ZLIB_ROOT)
  set(_portfolio_cv_importer_zlib_roots
    "C:/Apache24"
    "C:/Program Files/PostgreSQL/16"
    "C:/msys64/ucrt64"
    "C:/Program Files/JetBrains/CLion 2024.2.2/bin/mingw/x86_64-w64-mingw32"
  )

  foreach(_portfolio_cv_importer_zlib_root IN LISTS _portfolio_cv_importer_zlib_roots)
    if(EXISTS "${_portfolio_cv_importer_zlib_root}/include/zlib.h")
      set(ZLIB_ROOT "${_portfolio_cv_importer_zlib_root}" CACHE PATH "Detected ZLIB root for native PDF extractor")
      break()
    endif()
  endforeach()
endif()

find_package(ZLIB REQUIRED)

add_library(portfolio_cv_importer_native
  src/pdf_object_reader.cpp
  src/pdf_stream_decoder.cpp
  src/pdf_text_extractor.cpp
  src/resume_layout_parser.cpp
)

target_include_directories(
  portfolio_cv_importer_native
  PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(
  portfolio_cv_importer_native
  PUBLIC
    ZLIB::ZLIB
)

add_executable(portfolio_cv_pdf_extract src/main.cpp)
target_link_libraries(portfolio_cv_pdf_extract PRIVATE portfolio_cv_importer_native)

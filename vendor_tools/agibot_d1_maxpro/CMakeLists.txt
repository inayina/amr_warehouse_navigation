cmake_minimum_required(VERSION 3.16)
project(agibot_d1_maxpro_state_probe LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(
  AGIBOT_SDK_ROOT
  ""
  CACHE PATH
  "Path to the official x86/high_level_remote_client_209 SDK directory"
)

if(NOT AGIBOT_SDK_ROOT)
  message(FATAL_ERROR "Set -DAGIBOT_SDK_ROOT=/path/to/high_level_remote_client_209")
endif()

find_path(
  AGIBOT_SDK_INCLUDE_DIR
  NAMES high_level_base.h
  PATHS "${AGIBOT_SDK_ROOT}/include"
  NO_DEFAULT_PATH
  REQUIRED
)

find_library(
  AGIBOT_SDK_LIBRARY
  NAMES high_level_remote_tcp_client
  PATHS "${AGIBOT_SDK_ROOT}/build"
  NO_DEFAULT_PATH
  REQUIRED
)

find_package(OpenSSL REQUIRED COMPONENTS Crypto)

add_executable(agibot_d1_maxpro_state_probe state_probe.cpp)
target_include_directories(
  agibot_d1_maxpro_state_probe
  PRIVATE "${AGIBOT_SDK_INCLUDE_DIR}"
)
target_link_libraries(
  agibot_d1_maxpro_state_probe
  PRIVATE "${AGIBOT_SDK_LIBRARY}" OpenSSL::Crypto
)

get_filename_component(AGIBOT_SDK_LIBRARY_DIR "${AGIBOT_SDK_LIBRARY}" DIRECTORY)
set_target_properties(
  agibot_d1_maxpro_state_probe
  PROPERTIES BUILD_RPATH "${AGIBOT_SDK_LIBRARY_DIR}"
)

cmake_minimum_required(VERSION 3.25)

project(cccr_dist_smoke LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CCCR_SMOKE_LIBDIR)
  message(FATAL_ERROR "Set CCCR_SMOKE_LIBDIR to the release prefix lib directory")
endif()

find_package(CCCR CONFIG REQUIRED)

add_executable(cccr_dist_smoke smoke.cpp)
target_link_libraries(cccr_dist_smoke PRIVATE cccr::cccr)
set_target_properties(cccr_dist_smoke PROPERTIES
    BUILD_RPATH "${CCCR_SMOKE_LIBDIR}"
)
target_link_options(cccr_dist_smoke PRIVATE "LINKER:--disable-new-dtags")

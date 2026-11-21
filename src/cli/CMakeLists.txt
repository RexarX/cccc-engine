set(CCCR_CLI_HEADERS
    include/cccr/cli/cli.hpp
    include/cccr/cli/error.hpp
    include/cccr/cli/options.hpp
    include/cccr/cli/output.hpp
    include/cccr/cli/parse.hpp
    include/cccr/cli/run.hpp
)

set(CCCR_CLI_SOURCES
    src/parse.cpp
    src/output.cpp
    src/run.cpp
    src/main_lib.cpp
)

set(CCCR_CLI_ALL_FILES
    ${CCCR_CLI_HEADERS}
    ${CCCR_CLI_SOURCES}
)

# === Shared compiler settings ===
# Warnings and optimization flags are split into two separate INTERFACE
# libraries so each target can opt in independently.

set(MSVC_WARNINGS
    /W4              # High warning level
    /w14242          # Conversion warnings
    /w14254          # Operator conversion
    /w14263          # Member function doesn't override
    /w14265          # Virtual destructor warning
    /w14287          # Unsigned/negative constant mismatch
    /we4289          # Loop variable used outside scope
    /w14296          # Expression is always true/false
    /w14311          # Pointer truncation
    /w14545 /w14546 /w14547 /w14549 /w14555 # Suspicious operations
    /w14619          # Unknown warning number
    /w14640          # Thread-unsafe static initialization
    /w14826          # Wide character conversion
    /w14905 /w14906  # String literal casts
    /w14928          # Illegal copy initialization
)

set(CLANG_WARNINGS
    -Wall
    -Wextra
    -Wpedantic
    -Wshadow
    -Wnon-virtual-dtor
    -Wold-style-cast
    -Wcast-align
    -Wunused
    -Woverloaded-virtual
    -Wconversion
    -Wsign-conversion
    -Wnull-dereference
    -Wdouble-promotion
    -Wformat=2
    -Wimplicit-fallthrough
)

set(GCC_WARNINGS
    ${CLANG_WARNINGS}
    -Wmisleading-indentation
    -Wduplicated-cond
    -Wduplicated-branches
    -Wlogical-op
    -Wuseless-cast
)

if(CCCR_ENABLE_WARNINGS_AS_ERRORS)
  list(APPEND MSVC_WARNINGS /WX)
  list(APPEND CLANG_WARNINGS -Werror)
  list(APPEND GCC_WARNINGS -Werror)
endif()

add_library(cccr_cli_compiler_warnings INTERFACE)

target_compile_options(cccr_cli_compiler_warnings INTERFACE
    # MSVC and clang-cl (MSVC frontend) use MSVC-style warnings
    $<$<OR:$<CXX_COMPILER_ID:MSVC>,$<AND:$<CXX_COMPILER_ID:Clang>,$<PLATFORM_ID:Windows>>>:${MSVC_WARNINGS}>
    # Clang on Unix-like systems
    $<$<AND:$<CXX_COMPILER_ID:Clang>,$<NOT:$<PLATFORM_ID:Windows>>>:${CLANG_WARNINGS}>
    # GCC
    $<$<CXX_COMPILER_ID:GNU>:${GCC_WARNINGS}>
)

add_library(cccr_cli_compiler_optimizations INTERFACE)

set(_cccr_debug_rtc "$<$<CONFIG:Debug>:/RTC1>")
if(CCCR_ENABLE_SANITIZERS AND CCCR_SANITIZER_ADDRESS
    AND NOT CCCR_COMPILER_IS_CLANG_CL)
  set(_cccr_debug_rtc "")
endif()

target_compile_options(cccr_cli_compiler_optimizations INTERFACE
    # MSVC and clang-cl (MSVC frontend)
    $<$<OR:$<CXX_COMPILER_ID:MSVC>,$<AND:$<CXX_COMPILER_ID:Clang>,$<PLATFORM_ID:Windows>>>:
        /Zc:preprocessor
        /MP
        $<$<CONFIG:Debug>:/Od /Zi>
        ${_cccr_debug_rtc}
        $<$<CONFIG:RelWithDebInfo>:/O2 /Ob2 /Zi /Zo /DNDEBUG>
        $<$<CONFIG:Release>:/O2 /Ob2 /DNDEBUG>
    >
    # GCC and Clang on Unix-like systems
    $<$<AND:$<OR:$<CXX_COMPILER_ID:GNU>,$<CXX_COMPILER_ID:Clang>>,$<NOT:$<PLATFORM_ID:Windows>>>:
        $<$<CONFIG:Debug>:-Og -g3 -ggdb>
        $<$<CONFIG:RelWithDebInfo>:-O3 -g -fno-omit-frame-pointer -ffunction-sections -fdata-sections -fno-math-errno -DNDEBUG>
        $<$<CONFIG:Release>:-O3 -ffunction-sections -fdata-sections -fno-math-errno -DNDEBUG>
    >
    # Linux: split DWARF
    $<$<AND:$<PLATFORM_ID:Linux>,$<OR:$<CXX_COMPILER_ID:GNU>,$<CXX_COMPILER_ID:Clang>>>:
        $<$<CONFIG:Debug>:-gsplit-dwarf>
        $<$<CONFIG:RelWithDebInfo>:-gsplit-dwarf>
    >
    # Clang: profiling-quality debug info
    $<$<AND:$<CXX_COMPILER_ID:Clang>,$<NOT:$<PLATFORM_ID:Windows>>>:
        $<$<CONFIG:RelWithDebInfo>:-fdebug-info-for-profiling>
    >
)

target_link_options(cccr_cli_compiler_optimizations INTERFACE
    $<$<AND:$<OR:$<CXX_COMPILER_ID:GNU>,$<CXX_COMPILER_ID:Clang>>,$<NOT:$<PLATFORM_ID:Windows>>>:
        $<$<OR:$<CONFIG:Debug>,$<CONFIG:RelWithDebInfo>>:-rdynamic>
    >
    $<$<AND:$<PLATFORM_ID:Linux>,$<OR:$<CXX_COMPILER_ID:GNU>,$<CXX_COMPILER_ID:Clang>>>:
        $<$<CONFIG:RelWithDebInfo>:-Wl,--gc-sections>
    >
    $<$<AND:$<PLATFORM_ID:Darwin>,$<CXX_COMPILER_ID:Clang>>:
        $<$<CONFIG:RelWithDebInfo>:-Wl,-dead_strip>
    >
    $<$<OR:$<CXX_COMPILER_ID:MSVC>,$<AND:$<CXX_COMPILER_ID:Clang>,$<PLATFORM_ID:Windows>>>:
        $<$<CONFIG:Debug>:/INCREMENTAL>
        $<$<NOT:$<CONFIG:Debug>>:/INCREMENTAL:NO>
        $<$<CONFIG:RelWithDebInfo>:/OPT:REF /OPT:ICF>
    >
)

# === Creating static lib for testing ===

add_library(cccr_cli_lib STATIC ${CCCR_CLI_ALL_FILES})
add_library(cccr::cli::lib ALIAS cccr_cli_lib)

# PCH
target_precompile_headers(cccr_cli_lib PRIVATE
    $<$<COMPILE_LANGUAGE:CXX>:${CMAKE_CURRENT_SOURCE_DIR}/src/pch.hpp>
)

# C++ standart setup
set_target_properties(cccr_cli_lib PROPERTIES
    CXX_STANDARD 23
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)

# Output dir
set(_output_dir "${PROJECT_SOURCE_DIR}/bin/cli/$<LOWER_CASE:$<CONFIG>>-$<LOWER_CASE:${CMAKE_SYSTEM_NAME}>-$<LOWER_CASE:${CMAKE_SYSTEM_PROCESSOR}>")
set_target_properties(cccr_cli_lib PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${_output_dir}"
  LIBRARY_OUTPUT_DIRECTORY "${_output_dir}"
  ARCHIVE_OUTPUT_DIRECTORY "${_output_dir}"
)

# Folder setup
set_target_properties(cccr_cli_lib PROPERTIES FOLDER cli)

# Warnings + optimization flags (build-tree only; not part of install export)
target_link_libraries(cccr_cli_lib PRIVATE
    $<BUILD_INTERFACE:cccr_cli_compiler_warnings>
    $<BUILD_INTERFACE:cccr_cli_compiler_optimizations>
)

# LTO
if(CCCR_IPO_SUPPORTED)
  set_target_properties(cccr_cli_lib PROPERTIES
      INTERPROCEDURAL_OPTIMIZATION_RELWITHDEBINFO ON
      INTERPROCEDURAL_OPTIMIZATION_RELEASE ON
  )
endif()

# Sanitizer support
cccr_target_enable_sanitizers(cccr_cli_lib)

target_include_directories(cccr_cli_lib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(cccr_cli_lib
    PUBLIC
        cccr::core
    PRIVATE
        argparse::argparse
)

# === Creating executable ===

add_executable(cccr_cli src/main.cpp)

# C++ standart setup
set_target_properties(cccr_cli PROPERTIES
    CXX_STANDARD 23
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)

# Output dir
set(_output_dir "${PROJECT_SOURCE_DIR}/bin/cli/$<LOWER_CASE:$<CONFIG>>-$<LOWER_CASE:${CMAKE_SYSTEM_NAME}>-$<LOWER_CASE:${CMAKE_SYSTEM_PROCESSOR}>")
set_target_properties(cccr_cli PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${_output_dir}"
  LIBRARY_OUTPUT_DIRECTORY "${_output_dir}"
  ARCHIVE_OUTPUT_DIRECTORY "${_output_dir}"
)

# Folder setup
set_target_properties(cccr_cli PROPERTIES FOLDER cli)

# Warnings + optimization flags (build-tree only; not part of install export)
target_link_libraries(cccr_cli PRIVATE
    $<BUILD_INTERFACE:cccr_cli_compiler_warnings>
    $<BUILD_INTERFACE:cccr_cli_compiler_optimizations>
)

# LTO
if(CCCR_IPO_SUPPORTED)
  set_target_properties(cccr_cli PROPERTIES
      INTERPROCEDURAL_OPTIMIZATION_RELWITHDEBINFO ON
      INTERPROCEDURAL_OPTIMIZATION_RELEASE ON
  )
endif()

# Sanitizer support
cccr_target_enable_sanitizers(cccr_cli)

target_link_libraries(cccr_cli PRIVATE
    cccr::cli::lib
)

cccr_saxon_che_apply_build_rpath(cccr_cli)

if(CCCR_BUILD_TESTS)
  set(CCCR_CLI_TESTS
      tests/main.cpp
      tests/parse.cpp
      tests/run_smoke.cpp
  )

  add_executable(cccr_cli_tests ${CCCR_CLI_TESTS})

  # C++ standart setup
  set_target_properties(cccr_cli_tests PROPERTIES
      CXX_STANDARD 23
      CXX_STANDARD_REQUIRED ON
      CXX_EXTENSIONS OFF
  )

  # Output dir
  set(_output_dir "${PROJECT_SOURCE_DIR}/bin/tests/cli/$<LOWER_CASE:$<CONFIG>>-$<LOWER_CASE:${CMAKE_SYSTEM_NAME}>-$<LOWER_CASE:${CMAKE_SYSTEM_PROCESSOR}>")
  set_target_properties(cccr_cli_tests PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${_output_dir}"
    LIBRARY_OUTPUT_DIRECTORY "${_output_dir}"
    ARCHIVE_OUTPUT_DIRECTORY "${_output_dir}"
  )

  # Folder setup
  set_target_properties(cccr_cli_tests PROPERTIES FOLDER cli/tests)

  # Optimization flags only (no warnings for tests)
  target_link_libraries(cccr_cli_tests PRIVATE cccr_cli_compiler_optimizations)

  # LTO
  if(CCCR_IPO_SUPPORTED)
    set_target_properties(cccr_cli_tests PROPERTIES
        INTERPROCEDURAL_OPTIMIZATION_RELWITHDEBINFO ON
        INTERPROCEDURAL_OPTIMIZATION_RELEASE ON
    )
  endif()

  # Sanitizer support
  cccr_target_enable_sanitizers(cccr_cli_tests)

  target_compile_definitions(cccr_cli_tests PRIVATE
      CCCR_CLI_BASE_DATA_DIR="${PROJECT_SOURCE_DIR}/examples/data/base"
      CCCR_CLI_KUG_DATA_DIR="${PROJECT_SOURCE_DIR}/examples/data/kug"
  )

  target_link_libraries(cccr_cli_tests PRIVATE
      cccr::cli::lib
      doctest::doctest
  )

  # main.cpp defines DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN before the include,
  # so it cannot use a PCH that already included doctest.h.
  set_source_files_properties(tests/main.cpp PROPERTIES SKIP_PRECOMPILE_HEADERS ON)
  target_precompile_headers(cccr_cli_tests PRIVATE
      <doctest/doctest.h>
  )

  cccr_saxon_che_apply_build_rpath(cccr_cli_tests)

  add_test(NAME cccr_cli_tests COMMAND cccr_cli_tests)
  set_property(TEST cccr_cli_tests PROPERTY LABELS "unit" "cli")
endif()

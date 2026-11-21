set(CCCR_CORE_HEADERS
    include/cccr/utils/filesystem.hpp
    include/cccr/utils/macro.hpp
    include/cccr/assert.hpp
    include/cccr/compiler.hpp
    include/cccr/platform.hpp
    include/cccr/context.hpp
    include/cccr/log/level.hpp
    include/cccr/log/logging.hpp
    include/cccr/log/log.hpp
    include/cccr/ast/types.hpp
    include/cccr/ast/ast.hpp
    include/cccr/json/error.hpp
    include/cccr/json/load.hpp
    include/cccr/json/json.hpp
    include/cccr/xml/error.hpp
    include/cccr/xml/node.hpp
    include/cccr/xml/processor.hpp
    include/cccr/xml/xml.hpp
    include/cccr/xml/source.hpp
    include/cccr/csv/error.hpp
    include/cccr/csv/table.hpp
    include/cccr/csv/parse.hpp
    include/cccr/csv/project.hpp
    include/cccr/csv/source.hpp
    include/cccr/csv/csv.hpp
    include/cccr/input/error.hpp
    include/cccr/input/node.hpp
    include/cccr/input/query.hpp
    include/cccr/input/source.hpp
    include/cccr/input/input.hpp
    include/cccr/eval/error.hpp
    include/cccr/eval/qname.hpp
    include/cccr/eval/string.hpp
    include/cccr/eval/eval.hpp
    include/cccr/rdf/error.hpp
    include/cccr/rdf/term.hpp
    include/cccr/rdf/graph.hpp
    include/cccr/rdf/serialize.hpp
    include/cccr/rdf/syntax.hpp
    include/cccr/rdf/load.hpp
    include/cccr/rdf/ntriples.hpp
    include/cccr/rdf/rdf.hpp
    include/cccr/sparql/error.hpp
    include/cccr/sparql/substitute.hpp
    include/cccr/sparql/select.hpp
    include/cccr/sparql/results.hpp
    include/cccr/sparql/sparql.hpp
    include/cccr/engine/error.hpp
    include/cccr/engine/run.hpp
    include/cccr/engine/engine.hpp
    include/cccr/validate/error.hpp
    include/cccr/validate/literal.hpp
    include/cccr/validate/range.hpp
    include/cccr/validate/validate.hpp
)

set(CCCR_CORE_SOURCES
    src/assert.cpp
    src/json/load.cpp
    src/json/convert.cpp
    src/json/include_expand.cpp
    src/xml/node.cpp
    src/xml/processor.cpp
    src/csv/parse.cpp
    src/csv/project.cpp
    src/csv/source.cpp
    src/detail/redland_store.cpp
    src/detail/sparql_prepare.cpp
    src/rdf/graph.cpp
    src/rdf/serialize.cpp
    src/rdf/ntriples.cpp
    src/sparql/substitute.cpp
    src/sparql/select.cpp
    src/sparql/results.cpp
    src/eval/qname.cpp
    src/eval/string.cpp
    src/engine/run.cpp
    src/validate/literal.cpp
    src/validate/range.cpp
)

set(CCCR_CORE_ALL_FILES
    ${CCCR_CORE_HEADERS}
    ${CCCR_CORE_SOURCES}
)

# === Shared compiler settings ===
# Warnings and optimization flags are split into two separate INTERFACE
# libraries so each target can opt in independently (e.g. tests get
# optimizations but not warnings).

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

add_library(cccr_core_compiler_warnings INTERFACE)

target_compile_options(cccr_core_compiler_warnings INTERFACE
    # MSVC and clang-cl (MSVC frontend) use MSVC-style warnings
    $<$<OR:$<CXX_COMPILER_ID:MSVC>,$<AND:$<CXX_COMPILER_ID:Clang>,$<PLATFORM_ID:Windows>>>:${MSVC_WARNINGS}>
    # Clang on Unix-like systems
    $<$<AND:$<CXX_COMPILER_ID:Clang>,$<NOT:$<PLATFORM_ID:Windows>>>:${CLANG_WARNINGS}>
    # GCC
    $<$<CXX_COMPILER_ID:GNU>:${GCC_WARNINGS}>
)

add_library(cccr_core_compiler_optimizations INTERFACE)

set(_cccr_debug_rtc "$<$<CONFIG:Debug>:/RTC1>")
if(CCCR_ENABLE_SANITIZERS AND CCCR_SANITIZER_ADDRESS
    AND NOT CCCR_COMPILER_IS_CLANG_CL)
  set(_cccr_debug_rtc "")
endif()

target_compile_options(cccr_core_compiler_optimizations INTERFACE
    # MSVC and clang-cl (MSVC frontend)
    $<$<OR:$<CXX_COMPILER_ID:MSVC>,$<AND:$<CXX_COMPILER_ID:Clang>,$<PLATFORM_ID:Windows>>>:
        /Zc:preprocessor
        /MP
        $<$<CONFIG:Debug>:/Od /Zi /MDd>
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
    # Linux-only: split DWARF keeps debug info in .dwo files for faster links
    $<$<AND:$<PLATFORM_ID:Linux>,$<OR:$<CXX_COMPILER_ID:GNU>,$<CXX_COMPILER_ID:Clang>>>:
        $<$<CONFIG:Debug>:-gsplit-dwarf>
        $<$<CONFIG:RelWithDebInfo>:-gsplit-dwarf>
    >
    # Clang-only: extra debug info for profiling
    $<$<AND:$<CXX_COMPILER_ID:Clang>,$<NOT:$<PLATFORM_ID:Windows>>>:
        $<$<CONFIG:RelWithDebInfo>:-fdebug-info-for-profiling>
    >
)

target_link_options(cccr_core_compiler_optimizations INTERFACE
    # Export symbols for Debug/RelWithDebInfo so profilers/backtraces work
    $<$<AND:$<OR:$<CXX_COMPILER_ID:GNU>,$<CXX_COMPILER_ID:Clang>>,$<NOT:$<PLATFORM_ID:Windows>>>:
        $<$<OR:$<CONFIG:Debug>,$<CONFIG:RelWithDebInfo>>:-rdynamic>
    >
    # Linux: drop unused sections at link time (pairs with -ffunction-sections/-fdata-sections)
    $<$<AND:$<PLATFORM_ID:Linux>,$<OR:$<CXX_COMPILER_ID:GNU>,$<CXX_COMPILER_ID:Clang>>>:
        $<$<CONFIG:RelWithDebInfo>:-Wl,--gc-sections>
    >
    # macOS: equivalent dead-code stripping
    $<$<AND:$<PLATFORM_ID:Darwin>,$<CXX_COMPILER_ID:Clang>>:
        $<$<CONFIG:RelWithDebInfo>:-Wl,-dead_strip>
    >
    $<$<OR:$<CXX_COMPILER_ID:MSVC>,$<AND:$<CXX_COMPILER_ID:Clang>,$<PLATFORM_ID:Windows>>>:
        $<$<CONFIG:Debug>:/INCREMENTAL>
        $<$<NOT:$<CONFIG:Debug>>:/INCREMENTAL:NO>
        $<$<CONFIG:RelWithDebInfo>:/OPT:REF /OPT:ICF>
    >
)

if(CCCR_BUILD_SHARED)
  add_library(cccr_core SHARED ${CCCR_CORE_ALL_FILES})
else()
  add_library(cccr_core STATIC ${CCCR_CORE_ALL_FILES})
endif()
add_library(cccr::cccr ALIAS cccr_core)

# PCH
target_precompile_headers(cccr_core PRIVATE
    $<$<COMPILE_LANGUAGE:CXX>:${CMAKE_CURRENT_SOURCE_DIR}/src/pch.hpp>
)

# C++ standart setup
set_target_properties(cccr_core PROPERTIES
    CXX_STANDARD 23
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)

# Output dir
set(_output_dir "${PROJECT_SOURCE_DIR}/bin/core/$<LOWER_CASE:$<CONFIG>>-$<LOWER_CASE:${CMAKE_SYSTEM_NAME}>-$<LOWER_CASE:${CMAKE_SYSTEM_PROCESSOR}>")
set_target_properties(cccr_core PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${_output_dir}"
  LIBRARY_OUTPUT_DIRECTORY "${_output_dir}"
  ARCHIVE_OUTPUT_DIRECTORY "${_output_dir}"
)

# Folder setup
set_target_properties(cccr_core PROPERTIES FOLDER core)

# Platform definitions
target_compile_definitions(cccr_core PUBLIC
    $<$<PLATFORM_ID:Windows>:CCCR_PLATFORM_WINDOWS>
    $<$<PLATFORM_ID:Linux>:CCCR_PLATFORM_LINUX>
    $<$<PLATFORM_ID:Darwin>:CCCR_PLATFORM_MACOS>
    $<$<CONFIG:Debug>:CCCR_DEBUG_MODE>
    $<$<CONFIG:RelWithDebInfo>:CCCR_RELEASE_WITH_DEBUG_INFO_MODE>
    $<$<CONFIG:Release>:CCCR_RELEASE_MODE NDEBUG>
)

if(CCCR_BUILD_SHARED)
  # Consumers see CCCR_BUILD_SHARED. Only this target sees CCCR_CORE_BUILDING,
  # which selects dllexport while the shared library is compiled.
  target_compile_definitions(cccr_core
      PUBLIC CCCR_BUILD_SHARED
      PRIVATE CCCR_CORE_BUILDING
  )
  set_target_properties(cccr_core PROPERTIES
      SOVERSION 0
      VERSION "${PROJECT_VERSION}"
      CXX_VISIBILITY_PRESET hidden
      VISIBILITY_INLINES_HIDDEN ON
      INSTALL_RPATH "$ORIGIN"
      INSTALL_RPATH_USE_LINK_PATH FALSE
      BUILD_WITH_INSTALL_RPATH FALSE
  )
endif()

if(WIN32)
  target_compile_definitions(cccr_core PUBLIC
      UNICODE _UNICODE
      WIN32_LEAN_AND_MEAN
      NOMINMAX
  )
endif()

# Warnings + optimization flags (build-tree only; not part of install export)
target_link_libraries(cccr_core PRIVATE
    $<BUILD_INTERFACE:cccr_core_compiler_warnings>
    $<BUILD_INTERFACE:cccr_core_compiler_optimizations>
)

# LTO
if(CCCR_IPO_SUPPORTED)
  set_target_properties(cccr_core PROPERTIES
      INTERPROCEDURAL_OPTIMIZATION_RELWITHDEBINFO ON
      INTERPROCEDURAL_OPTIMIZATION_RELEASE ON
  )
endif()

# Sanitizer support
cccr_target_enable_sanitizers(cccr_core)

target_compile_definitions(cccr_core PUBLIC
    $<$<OR:$<CONFIG:Debug>,$<CONFIG:RelWithDebInfo>>:CCCR_ENABLE_ASSERT>
    CCCR_PROJECT_VERSION="${PROJECT_VERSION}"
)

target_include_directories(cccr_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# Third-party (BUILD_INTERFACE only — install(EXPORT) cannot reference
# non-exported imported targets). A static library's consumers link Redland
# and Saxon again from CCCRConfig.cmake. A shared library keeps them private.
if(CCCR_BUILD_SHARED)
  target_link_libraries(cccr_core PRIVATE
      $<BUILD_INTERFACE:cccr::redland>
      $<BUILD_INTERFACE:glaze::glaze>
      $<BUILD_INTERFACE:SaxonCHE::saxonc-he>
  )
else()
  target_link_libraries(cccr_core
      PUBLIC
          $<BUILD_INTERFACE:cccr::redland>
      PRIVATE
          $<BUILD_INTERFACE:glaze::glaze>
          $<BUILD_INTERFACE:SaxonCHE::saxonc-he>
  )
endif()

if(CCCR_BUILD_SHARED AND CMAKE_SYSTEM_NAME STREQUAL "Linux")
  # One option each: CMake turns commas in LINKER: into separate ld arguments.
  target_link_options(cccr_core PRIVATE
      "LINKER:--exclude-libs=libraptor2.a"
      "LINKER:--exclude-libs=librasqal.a"
      "LINKER:--exclude-libs=librdf.a"
  )
  cccr_saxon_che_apply_build_rpath(cccr_core)
endif()

if(CCCR_REDLAND_VENDORED)
  add_dependencies(cccr_core cccr_redland_ep)
endif()

if(CCCR_BUILD_TESTS)
  set(CCCR_CORE_TESTS
      tests/utils/filesystem.cpp
      tests/utils/macro.cpp
      tests/assert.cpp
      tests/compiler.cpp
      tests/main.cpp
      tests/platform.cpp
      tests/log_smoke.cpp
      tests/example_smoke.cpp
      tests/csv_smoke.cpp
      tests/nested_description.cpp
      tests/include_eval.cpp
      tests/validate.cpp
      tests/predicates_list.cpp
      tests/dual_xquery.cpp
      tests/include_schema.cpp
      tests/xquery_include.cpp
      tests/sparql_context.cpp
      tests/sparql_results.cpp
      tests/nested_subject.cpp
      tests/literal_lang.cpp
      tests/live_kg.cpp
      tests/allocator.cpp
      tests/redland_link.cpp
      tests/merge_range.cpp
      tests/rdf_load.cpp
  )

  add_executable(cccr_core_tests ${CCCR_CORE_TESTS})

  # C++ standart setup
  set_target_properties(cccr_core_tests PROPERTIES
      CXX_STANDARD 23
      CXX_STANDARD_REQUIRED ON
      CXX_EXTENSIONS OFF
  )

  # Output dir
  set(_output_dir "${PROJECT_SOURCE_DIR}/bin/tests/core/$<LOWER_CASE:$<CONFIG>>-$<LOWER_CASE:${CMAKE_SYSTEM_NAME}>-$<LOWER_CASE:${CMAKE_SYSTEM_PROCESSOR}>")
  set_target_properties(cccr_core_tests PROPERTIES
      RUNTIME_OUTPUT_DIRECTORY "${_output_dir}"
      LIBRARY_OUTPUT_DIRECTORY "${_output_dir}"
      ARCHIVE_OUTPUT_DIRECTORY "${_output_dir}"
  )

  # Folder setup
  set_target_properties(cccr_core_tests PROPERTIES FOLDER core/tests)

  # Optimization flags only (no warnings for tests)
  target_link_libraries(cccr_core_tests PRIVATE cccr_core_compiler_optimizations)

  # LTO
  if(CCCR_IPO_SUPPORTED)
    set_target_properties(cccr_core_tests PROPERTIES
        INTERPROCEDURAL_OPTIMIZATION_RELWITHDEBINFO ON
        INTERPROCEDURAL_OPTIMIZATION_RELEASE ON
    )
  endif()

  # Sanitizer support
  cccr_target_enable_sanitizers(cccr_core_tests)

  target_link_libraries(cccr_core_tests PRIVATE
      cccr::cccr
      cccr::redland
      doctest::doctest
  )

  # main.cpp defines DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN before the include,
  # so it cannot use a PCH that already included doctest.h.
  set_source_files_properties(tests/main.cpp PROPERTIES SKIP_PRECOMPILE_HEADERS ON)
  target_precompile_headers(cccr_core_tests PRIVATE
      <doctest/doctest.h>
      <cccr/engine/engine.hpp>
  )

  cccr_saxon_che_apply_build_rpath(cccr_core_tests)

  add_test(NAME cccr_core_tests COMMAND cccr_core_tests)
  set_property(TEST cccr_core_tests PROPERTY LABELS "unit" "core")
endif()

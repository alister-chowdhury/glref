cmake_minimum_required(VERSION 3.10)

project(glref-tools)


if (MSVC)
    add_compile_options(/O2)
else()
    add_compile_options(-O3)
endif()


# Output binaries in ./bin
set(OUTPUT_BIN_DIR                          "${CMAKE_CURRENT_SOURCE_DIR}/bin")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY          "${OUTPUT_BIN_DIR}")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY          "${OUTPUT_BIN_DIR}")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY          "${OUTPUT_BIN_DIR}")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG    "${OUTPUT_BIN_DIR}")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE  "${OUTPUT_BIN_DIR}")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_DEBUG    "${OUTPUT_BIN_DIR}")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_RELEASE  "${OUTPUT_BIN_DIR}")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_DEBUG    "${OUTPUT_BIN_DIR}")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_RELEASE  "${OUTPUT_BIN_DIR}")


find_package(Threads REQUIRED)
add_library(glref_threading_helper INTERFACE)
target_link_libraries(glref_threading_helper INTERFACE Threads::Threads)

# If TBB can be found, disable msdfgen from using OpenMP
# so we can deal with threading at a higher level
find_package(TBB CONFIG)
if(TBB_FOUND)
    set(MSDFGEN_USE_OPENMP                  OFF    CACHE BOOL "" FORCE)
    target_link_libraries(glref_threading_helper INTERFACE TBB::tbb)
    target_compile_definitions(glref_threading_helper INTERFACE -DGLREF_TBB_SUPPORT)

# Otherwise enable it
else()
    set(MSDFGEN_USE_OPENMP                  ON     CACHE BOOL "" FORCE)
endif()

# Build msdfgen
# # At the moment I seem unable to get this to work properly.
# set(MSDFGEN_USE_SKIA                    ON     CACHE BOOL "" FORCE)
set(MSDFGEN_BUILD_MSDFGEN_STANDALONE    OFF    CACHE BOOL "" FORCE)
add_subdirectory("thirdparty/msdfgen")
add_subdirectory("thirdparty/docopt.cpp")


# TODO: Should probably make this per-target...
include_directories("thirdparty/msdfgen")
include_directories("thirdparty/docopt.cpp")



add_subdirectory("indirect-mtsdf-utf8-gen")
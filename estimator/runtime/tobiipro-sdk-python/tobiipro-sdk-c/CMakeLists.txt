cmake_minimum_required(VERSION 3.20)

project(tobii_pro_sdk_for_python)

# add interface library for tobii pro sdk (tobii research)
add_library(tobiipro_sdk INTERFACE)
target_include_directories(tobiipro_sdk INTERFACE 3rd-party/include)
target_link_directories(tobiipro_sdk INTERFACE 3rd-party/lib)
target_link_libraries(tobiipro_sdk INTERFACE tobii_research)

# set a custom variable call MYVAR, with value 42
get_filename_component(tobii_research_dll 3rd-party/lib/tobii_research.dll ABSOLUTE)

# add executable targets residing in subdirectories
add_subdirectory(examples)

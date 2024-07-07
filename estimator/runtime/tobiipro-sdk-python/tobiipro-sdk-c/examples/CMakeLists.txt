file(GLOB EXAMPLES *.c)

foreach(EXAMPLE ${EXAMPLES})
  get_filename_component(EXAMPLE_WE "${EXAMPLE}" NAME_WE)
  add_executable(${EXAMPLE_WE} ${EXAMPLE})
  target_link_libraries(${EXAMPLE_WE} PRIVATE tobiipro_sdk)
endforeach()

# set and unset a variable
set(dll_destination "${CMAKE_CURRENT_BINARY_DIR}/$<CONFIG>")
add_custom_target(copy_dll_for_example ALL
  COMMAND ${CMAKE_COMMAND} -E make_directory ${dll_destination}
  COMMAND ${CMAKE_COMMAND} -E copy ${tobii_research_dll} ${dll_destination})
unset(dll_destination)

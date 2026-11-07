# PyMOOS2Config.cmake: build and install rules for pymoos2 apps.
#
#   pymoos2_add_script_app(NAME pFoo ENTRY pFoo.py [MODULES Foo.py ...] [REQUIRES mod ...])
#   pymoos2_add_package_app(NAME pFoo PACKAGE pfoo [REQUIRES mod ...])
if(NOT PYMOOS2_PYTHON OR NOT EXISTS "${PYMOOS2_PYTHON}")
  set(PyMOOS2_FOUND FALSE)
  set(PyMOOS2_NOT_FOUND_MESSAGE "set PYMOOS2_PYTHON to the interpreter that has pymoos2 installed")
  return()
endif()
include_guard(GLOBAL)

set(PYMOOS2_CMAKE_DIR "${CMAKE_CURRENT_LIST_DIR}" CACHE INTERNAL "Directory of PyMOOS2Config.cmake")
set(PYMOOS2_INSTALL_LIBDIR "lib/pymoos2-apps" CACHE STRING
    "Where `cmake --install` puts package apps, relative to CMAKE_INSTALL_PREFIX")

function(_pymoos2_bin_dir out)
  if(EXECUTABLE_OUTPUT_PATH)
    set(${out} "${EXECUTABLE_OUTPUT_PATH}" PARENT_SCOPE)
  elseif(CMAKE_RUNTIME_OUTPUT_DIRECTORY)
    set(${out} "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}" PARENT_SCOPE)
  else()
    set(${out} "${CMAKE_BINARY_DIR}/bin" PARENT_SCOPE)
  endif()
endfunction()

function(_pymoos2_check_target app src_path)
  add_custom_target(${app}_check
    COMMAND "${PYMOOS2_PYTHON}" -m pymoos2.tools.check "${src_path}" --require pymoos2 ${ARGN}
    COMMENT "Checking ${app} sources and imports with ${PYMOOS2_PYTHON}"
    VERBATIM)
endfunction()

function(pymoos2_add_script_app)
  cmake_parse_arguments(A "" "NAME;ENTRY" "MODULES;REQUIRES" ${ARGN})
  if(NOT A_NAME OR NOT A_ENTRY)
    message(FATAL_ERROR "pymoos2_add_script_app needs NAME and ENTRY")
  endif()
  set(src "${CMAKE_CURRENT_SOURCE_DIR}")
  _pymoos2_bin_dir(bin)
  _pymoos2_check_target(${A_NAME} "${src}" ${A_REQUIRES})
  set(module_paths "")
  foreach(m ${A_MODULES})
    list(APPEND module_paths "${src}/${m}")
  endforeach()
  add_custom_target(${A_NAME} ALL
    COMMAND "${PYMOOS2_PYTHON}" -m pymoos2.tools.install_script
            --python "${PYMOOS2_PYTHON}" --dest "${bin}" --name ${A_NAME}
            "${src}/${A_ENTRY}" ${module_paths}
    DEPENDS ${A_NAME}_check
    COMMENT "Installing ${A_NAME} to ${bin}"
    VERBATIM)
  install(PROGRAMS "${bin}/${A_NAME}" DESTINATION bin)
  foreach(m ${A_MODULES})
    install(FILES "${bin}/${m}" DESTINATION bin)
  endforeach()
endfunction()

function(pymoos2_add_package_app)
  cmake_parse_arguments(A "" "NAME;PACKAGE" "REQUIRES" ${ARGN})
  if(NOT A_NAME OR NOT A_PACKAGE)
    message(FATAL_ERROR "pymoos2_add_package_app needs NAME and PACKAGE")
  endif()
  set(src "${CMAKE_CURRENT_SOURCE_DIR}")
  if(NOT IS_DIRECTORY "${src}/${A_PACKAGE}")
    message(FATAL_ERROR "${A_NAME}: package directory ${src}/${A_PACKAGE} not found")
  endif()
  _pymoos2_bin_dir(bin)
  _pymoos2_check_target(${A_NAME} "${src}/${A_PACKAGE}" ${A_REQUIRES})

  set(APP_NAME ${A_NAME})
  set(PKG_NAME ${A_PACKAGE})
  string(TOUPPER "${A_NAME}" APP_NAME_UPPER)
  string(REGEX REPLACE "[^A-Z0-9_]" "_" APP_NAME_UPPER "${APP_NAME_UPPER}")

  set(PKG_ROOT_LINE "PKG_ROOT=\"${src}\"")
  configure_file("${PYMOOS2_CMAKE_DIR}/launcher.sh.in" "${CMAKE_CURRENT_BINARY_DIR}/${A_NAME}" @ONLY)
  set(PKG_ROOT_LINE "PKG_ROOT=\"$(cd \"$(dirname \"$0\")/../${PYMOOS2_INSTALL_LIBDIR}/${A_NAME}\" && pwd)\"")
  configure_file("${PYMOOS2_CMAKE_DIR}/launcher.sh.in" "${CMAKE_CURRENT_BINARY_DIR}/install/${A_NAME}" @ONLY)

  add_custom_target(${A_NAME} ALL
    COMMAND ${CMAKE_COMMAND} -E make_directory "${bin}"
    COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_CURRENT_BINARY_DIR}/${A_NAME}" "${bin}/${A_NAME}"
    COMMAND chmod +x "${bin}/${A_NAME}"
    DEPENDS ${A_NAME}_check
    COMMENT "Installing ${A_NAME} launcher to ${bin}"
    VERBATIM)

  install(DIRECTORY "${src}/${A_PACKAGE}"
          DESTINATION "${PYMOOS2_INSTALL_LIBDIR}/${A_NAME}"
          PATTERN "__pycache__" EXCLUDE
          PATTERN "*.pyc" EXCLUDE)
  install(PROGRAMS "${CMAKE_CURRENT_BINARY_DIR}/install/${A_NAME}" DESTINATION bin)
endfunction()

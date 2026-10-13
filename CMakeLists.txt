cmake_minimum_required(VERSION 3.25)

project(godot LANGUAGES C CXX ASM)

find_program(CCACHE_PROGRAM ccache)
if(CCACHE_PROGRAM)
    message(STATUS "ccache found, using it")
    set(CMAKE_C_COMPILER_LAUNCHER ${CCACHE_PROGRAM})
    set(CMAKE_CXX_COMPILER_LAUNCHER ${CCACHE_PROGRAM})
endif()

if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    message(FATAL_ERROR "This CMake build only supports Linux.")
endif()

set(CMAKE_C_STANDARD 17)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
option(FEATURE_EDITOR "Build the editor instead of an export template" ON)
option(FEATURE_DEV_BUILD "Enable engine-developer only code (DEV_ENABLED)" OFF)
option(FEATURE_DEPRECATED "Compile deprecated compatibility code" ON)
option(FEATURE_DOUBLE_PRECISION "Use double precision for real_t" OFF)

option(FEATURE_RENDERING_DEVICE "Enable the RenderingDevice abstraction" ON)
option(FEATURE_FORWARD_PLUS "Enable the Forward+ renderer" ON)
option(FEATURE_FORWARD_MOBILE "Enable the Mobile renderer" ON)
option(FEATURE_VULKAN "Enable the Vulkan rendering driver" ON)
option(FEATURE_OPENGL "Enable the OpenGL / GLES3 rendering driver" ON)
option(FEATURE_SDL "Enable the SDL3 input driver" ON)

option(FEATURE_X11 "Enable the X11 display server" ON)
option(FEATURE_WAYLAND "Enable the Wayland display server" ON)
option(FEATURE_LIBDECOR "Enable libdecor client-side decorations" ON)
option(FEATURE_ALSA "Enable the ALSA audio driver" ON)
option(FEATURE_PULSEAUDIO "Enable the PulseAudio audio driver" ON)
option(FEATURE_DBUS "Enable D-Bus integration" ON)
option(FEATURE_SPEECHD "Enable text-to-speech via Speech Dispatcher" ON)
option(FEATURE_FONTCONFIG "Enable fontconfig system fonts" ON)
option(FEATURE_UDEV "Enable udev controller hotplugging" ON)
option(FEATURE_DYNAMIC_LOADING "dlopen system libraries instead of linking them" ON)

option(FEATURE_MINIZIP "Enable ZIP archive support" ON)
option(FEATURE_BROTLI "Enable Brotli decompression and WOFF2 fonts" ON)
option(FEATURE_UPDATE_CHECK "Enable the editor update check" OFF)

# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------
set(GODOT_MODULE_LIST
    astcenc basis_universal bcdec betsy bmp camera csg cvtt dds enet etcpak fbx
    freetype gdscript glslang gltf godot_physics_2d godot_physics_3d gridmap hdr
    interactive_music jolt_physics jpg jsonrpc ktx lightmapper_rd mbedtls meshoptimizer
    mobile_vr mp3 msdfgen multiplayer navigation_2d navigation_3d noise ogg raycast
    svg text_server_adv text_server_fb texture_streaming tga theora tilemap tinyexr
    upnp vhacd visual_shader vorbis webp websocket xatlas_unwrap zip
)

set(GODOT_MODULES_DEFAULT_OFF mbedtls websocket bmp mp3 mobile_vr)

set(GODOT_ENABLED_MODULES "")
foreach(module IN LISTS GODOT_MODULE_LIST)
    string(TOUPPER ${module} MODULE_UPPER)
    if(module IN_LIST GODOT_MODULES_DEFAULT_OFF)
        set(module_default OFF)
    else()
        set(module_default ON)
    endif()
    option(FEATURE_MODULE_${MODULE_UPPER} "Enable the '${module}' module" ${module_default})
    if(FEATURE_MODULE_${MODULE_UPPER})
        list(APPEND GODOT_ENABLED_MODULES ${module})
    endif()
endforeach()

# Feature interdependencies.
if(NOT FEATURE_RENDERING_DEVICE OR (NOT FEATURE_FORWARD_PLUS AND NOT FEATURE_FORWARD_MOBILE))
    set(FEATURE_VULKAN OFF)
endif()
if(NOT FEATURE_VULKAN AND NOT FEATURE_OPENGL)
    message(FATAL_ERROR "At least one of FEATURE_VULKAN / FEATURE_OPENGL must be enabled.")
endif()
if(FEATURE_WAYLAND AND NOT FEATURE_X11 AND NOT FEATURE_VULKAN AND NOT FEATURE_OPENGL)
    set(FEATURE_WAYLAND OFF)
endif()
if(NOT FEATURE_BROTLI)
    message(FATAL_ERROR "Brotli is required for WOFF2 font support.")
endif()

# ---------------------------------------------------------------------------
# Generated sources (single code generation step)
# ---------------------------------------------------------------------------
find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(GEN_DIR ${CMAKE_BINARY_DIR}/gen)
set(GEN_STAMP ${CMAKE_BINARY_DIR}/.godot_generated.stamp)

file(GLOB_RECURSE GEN_SHADERS CONFIGURE_DEPENDS
    ${CMAKE_SOURCE_DIR}/servers/rendering/**/*.glsl)
file(GLOB GEN_ICONS
    ${CMAKE_SOURCE_DIR}/editor/icons/*.svg
    ${CMAKE_SOURCE_DIR}/scene/theme/icons/*.svg
    ${CMAKE_SOURCE_DIR}/scene/theme/icons/debug_icons/*.svg
    ${CMAKE_SOURCE_DIR}/platform/linuxbsd/export/*.svg)
file(GLOB GEN_MODULE_ICONS ${CMAKE_SOURCE_DIR}/modules/*/icons/*.svg)
file(GLOB GEN_FONTS
    ${CMAKE_SOURCE_DIR}/thirdparty/fonts/*.ttf
    ${CMAKE_SOURCE_DIR}/thirdparty/fonts/*.otf
    ${CMAKE_SOURCE_DIR}/thirdparty/fonts/*.woff
    ${CMAKE_SOURCE_DIR}/thirdparty/fonts/*.woff2)
file(GLOB GEN_BUILDERS
    ${CMAKE_SOURCE_DIR}/*_builders.py
    ${CMAKE_SOURCE_DIR}/core/*_builders.py
    ${CMAKE_SOURCE_DIR}/core/*/*.py
    ${CMAKE_SOURCE_DIR}/editor/*.py
    ${CMAKE_SOURCE_DIR}/editor/*/*.py
    ${CMAKE_SOURCE_DIR}/main/*.py
    ${CMAKE_SOURCE_DIR}/platform/platform_builders.py
    ${CMAKE_SOURCE_DIR}/scene/theme/*.py
    ${CMAKE_SOURCE_DIR}/scene/theme/icons/*.py
    ${CMAKE_SOURCE_DIR}/servers/rendering/storage/*.py
    ${CMAKE_SOURCE_DIR}/modules/text_server_adv/*.py)

set(GEN_INPUTS
    ${GEN_SHADERS} ${GEN_ICONS} ${GEN_MODULE_ICONS} ${GEN_FONTS} ${GEN_BUILDERS}
    ${CMAKE_SOURCE_DIR}/misc/cmake/generate.py
    ${CMAKE_SOURCE_DIR}/methods.py
    ${CMAKE_SOURCE_DIR}/version.py
    ${CMAKE_SOURCE_DIR}/AUTHORS.md
    ${CMAKE_SOURCE_DIR}/DONORS.md
    ${CMAKE_SOURCE_DIR}/LICENSE.txt
    ${CMAKE_SOURCE_DIR}/COPYRIGHT.txt
    ${CMAKE_SOURCE_DIR}/thirdparty/certs/ca-bundle.crt
    ${CMAKE_SOURCE_DIR}/thirdparty/smaa/AreaTex.png
    ${CMAKE_SOURCE_DIR}/thirdparty/smaa/SearchTex.png
    ${CMAKE_SOURCE_DIR}/thirdparty/icu4c/icudt_godot.dat
    ${CMAKE_SOURCE_DIR}/main/splash.png
    ${CMAKE_SOURCE_DIR}/main/app_icon.png
    ${CMAKE_SOURCE_DIR}/core/input/gamecontrollerdb.txt
    ${CMAKE_SOURCE_DIR}/core/input/godotcontrollerdb.txt
    ${CMAKE_SOURCE_DIR}/servers/rendering/storage/ltc/ltc_lut1.dds
    ${CMAKE_SOURCE_DIR}/servers/rendering/storage/ltc/ltc_lut2.dds
    ${CMAKE_SOURCE_DIR}/modules/gdscript/editor/script_templates)

if(FEATURE_WAYLAND)
    find_program(WAYLAND_SCANNER wayland-scanner)
    if(NOT WAYLAND_SCANNER)
        message(WARNING "wayland-scanner not found, disabling Wayland support")
        set(FEATURE_WAYLAND OFF)
    endif()
endif()

set(GEN_ARGS --root ${CMAKE_SOURCE_DIR} --out ${GEN_DIR})
if(FEATURE_EDITOR)
    list(APPEND GEN_ARGS --editor)
endif()
if(FEATURE_OPENGL)
    list(APPEND GEN_ARGS --gles3)
endif()
if(FEATURE_WAYLAND)
    list(APPEND GEN_ARGS --wayland)
endif()
if(FEATURE_MODULE_TEXT_SERVER_ADV AND FEATURE_EDITOR)
    list(APPEND GEN_ARGS --icu-data)
endif()
foreach(module IN LISTS GODOT_ENABLED_MODULES)
    list(APPEND GEN_ARGS --module-icons ${module}/icons)
endforeach()

add_custom_command(
    OUTPUT ${GEN_STAMP}
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/misc/cmake/generate.py ${GEN_ARGS}
    COMMAND ${CMAKE_COMMAND} -E touch ${GEN_STAMP}
    DEPENDS ${GEN_INPUTS}
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Generating Godot generated sources"
    VERBATIM
)
add_custom_target(godot_generated DEPENDS ${GEN_STAMP})

# Generated headers are included by bare filename all over the tree, so every
# directory holding one has to be reachable from the include path.
execute_process(
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/misc/cmake/generate.py ${GEN_ARGS}
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    RESULT_VARIABLE GEN_RESULT
)
if(NOT GEN_RESULT EQUAL 0)
    message(FATAL_ERROR "Godot source generation failed (${GEN_RESULT})")
endif()

file(GLOB_RECURSE GEN_DIRS LIST_DIRECTORIES true ${GEN_DIR}/*)
set(GEN_INCLUDE_DIRS ${GEN_DIR})
foreach(gen_dir IN LISTS GEN_DIRS)
    if(IS_DIRECTORY ${gen_dir})
        list(APPEND GEN_INCLUDE_DIRS ${gen_dir})
    endif()
endforeach()
list(REMOVE_DUPLICATES GEN_INCLUDE_DIRS)

# Module defines and registration, generated directly by CMake.
set(MODULES_ENABLED_H "")
set(REGISTER_MODULES_CPP "#include \"register_module_types.h\"\n\n#include \"modules/modules_enabled.gen.h\"\n\n")
foreach(module IN LISTS GODOT_ENABLED_MODULES)
    string(TOUPPER ${module} MODULE_UPPER)
    string(APPEND MODULES_ENABLED_H "#define MODULE_${MODULE_UPPER}_ENABLED\n")
    string(APPEND REGISTER_MODULES_CPP
        "\n// IWYU pragma: begin_keep.\n#include \"modules/${module}/register_types.h\"\n")
endforeach()
string(APPEND REGISTER_MODULES_CPP "// IWYU pragma: end_keep.\n\nvoid initialize_modules(ModuleInitializationLevel p_level) {\n")
foreach(module IN LISTS GODOT_ENABLED_MODULES)
    string(TOUPPER ${module} MODULE_UPPER)
    string(APPEND REGISTER_MODULES_CPP
        "\n#ifdef MODULE_${MODULE_UPPER}_ENABLED\n\tinitialize_${module}_module(p_level);\n#endif")
endforeach()
string(APPEND REGISTER_MODULES_CPP "\n}\n\nvoid uninitialize_modules(ModuleInitializationLevel p_level) {\n")
foreach(module IN LISTS GODOT_ENABLED_MODULES)
    string(TOUPPER ${module} MODULE_UPPER)
    string(APPEND REGISTER_MODULES_CPP
        "\n#ifdef MODULE_${MODULE_UPPER}_ENABLED\n\tuninitialize_${module}_module(p_level);\n#endif")
endforeach()
string(APPEND REGISTER_MODULES_CPP "\n}\n")

file(GENERATE OUTPUT ${GEN_DIR}/modules/modules_enabled.gen.h CONTENT "${MODULES_ENABLED_H}")
file(GENERATE OUTPUT ${GEN_DIR}/modules/register_module_types.gen.cpp CONTENT "${REGISTER_MODULES_CPP}")

# ---------------------------------------------------------------------------
# Global compile setup
# ---------------------------------------------------------------------------
find_package(Threads REQUIRED)

add_compile_options(
    -ffp-contract=off
    $<$<COMPILE_LANGUAGE:CXX>:-fno-exceptions>
)

include(CheckCXXCompilerFlag)
check_cxx_compiler_flag("-msse4.2" GODOT_HAS_SSE42)
if(GODOT_HAS_SSE42 AND CMAKE_SIZEOF_VOID_P EQUAL 8)
    add_compile_options(-msse4.2 -mpopcnt)
endif()

set(GODOT_DEFINES
    LINUXBSD_ENABLED
    UNIX_ENABLED
    THREADS_ENABLED
    OVERRIDE_ENABLED
    OVERRIDE_PATH_ENABLED
    CRASH_HANDLER_ENABLED
    _FILE_OFFSET_BITS=64
    _LIBCPP_REMOVE_TRANSITIVE_INCLUDES
)
if(FEATURE_EDITOR)
    list(APPEND GODOT_DEFINES TOOLS_ENABLED DEBUG_ENABLED ENGINE_UPDATE_CHECK_ENABLED NO_EDITOR_SPLASH)
else()
    list(APPEND GODOT_DEFINES DEBUG_ENABLED)
endif()
if(FEATURE_DEV_BUILD)
    list(APPEND GODOT_DEFINES DEV_ENABLED)
else()
    list(APPEND GODOT_DEFINES NDEBUG)
endif()
if(NOT FEATURE_DEPRECATED)
    list(APPEND GODOT_DEFINES DISABLE_DEPRECATED)
endif()
if(FEATURE_DOUBLE_PRECISION)
    list(APPEND GODOT_DEFINES REAL_T_IS_DOUBLE)
endif()
if(FEATURE_MINIZIP)
    list(APPEND GODOT_DEFINES MINIZIP_ENABLED)
endif()
if(FEATURE_BROTLI)
    list(APPEND GODOT_DEFINES BROTLI_ENABLED)
endif()
if(FEATURE_RENDERING_DEVICE)
    list(APPEND GODOT_DEFINES RD_ENABLED)
    if(FEATURE_FORWARD_PLUS)
        list(APPEND GODOT_DEFINES FORWARD_RD_ENABLED)
    endif()
    if(FEATURE_FORWARD_MOBILE)
        list(APPEND GODOT_DEFINES MOBILE_RD_ENABLED)
    endif()
endif()
if(FEATURE_DYNAMIC_LOADING)
    list(APPEND GODOT_DEFINES SOWRAP_ENABLED)
endif()
if(FEATURE_X11)
    list(APPEND GODOT_DEFINES X11_ENABLED)
endif()
if(FEATURE_WAYLAND)
    list(APPEND GODOT_DEFINES WAYLAND_ENABLED)
    if(FEATURE_LIBDECOR)
        list(APPEND GODOT_DEFINES LIBDECOR_ENABLED)
    endif()
endif()
if(FEATURE_ALSA)
    list(APPEND GODOT_DEFINES ALSA_ENABLED ALSAMIDI_ENABLED)
endif()
if(FEATURE_PULSEAUDIO)
    list(APPEND GODOT_DEFINES PULSEAUDIO_ENABLED _REENTRANT)
endif()
if(FEATURE_DBUS)
    list(APPEND GODOT_DEFINES DBUS_ENABLED)
endif()
if(FEATURE_SPEECHD)
    list(APPEND GODOT_DEFINES SPEECHD_ENABLED)
endif()
if(FEATURE_FONTCONFIG)
    list(APPEND GODOT_DEFINES FONTCONFIG_ENABLED)
endif()
if(FEATURE_UDEV)
    list(APPEND GODOT_DEFINES UDEV_ENABLED TOUCH_ENABLED)
endif()
if(FEATURE_VULKAN)
    list(APPEND GODOT_DEFINES VULKAN_ENABLED USE_VOLK VMA_EXTERNAL_MEMORY_WIN32=0 VMA_STATIC_VULKAN_FUNCTIONS=1)
    if(FEATURE_X11)
        list(APPEND GODOT_DEFINES VK_USE_PLATFORM_XLIB_KHR)
    endif()
    if(FEATURE_WAYLAND)
        list(APPEND GODOT_DEFINES VK_USE_PLATFORM_WAYLAND_KHR)
    endif()
endif()
if(FEATURE_OPENGL)
    list(APPEND GODOT_DEFINES GLES3_ENABLED GLAD_ENABLED EGL_ENABLED GLAD_GLES2 GLAD_GLX_NO_X11)
endif()
if(FEATURE_SDL)
    list(APPEND GODOT_DEFINES SDL_ENABLED)
endif()

if(FEATURE_MODULE_TEXT_SERVER_ADV)
    list(APPEND GODOT_DEFINES U_STATIC_IMPLEMENTATION U_HAVE_LIB_SUFFIX=1
            U_LIB_SUFFIX_C_NAME=_godot HAVE_ICU_BUILTIN)
    if(FEATURE_EDITOR)
        list(APPEND GODOT_DEFINES ICU_STATIC_DATA)
    endif()
endif()

# Defines that the bundled libraries expect the Godot sources to see as well.
if(FEATURE_MODULE_ENET)
    list(APPEND GODOT_DEFINES GODOT_ENET)
endif()
if(FEATURE_MODULE_MSDFGEN)
    list(APPEND GODOT_DEFINES MSDFGEN_PUBLIC=)
endif()
if(FEATURE_MODULE_SVG)
    list(APPEND GODOT_DEFINES TVG_STATIC)
endif()
if(FEATURE_MODULE_FREETYPE AND FEATURE_BROTLI)
    list(APPEND GODOT_DEFINES FT_CONFIG_OPTION_USE_BROTLI)
endif()
if(FEATURE_DYNAMIC_LOADING)
    list(APPEND GODOT_DEFINES SOWRAP_ENABLED)
endif()
if(NOT FEATURE_EDITOR AND "gdscript" IN_LIST GODOT_ENABLED_MODULES)
    list(APPEND GODOT_DEFINES GDSCRIPT_NO_LSP)
endif()
set(VULKAN_PLATFORM_DEFINES "")
if(FEATURE_X11)
    list(APPEND VULKAN_PLATFORM_DEFINES VK_USE_PLATFORM_XLIB_KHR)
endif()
if(FEATURE_WAYLAND)
    list(APPEND VULKAN_PLATFORM_DEFINES VK_USE_PLATFORM_WAYLAND_KHR)
endif()
list(APPEND GODOT_DEFINES ZSTD_STATIC_LINKING_ONLY CLIPPER2_ENABLED ${VULKAN_PLATFORM_DEFINES})

add_library(godot_common INTERFACE)
target_compile_definitions(godot_common INTERFACE ${GODOT_DEFINES})
target_include_directories(godot_common INTERFACE
    # Ahead of the real system headers so the dlopen stubs win.
    $<$<BOOL:${FEATURE_DYNAMIC_LOADING}>:${CMAKE_SOURCE_DIR}/thirdparty/linuxbsd_headers>
    ${CMAKE_SOURCE_DIR}
    ${CMAKE_SOURCE_DIR}/platform
    ${CMAKE_SOURCE_DIR}/platform/linuxbsd
    ${CMAKE_SOURCE_DIR}/modules
    ${CMAKE_SOURCE_DIR}/thirdparty
    ${CMAKE_SOURCE_DIR}/thirdparty/dr_libs
    ${CMAKE_SOURCE_DIR}/thirdparty/grisu2
    ${GEN_INCLUDE_DIRS}
)
add_dependencies(godot_common godot_generated)

# ---------------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------------
set(THIRDPARTY_LIBS "")

if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64|i686|i386)$")
    set(GODOT_ARCH_X86 ON)
else()
    set(GODOT_ARCH_X86 OFF)
endif()
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64|arm.*)$")
    set(GODOT_ARCH_ARM ON)
else()
    set(GODOT_ARCH_ARM OFF)
endif()

function(godot_thirdparty name)
    cmake_parse_arguments(TP "" "" "SOURCES;INCLUDES;PUBLIC_INCLUDES;DEFINES;PUBLIC_DEFINES;EXTRA_FLAGS" ${ARGN})
    add_library(${name} STATIC ${TP_SOURCES})
    target_link_libraries(${name} PUBLIC godot_common)
    target_include_directories(${name} SYSTEM PUBLIC ${TP_INCLUDES})
    target_include_directories(${name} SYSTEM PUBLIC ${TP_PUBLIC_INCLUDES})
    target_compile_definitions(${name} PRIVATE ${TP_DEFINES})
    target_compile_definitions(${name} PUBLIC ${TP_PUBLIC_DEFINES})
    target_compile_options(${name} PRIVATE -w ${TP_EXTRA_FLAGS})
    set(THIRDPARTY_LIBS ${THIRDPARTY_LIBS} ${name} PARENT_SCOPE)
endfunction()

function(godot_engine_library name)
    cmake_parse_arguments(LIB "" "" "SOURCES;PUBLIC_INCLUDES" ${ARGN})
    add_library(${name} STATIC ${LIB_SOURCES})
    target_link_libraries(${name} PUBLIC godot_common)
    target_include_directories(${name} PUBLIC ${LIB_PUBLIC_INCLUDES})
    target_compile_options(${name} PRIVATE -Wall -Wno-unused-parameter)
    set(GODOT_ENGINE_LIBS ${GODOT_ENGINE_LIBS} ${name} PARENT_SCOPE)
endfunction()

# --- core's bundled libraries
godot_thirdparty(tp_misc SOURCES
    ${CMAKE_SOURCE_DIR}/thirdparty/misc/fastlz.c
    ${CMAKE_SOURCE_DIR}/thirdparty/misc/qoa.c
    ${CMAKE_SOURCE_DIR}/thirdparty/misc/r128.c
    ${CMAKE_SOURCE_DIR}/thirdparty/misc/smaz.c
    ${CMAKE_SOURCE_DIR}/thirdparty/misc/pcg.cpp
    ${CMAKE_SOURCE_DIR}/thirdparty/misc/polypartition.cpp
    ${CMAKE_SOURCE_DIR}/thirdparty/misc/smolv.cpp
)

if(FEATURE_BROTLI)
    file(GLOB BROTLI_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/brotli/common/*.c
                            ${CMAKE_SOURCE_DIR}/thirdparty/brotli/dec/*.c)
    godot_thirdparty(tp_brotli
        SOURCES ${BROTLI_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/brotli/include
    )
endif()

if(FEATURE_MINIZIP)
    file(GLOB MINIZIP_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/minizip/*.c)
    godot_thirdparty(tp_minizip
        SOURCES ${MINIZIP_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/minizip
    )
endif()

file(GLOB ZLIB_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/zlib/*.c)
godot_thirdparty(tp_zlib
    SOURCES ${ZLIB_SOURCES}
    INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/zlib
)

file(GLOB ZSTD_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/zstd/common/*.c
                      ${CMAKE_SOURCE_DIR}/thirdparty/zstd/compress/*.c
                      ${CMAKE_SOURCE_DIR}/thirdparty/zstd/decompress/*.c)
if(GODOT_ARCH_X86 AND NOT MSVC)
    list(APPEND ZSTD_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/zstd/decompress/huf_decompress_amd64.S)
endif()
godot_thirdparty(tp_zstd
    SOURCES ${ZSTD_SOURCES}
    INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/zstd ${CMAKE_SOURCE_DIR}/thirdparty/zstd/common
    DEFINES ZSTD_STATIC_LINKING_ONLY
)

file(GLOB PCRE2_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/pcre2/src/*.c)
godot_thirdparty(tp_pcre2
    SOURCES ${PCRE2_SOURCES}
    INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/pcre2/src
    DEFINES PCRE2_STATIC HAVE_CONFIG_H SUPPORT_UNICODE PCRE2_CODE_UNIT_WIDTH=32 SUPPORT_JIT
)

file(GLOB CLIPPER2_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/clipper2/src/*.cpp)
godot_thirdparty(tp_clipper2
    SOURCES ${CLIPPER2_SOURCES}
    INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/clipper2/include
    DEFINES CLIPPER2_ENABLED
)

file(GLOB PNG_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/libpng/*.c)
if(GODOT_ARCH_X86)
    list(APPEND PNG_SOURCES
        ${CMAKE_SOURCE_DIR}/thirdparty/libpng/intel/intel_init.c
        ${CMAKE_SOURCE_DIR}/thirdparty/libpng/intel/filter_sse2_intrinsics.c)
elseif(GODOT_ARCH_ARM)
    list(APPEND PNG_SOURCES
        ${CMAKE_SOURCE_DIR}/thirdparty/libpng/arm/arm_init.c
        ${CMAKE_SOURCE_DIR}/thirdparty/libpng/arm/filter_neon_intrinsics.c
        ${CMAKE_SOURCE_DIR}/thirdparty/libpng/arm/palette_neon_intrinsics.c)
endif()
godot_thirdparty(tp_libpng
    SOURCES ${PNG_SOURCES}
    INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/libpng
    DEFINES PNG_INTEL_SSE
)

# --- rendering
if(FEATURE_VULKAN)
    godot_thirdparty(tp_vulkan
        SOURCES
            ${CMAKE_SOURCE_DIR}/thirdparty/vulkan/vk_mem_alloc.cpp
            ${CMAKE_SOURCE_DIR}/thirdparty/volk/volk.c
            ${CMAKE_SOURCE_DIR}/thirdparty/re-spirv/re-spirv.cpp
        INCLUDES
            ${CMAKE_SOURCE_DIR}/thirdparty/vulkan
            ${CMAKE_SOURCE_DIR}/thirdparty/vulkan/include
            ${CMAKE_SOURCE_DIR}/thirdparty/volk
            ${CMAKE_SOURCE_DIR}/thirdparty/spirv-headers/include
    )
endif()

if(FEATURE_OPENGL)
    godot_thirdparty(tp_glad
        SOURCES
            ${CMAKE_SOURCE_DIR}/thirdparty/glad/gl.c
            ${CMAKE_SOURCE_DIR}/thirdparty/glad/egl.c
            ${CMAKE_SOURCE_DIR}/thirdparty/glad/glx.c
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/glad
        DEFINES GLAD_GLES2 GLAD_GLX_NO_X11
    )
endif()

if(FEATURE_RENDERING_DEVICE)
    file(GLOB FSR2_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/amd-fsr2/*.cpp)
    godot_thirdparty(tp_fsr2
        SOURCES ${FSR2_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/amd-fsr2
        DEFINES FFX_GCC
    )
    godot_thirdparty(tp_spirv_reflect
        SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/spirv-reflect/spirv_reflect.c
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/spirv-reflect
    )
endif()

# --- audio codecs
if(FEATURE_MODULE_OGG)
    file(GLOB OGG_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/libogg/*.c)
    godot_thirdparty(tp_libogg
        SOURCES ${OGG_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/libogg
    )
endif()

if(FEATURE_MODULE_VORBIS)
    file(GLOB VORBIS_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/libvorbis/*.c)
    list(REMOVE_ITEM VORBIS_SOURCES
        ${CMAKE_SOURCE_DIR}/thirdparty/libvorbis/barkmel.c
        ${CMAKE_SOURCE_DIR}/thirdparty/libvorbis/psytune.c
        ${CMAKE_SOURCE_DIR}/thirdparty/libvorbis/tone.c)
    godot_thirdparty(tp_libvorbis
        SOURCES ${VORBIS_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/libvorbis ${CMAKE_SOURCE_DIR}/thirdparty/libogg
    )
endif()

if(FEATURE_MODULE_THEORA)
    set(THEORA_SOURCES
        bitpack.c decinfo.c decode.c dequant.c fragment.c huffdec.c idct.c info.c
        internal.c quant.c state.c
    )
    if(FEATURE_EDITOR)
        list(APPEND THEORA_SOURCES
            analyze.c encfrag.c encinfo.c encode.c enquant.c fdct.c huffenc.c
            mathops.c mcenc.c rate.c tokenize.c
        )
    endif()
    list(TRANSFORM THEORA_SOURCES PREPEND ${CMAKE_SOURCE_DIR}/thirdparty/libtheora/)
    if(FEATURE_EDITOR AND GODOT_ARCH_X86)
        file(GLOB THEORA_X86_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/libtheora/x86/*.c)
        list(APPEND THEORA_SOURCES ${THEORA_X86_SOURCES})
        set_source_files_properties(${THEORA_X86_SOURCES} PROPERTIES COMPILE_DEFINITIONS "OC_X86_ASM")
    endif()
    godot_thirdparty(tp_libtheora
        SOURCES ${THEORA_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/libtheora
                 ${CMAKE_SOURCE_DIR}/thirdparty/libogg ${CMAKE_SOURCE_DIR}/thirdparty/libvorbis
    )
endif()

if(FEATURE_MODULE_WEBP)
    file(GLOB_RECURSE WEBP_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/libwebp/*.c)
    godot_thirdparty(tp_libwebp
        SOURCES ${WEBP_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/libwebp ${CMAKE_SOURCE_DIR}/thirdparty/libwebp/src
    )
endif()

if(FEATURE_MODULE_JPG)
    set(JPEG_COMMON
        jaricom.c jcapimin.c jcarith.c jchuff.c jcicc.c jcinit.c jcmarker.c jcmaster.c
        jcomapi.c jcparam.c jcphuff.c jctrans.c jdapimin.c jdarith.c jdatadst.c
        jdatadst-tj.c jdatasrc.c jdatasrc-tj.c jdhuff.c jdicc.c jdinput.c jdmarker.c
        jdmaster.c jdphuff.c jdtrans.c jerror.c jfdctflt.c jmemmgr.c jmemnobs.c
        jpeg_nbits.c transupp.c turbojpeg.c)
    set(JPEG_BITDEP
        jcapistd.c jccoefct.c jccolor.c jcdctmgr.c jcmainct.c jcprepct.c jcsample.c
        jdcoefct.c jdcolor.c jdapistd.c jddctmgr.c jdmainct.c jdmerge.c jdpostct.c
        jdsample.c jfdctfst.c jfdctint.c jidctflt.c jidctfst.c jidctint.c jidctred.c
        jutils.c jquant1.c jquant2.c)
    list(TRANSFORM JPEG_COMMON PREPEND ${CMAKE_SOURCE_DIR}/thirdparty/libjpeg-turbo/src/)
    list(TRANSFORM JPEG_BITDEP PREPEND ${CMAKE_SOURCE_DIR}/thirdparty/libjpeg-turbo/src/)
    godot_thirdparty(tp_libjpeg_turbo
        SOURCES ${JPEG_COMMON} ${JPEG_BITDEP}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/libjpeg-turbo/src
    )
    godot_thirdparty(tp_libjpeg_turbo_12
        SOURCES ${JPEG_BITDEP}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/libjpeg-turbo/src
        DEFINES BITS_IN_JSAMPLE=12
    )
endif()

# --- networking / crypto
if(FEATURE_MODULE_ENET)
    file(GLOB ENET_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/enet/*.c)
    list(APPEND ENET_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/enet/enet_godot.cpp)
    godot_thirdparty(tp_enet
        SOURCES ${ENET_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/enet
        DEFINES GODOT_ENET
    )
endif()

if(FEATURE_MODULE_UPNP)
    file(GLOB MINIUPNPC_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/miniupnpc/src/*.c)
    godot_thirdparty(tp_miniupnpc
        SOURCES ${MINIUPNPC_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/miniupnpc/include
                 ${CMAKE_SOURCE_DIR}/thirdparty/miniupnpc/include/miniupnpc
    )
endif()

set(MBEDTLS_DEFINES
    "TF_PSA_CRYPTO_CONFIG_FILE=<godot_psa_config.h>"
    "MBEDTLS_CONFIG_FILE=<godot_mbedtls_config.h>"
)
set(MBEDTLS_INCLUDES
    ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/godot
    ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/include
    ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/include
    ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/drivers/builtin/include
    ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/drivers/builtin/src
    ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/platform
    ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/utilities
    ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/extras
    ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/dispatch
    ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/core
)
if(FEATURE_MODULE_MBEDTLS OR FEATURE_MODULE_WEBSOCKET)
    file(GLOB PSA_CRYPTO_SOURCES
        ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/core/*.c
        ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/drivers/builtin/src/*.c
        ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/extras/*.c
        ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/platform/*.c
        ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/tf-psa-crypto/utilities/*.c)
    godot_thirdparty(tp_psa_crypto
        SOURCES
            ${PSA_CRYPTO_SOURCES}
            ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/godot/godot_mbedtls_platform.cpp
        PUBLIC_INCLUDES ${MBEDTLS_INCLUDES}
        PUBLIC_DEFINES ${MBEDTLS_DEFINES}
    )
    file(GLOB MBEDTLS_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/library/*.c)
    godot_thirdparty(tp_mbedtls
        SOURCES ${MBEDTLS_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/library
        PUBLIC_INCLUDES ${MBEDTLS_INCLUDES}
        PUBLIC_DEFINES ${MBEDTLS_DEFINES}
    )
else()
    list(APPEND MBEDTLS_DEFINES GODOT_MBEDTLS_LIGHT)
    set(MBEDTLS_LIGHT_SOURCES
        tf-psa-crypto/core/psa_crypto.c
        tf-psa-crypto/core/psa_crypto_client.c
        tf-psa-crypto/core/psa_crypto_driver_wrappers_no_static.c
        tf-psa-crypto/core/psa_crypto_random.c
        tf-psa-crypto/core/psa_crypto_slot_management.c
        tf-psa-crypto/utilities/base64.c
        tf-psa-crypto/utilities/constant_time.c
        tf-psa-crypto/platform/threading.c
        tf-psa-crypto/extras/md.c
        tf-psa-crypto/drivers/builtin/src/aes.c
        tf-psa-crypto/drivers/builtin/src/ctr_drbg.c
        tf-psa-crypto/drivers/builtin/src/cipher.c
        tf-psa-crypto/drivers/builtin/src/cipher_wrap.c
        tf-psa-crypto/drivers/builtin/src/entropy.c
        tf-psa-crypto/drivers/builtin/src/entropy_poll.c
        tf-psa-crypto/drivers/builtin/src/md5.c
        tf-psa-crypto/drivers/builtin/src/psa_crypto_cipher.c
        tf-psa-crypto/drivers/builtin/src/psa_crypto_hash.c
        tf-psa-crypto/drivers/builtin/src/psa_crypto_rsa.c
        tf-psa-crypto/drivers/builtin/src/psa_util_internal.c
        tf-psa-crypto/drivers/builtin/src/sha1.c
        tf-psa-crypto/drivers/builtin/src/sha256.c
    )
    list(TRANSFORM MBEDTLS_LIGHT_SOURCES PREPEND ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/)
    godot_thirdparty(tp_mbedtls_light
        SOURCES
            ${MBEDTLS_LIGHT_SOURCES}
            ${CMAKE_SOURCE_DIR}/thirdparty/mbedtls/godot/godot_mbedtls_platform.cpp
        PUBLIC_INCLUDES ${MBEDTLS_INCLUDES}
        PUBLIC_DEFINES ${MBEDTLS_DEFINES}
    )
endif()

if(FEATURE_MODULE_WEBSOCKET)
    file(GLOB WSLAY_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/wslay/*.c)
    godot_thirdparty(tp_wslay
        SOURCES ${WSLAY_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/wslay
        DEFINES HAVE_CONFIG_H HAVE_NETINET_IN_H
    )
endif()

# --- image / geometry codecs used by modules
if(FEATURE_MODULE_ASTCENC)
    file(GLOB ASTCENC_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/astcenc/*.cpp)
    godot_thirdparty(tp_astcenc
        SOURCES ${ASTCENC_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/astcenc
    )
endif()

if(FEATURE_MODULE_BASIS_UNIVERSAL)
    set(BASIS_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/basis_universal/transcoder/basisu_transcoder.cpp)
    # The encoder is only needed by the editor.
    if(FEATURE_EDITOR)
        set(BASIS_ENCODER_SOURCES
            3rdparty/android_astc_decomp.cpp
            basisu_astc_hdr_6x6_enc.cpp
            basisu_astc_hdr_common.cpp
            basisu_backend.cpp
            basisu_basis_file.cpp
            basisu_bc7enc.cpp
            basisu_comp.cpp
            basisu_enc.cpp
            basisu_etc.cpp
            basisu_frontend.cpp
            basisu_gpu_texture.cpp
            basisu_kernels_sse.cpp
            basisu_opencl.cpp
            basisu_pvrtc1_4.cpp
            basisu_resample_filters.cpp
            basisu_resampler.cpp
            basisu_ssim.cpp
            basisu_uastc_enc.cpp
            basisu_uastc_hdr_4x4_enc.cpp
            jpgd.cpp
            pvpngreader.cpp
        )
        list(TRANSFORM BASIS_ENCODER_SOURCES PREPEND ${CMAKE_SOURCE_DIR}/thirdparty/basis_universal/encoder/)
        list(APPEND BASIS_SOURCES ${BASIS_ENCODER_SOURCES})
    endif()
    godot_thirdparty(tp_basis_universal
        SOURCES ${BASIS_SOURCES}
        INCLUDES
            ${CMAKE_SOURCE_DIR}/thirdparty/basis_universal
            ${CMAKE_SOURCE_DIR}/thirdparty/tinyexr
            ${CMAKE_SOURCE_DIR}/thirdparty/zstd
        DEFINES BASISD_SUPPORT_KTX2_ZSTD=1 BASISD_SUPPORT_ATC=0
                BASISD_SUPPORT_FXT1=0 BASISD_SUPPORT_PVRTC1=0 BASISD_SUPPORT_PVRTC2=0
        EXTRA_FLAGS -fno-strict-aliasing
    )
endif()

if(FEATURE_MODULE_CVTT)
    file(GLOB CVTT_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/cvtt/*.cpp)
    godot_thirdparty(tp_cvtt
        SOURCES ${CVTT_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/cvtt
    )
endif()

if(FEATURE_MODULE_ETCPAK)
    file(GLOB ETCPAK_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/etcpak/*.cpp)
    godot_thirdparty(tp_etcpak
        SOURCES ${ETCPAK_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/etcpak
    )
endif()

if(FEATURE_MODULE_FBX)
    godot_thirdparty(tp_ufbx
        SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/ufbx/ufbx.c
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/ufbx
        DEFINES UFBX_NO_SUBDIVISION UFBX_NO_TESSELLATION UFBX_NO_GEOMETRY_CACHE
                UFBX_NO_SCENE_EVALUATION UFBX_NO_INDEX_GENERATION
                UFBX_NO_SKINNING_EVALUATION UFBX_NO_FORMAT_OBJ
    )
endif()

if(FEATURE_MODULE_GLSLANG)
    file(GLOB_RECURSE GLSLANG_SOURCES
        ${CMAKE_SOURCE_DIR}/thirdparty/glslang/glslang/*.cpp
        ${CMAKE_SOURCE_DIR}/thirdparty/glslang/SPIRV/*.cpp)
    list(REMOVE_ITEM GLSLANG_SOURCES
        ${CMAKE_SOURCE_DIR}/thirdparty/glslang/glslang/OSDependent/Windows/ossource.cpp
        ${CMAKE_SOURCE_DIR}/thirdparty/glslang/glslang/OSDependent/Web/glslang.js.cpp)
    godot_thirdparty(tp_glslang
        SOURCES ${GLSLANG_SOURCES}
        INCLUDES
            ${CMAKE_SOURCE_DIR}/thirdparty/glslang
            ${CMAKE_SOURCE_DIR}/thirdparty
            ${CMAKE_SOURCE_DIR}/thirdparty/spirv-headers/include/spirv/unified1
    )
endif()

if(FEATURE_MODULE_KTX)
    file(GLOB KTX_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/libktx/lib/*.c
                         ${CMAKE_SOURCE_DIR}/thirdparty/libktx/lib/*.cpp
                         ${CMAKE_SOURCE_DIR}/thirdparty/libktx/external/dfdutils/*.c)
    godot_thirdparty(tp_libktx
        SOURCES ${KTX_SOURCES}
        INCLUDES
            ${CMAKE_SOURCE_DIR}/thirdparty/libktx/include
            ${CMAKE_SOURCE_DIR}/thirdparty/libktx/utils
            ${CMAKE_SOURCE_DIR}/thirdparty/libktx/lib
            ${CMAKE_SOURCE_DIR}/thirdparty/libktx/other_include
            ${CMAKE_SOURCE_DIR}/thirdparty/libktx/external
            ${CMAKE_SOURCE_DIR}/thirdparty/basis_universal
            ${CMAKE_SOURCE_DIR}/thirdparty/vulkan/include
        DEFINES KHRONOS_STATIC=1
    )
    # The editor already builds miniz through the basis_universal encoder.
    if(FEATURE_EDITOR)
        target_compile_definitions(tp_libktx PRIVATE MINIZ_HEADER_FILE_ONLY)
    endif()
    if(NOT FEATURE_VULKAN)
        target_compile_definitions(tp_libktx PRIVATE LIBKTX)
    endif()
endif()

if(FEATURE_MODULE_MESHOPTIMIZER)
    file(GLOB MESHOPT_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/meshoptimizer/*.cpp)
    godot_thirdparty(tp_meshoptimizer
        SOURCES ${MESHOPT_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/meshoptimizer
    )
endif()

if(FEATURE_MODULE_MSDFGEN)
    file(GLOB MSDFGEN_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/msdfgen/core/*.cpp)
    list(REMOVE_ITEM MSDFGEN_SOURCES
        ${CMAKE_SOURCE_DIR}/thirdparty/msdfgen/core/export-svg.cpp
        ${CMAKE_SOURCE_DIR}/thirdparty/msdfgen/core/save-bmp.cpp
        ${CMAKE_SOURCE_DIR}/thirdparty/msdfgen/core/save-fl32.cpp
        ${CMAKE_SOURCE_DIR}/thirdparty/msdfgen/core/save-rgba.cpp
        ${CMAKE_SOURCE_DIR}/thirdparty/msdfgen/core/save-tiff.cpp)
    godot_thirdparty(tp_msdfgen
        SOURCES ${MSDFGEN_SOURCES}
        INCLUDES
            ${CMAKE_SOURCE_DIR}/thirdparty/msdfgen
            ${CMAKE_SOURCE_DIR}/thirdparty/freetype/include
            ${CMAKE_SOURCE_DIR}/thirdparty/nanosvg
        DEFINES MSDFGEN_PUBLIC=
    )
endif()

if(FEATURE_MODULE_SVG)
    file(GLOB_RECURSE THORVG_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/thorvg/src/*.cpp)
    godot_thirdparty(tp_thorvg
        SOURCES ${THORVG_SOURCES}
        INCLUDES
            ${CMAKE_SOURCE_DIR}/thirdparty/thorvg/inc
            ${CMAKE_SOURCE_DIR}/thirdparty/thorvg/src/common
            ${CMAKE_SOURCE_DIR}/thirdparty/thorvg/src/loaders/svg
            ${CMAKE_SOURCE_DIR}/thirdparty/thorvg/src/renderer
            ${CMAKE_SOURCE_DIR}/thirdparty/thorvg/src/renderer/sw_engine
            ${CMAKE_SOURCE_DIR}/thirdparty/thorvg/src/loaders/raw
            ${CMAKE_SOURCE_DIR}/thirdparty/thorvg/src/loaders/external_png
            ${CMAKE_SOURCE_DIR}/thirdparty/thorvg/src/loaders/external_webp
            ${CMAKE_SOURCE_DIR}/thirdparty/thorvg/src/loaders/external_jpg
            ${CMAKE_SOURCE_DIR}/thirdparty/libpng
            ${CMAKE_SOURCE_DIR}/thirdparty/libwebp/src
            ${CMAKE_SOURCE_DIR}/thirdparty/libjpeg-turbo/src
        DEFINES TVG_STATIC
    )
endif()

if(FEATURE_MODULE_TINYEXR)
    godot_thirdparty(tp_tinyexr
        SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/tinyexr/tinyexr.cc
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/tinyexr ${CMAKE_SOURCE_DIR}/thirdparty/zlib
        DEFINES TINYEXR_USE_THREAD TINYEXR_USE_MINIZ=0
    )
endif()

if(FEATURE_MODULE_VHACD)
    file(GLOB VHACD_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/vhacd/src/*.cpp)
    godot_thirdparty(tp_vhacd
        SOURCES ${VHACD_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/vhacd/inc
    )
endif()

if(FEATURE_MODULE_XATLAS_UNWRAP)
    godot_thirdparty(tp_xatlas
        SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/xatlas/xatlas.cpp
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/xatlas
    )
endif()

if(FEATURE_MODULE_CSG)
    file(GLOB MANIFOLD_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/manifold/src/*.cpp)
    godot_thirdparty(tp_manifold
        SOURCES ${MANIFOLD_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/manifold/include
        DEFINES MANIFOLD_PAR=-1
    )
endif()

if(FEATURE_MODULE_RAYCAST)
    file(GLOB_RECURSE EMBREE_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/embree/*.cpp)
    godot_thirdparty(tp_embree
        SOURCES ${EMBREE_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/embree ${CMAKE_SOURCE_DIR}/thirdparty/embree/include
        DEFINES EMBREE_TARGET_SSE2 EMBREE_LOWEST_ISA TASKING_INTERNAL NDEBUG
        EXTRA_FLAGS -fno-strict-overflow -fno-delete-null-pointer-checks -fwrapv
                  -fsigned-char -fno-tree-vectorize -fvisibility=hidden
                  -fvisibility-inlines-hidden
                  $<$<STREQUAL:${CMAKE_SYSTEM_PROCESSOR},aarch64>:-flax-vector-conversions>
    )
endif()

if(FEATURE_MODULE_NAVIGATION_2D OR FEATURE_MODULE_NAVIGATION_3D)
    file(GLOB RVO2D_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/rvo2/rvo2_2d/*.cpp)
    godot_thirdparty(tp_rvo2_2d
        SOURCES ${RVO2D_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/rvo2/rvo2_2d
    )
    if(FEATURE_MODULE_NAVIGATION_3D)
        file(GLOB RVO2_3D_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/rvo2/rvo2_3d/*.cpp)
        godot_thirdparty(tp_rvo2_3d
            SOURCES ${RVO2_3D_SOURCES}
            INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/rvo2/rvo2_3d
        )
        file(GLOB_RECURSE RECAST_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/recastnavigation/Recast/Source/*.cpp)
        godot_thirdparty(tp_recast
            SOURCES ${RECAST_SOURCES}
            INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/recastnavigation/Recast/Include
        )
    endif()
endif()

if(FEATURE_MODULE_JOLT_PHYSICS)
    file(GLOB_RECURSE JOLT_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/jolt_physics/Jolt/*.cpp)
    godot_thirdparty(tp_jolt
        SOURCES ${JOLT_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/jolt_physics
    )
endif()

if(FEATURE_MODULE_FREETYPE)
    set(FREETYPE_SOURCES
        autofit/autofit.c base/ftbase.c base/ftbbox.c base/ftbdf.c base/ftbitmap.c
        base/ftcid.c base/ftdebug.c base/ftfstype.c base/ftgasp.c base/ftglyph.c
        base/ftgxval.c base/ftinit.c base/ftmm.c base/ftotval.c base/ftpatent.c
        base/ftpfr.c base/ftstroke.c base/ftsynth.c base/ftsystem.c base/fttype1.c
        base/ftwinfnt.c bdf/bdf.c bzip2/ftbzip2.c cache/ftcache.c cff/cff.c
        cid/type1cid.c gxvalid/gxvalid.c gzip/ftgzip.c lzw/ftlzw.c otvalid/otvalid.c
        pcf/pcf.c pfr/pfr.c psaux/psaux.c pshinter/pshinter.c psnames/psnames.c
        raster/raster.c sdf/sdf.c svg/svg.c smooth/smooth.c truetype/truetype.c
        type1/type1.c type42/type42.c winfonts/winfnt.c sfnt/sfnt.c)
    list(TRANSFORM FREETYPE_SOURCES PREPEND ${CMAKE_SOURCE_DIR}/thirdparty/freetype/src/)
    set(FREETYPE_DEFS FT2_BUILD_LIBRARY FT_CONFIG_OPTION_USE_PNG FT_CONFIG_OPTION_SYSTEM_ZLIB)
    if(FEATURE_BROTLI)
        list(APPEND FREETYPE_DEFS FT_CONFIG_OPTION_USE_BROTLI)
    endif()
    if(FEATURE_MODULE_TEXT_SERVER_ADV)
        list(APPEND FREETYPE_DEFS FT_CONFIG_OPTION_USE_HARFBUZZ)
    endif()
    godot_thirdparty(tp_freetype
        SOURCES ${FREETYPE_SOURCES}
        INCLUDES
            ${CMAKE_SOURCE_DIR}/thirdparty/freetype/include
            ${CMAKE_SOURCE_DIR}/thirdparty/libpng
            ${CMAKE_SOURCE_DIR}/thirdparty/harfbuzz/src
            ${CMAKE_SOURCE_DIR}/thirdparty/brotli/include
            ${CMAKE_SOURCE_DIR}/thirdparty/zlib
        DEFINES ${FREETYPE_DEFS}
    )
endif()

if(FEATURE_MODULE_TEXT_SERVER_ADV)
    set(HARFBUZZ_SOURCES
        hb-aat-layout hb-aat-map hb-blob hb-buffer-serialize hb-buffer-verify hb-buffer
        hb-common hb-draw hb-face-builder hb-face hb-fallback-shape hb-font hb-icu
        hb-map hb-number hb-ot-cff1-table hb-ot-cff2-table hb-ot-color hb-ot-face
        hb-ot-font hb-ot-layout hb-ot-map hb-ot-math hb-ot-meta hb-ot-metrics hb-ot-name
        hb-ot-shaper-arabic hb-ot-shaper-default hb-ot-shaper-hangul hb-ot-shaper-hebrew
        hb-ot-shaper-indic-table hb-ot-shaper-indic hb-ot-shaper-khmer hb-ot-shaper-myanmar
        hb-ot-shaper-syllabic hb-ot-shaper-thai hb-ot-shaper-use
        hb-ot-shaper-vowel-constraints hb-ot-shape-fallback hb-ot-shape-normalize
        hb-ot-shape hb-ot-tag hb-ot-var hb-outline hb-paint-bounded hb-paint-extents
        hb-paint hb-set hb-shape-plan hb-shape hb-shaper hb-static hb-style hb-raster
        hb-raster-draw hb-raster-image hb-raster-paint hb-vector-draw
        hb-vector-paint-svg hb-vector-paint hb-vector-path hb-vector hb-subset hb-ucd
        hb-unicode hb-zlib
    )
    list(TRANSFORM HARFBUZZ_SOURCES PREPEND ${CMAKE_SOURCE_DIR}/thirdparty/harfbuzz/src/)
    list(TRANSFORM HARFBUZZ_SOURCES APPEND ".cc")
    list(APPEND HARFBUZZ_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/harfbuzz/src/OT/Var/VARC/VARC.cc)
    if(FEATURE_MODULE_FREETYPE)
        list(APPEND HARFBUZZ_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/harfbuzz/src/hb-ft.cc)
        list(APPEND HARFBUZZ_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/harfbuzz/src/hb-graphite2.cc)
    endif()
    godot_thirdparty(tp_harfbuzz
        SOURCES ${HARFBUZZ_SOURCES}
        INCLUDES
            ${CMAKE_SOURCE_DIR}/thirdparty/harfbuzz/src
            ${CMAKE_SOURCE_DIR}/thirdparty/icu4c/common
            ${CMAKE_SOURCE_DIR}/thirdparty/icu4c/i18n
            ${CMAKE_SOURCE_DIR}/thirdparty/freetype/include
            ${CMAKE_SOURCE_DIR}/thirdparty/graphite/include
            ${CMAKE_SOURCE_DIR}/thirdparty/zlib
            ${CMAKE_SOURCE_DIR}/thirdparty/libpng
        DEFINES HAVE_ICU HAVE_ZLIB HAVE_PNG HAVE_PTHREAD HAVE_FREETYPE HAVE_GRAPHITE2
                U_STATIC_IMPLEMENTATION U_HAVE_LIB_SUFFIX=1 U_LIB_SUFFIX_C_NAME=_godot
                HAVE_ICU_BUILTIN
    )

    file(GLOB GRAPHITE_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/graphite/src/*.cpp)
    list(REMOVE_ITEM GRAPHITE_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/graphite/src/call_machine.cpp)
    godot_thirdparty(tp_graphite
        SOURCES ${GRAPHITE_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/graphite/src ${CMAKE_SOURCE_DIR}/thirdparty/graphite/include
        DEFINES GRAPHITE2_STATIC GRAPHITE2_NTRACING GRAPHITE2_NFILEFACE
    )

    file(GLOB ICU_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/icu4c/common/*.cpp
                         ${CMAKE_SOURCE_DIR}/thirdparty/icu4c/i18n/*.cpp)
    list(REMOVE_ITEM ICU_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/icu4c/common/ushape.cpp)
    if(NOT FEATURE_EDITOR)
        # Export templates ship a stub instead of the ~30 MB ICU data blob.
        list(APPEND ICU_SOURCES ${CMAKE_SOURCE_DIR}/modules/text_server_adv/icu_data/icudata_stub.cpp)
    endif()
    godot_thirdparty(tp_icu
        SOURCES ${ICU_SOURCES}
        INCLUDES ${CMAKE_SOURCE_DIR}/thirdparty/icu4c/common ${CMAKE_SOURCE_DIR}/thirdparty/icu4c/i18n
        DEFINES
            U_STATIC_IMPLEMENTATION U_COMMON_IMPLEMENTATION U_HAVE_LIB_SUFFIX=1
            U_LIB_SUFFIX_C_NAME=_godot U_ENABLE_DYLOAD=0 PKGDATA_MODE=static
            UCONFIG_NO_COLLATION UCONFIG_NO_CONVERSION UCONFIG_NO_FORMATTING
            UCONFIG_NO_SERVICE UCONFIG_NO_IDNA UCONFIG_NO_FILE_IO
            UCONFIG_NO_TRANSLITERATION UCONFIG_NO_REGULAR_EXPRESSIONS
    )
    if(FEATURE_EDITOR)
        list(APPEND GODOT_DEFINES ICU_STATIC_DATA)
    endif()
endif()

if(FEATURE_SDL)
    file(GLOB_RECURSE SDL_SOURCES ${CMAKE_SOURCE_DIR}/thirdparty/sdl/*.c)
    set(SDL_KEEP
        "^${CMAKE_SOURCE_DIR}/thirdparty/sdl/[^/]+\\.c$"
        "/atomic/SDL_(atomic|spinlock)\\.c$"
        "/events/SDL_(events|eventwatch)\\.c$"
        "/haptic/SDL_haptic\\.c$"
        "/haptic/hidapi/SDL_hidapihaptic[^/]*\\.c$"
        "/haptic/linux/SDL_syshaptic\\.c$"
        "/io/SDL_iostream\\.c$"
        "/joystick/SDL_(gamepad|joystick|steam_virtual_gamepad)\\.c$"
        "/joystick/controller_type\\.c$"
        "/joystick/hidapi/[^/]+\\.c$"
        "/joystick/linux/SDL_sysjoystick\\.c$"
        "/libm/[^/]+\\.c$"
        "/loadso/dlopen/SDL_sysloadso\\.c$"
        "/misc/SDL_libusb\\.c$"
        "/sensor/SDL_sensor\\.c$"
        "/sensor/dummy/SDL_dummysensor\\.c$"
        "/stdlib/[^/]+\\.c$"
        "/thread/SDL_thread\\.c$"
        "/thread/pthread/[^/]+\\.c$"
        "/timer/SDL_timer\\.c$"
        "/timer/unix/SDL_systimer\\.c$"
        "/core/linux/[^/]+\\.c$"
        "/core/unix/[^/]+\\.c$"
        "/hidapi/SDL_hidapi\\.c$"
    )
    set(SDL_FILTER "")
    foreach(pat IN LISTS SDL_KEEP)
        string(APPEND SDL_FILTER "${pat}|")
    endforeach()
    string(REGEX REPLACE "\\|$" "" SDL_FILTER "${SDL_FILTER}")
    list(FILTER SDL_SOURCES INCLUDE REGEX "${SDL_FILTER}")
    godot_thirdparty(tp_sdl
        SOURCES ${SDL_SOURCES}
        INCLUDES
            ${CMAKE_SOURCE_DIR}/thirdparty/sdl
            ${CMAKE_SOURCE_DIR}/thirdparty/sdl/include
            ${CMAKE_SOURCE_DIR}/thirdparty/sdl/include/build_config
            ${CMAKE_SOURCE_DIR}/thirdparty/sdl/core/linux
            ${CMAKE_SOURCE_DIR}/drivers/sdl
        DEFINES SDL_PLATFORM_PRIVATE
    )
endif()

# ---------------------------------------------------------------------------
# Godot sources
# ---------------------------------------------------------------------------
# Every Godot translation unit sees the bundled headers, the same way the global
# include path worked before; the link graph stays owned by the executable.
set(GODOT_THIRDPARTY_INCLUDES "")
set(GODOT_THIRDPARTY_DEFINES "")
foreach(tp IN LISTS THIRDPARTY_LIBS)
    get_target_property(tp_includes ${tp} INTERFACE_INCLUDE_DIRECTORIES)
    if(tp_includes)
        list(APPEND GODOT_THIRDPARTY_INCLUDES ${tp_includes})
    endif()
    get_target_property(tp_defines ${tp} INTERFACE_COMPILE_DEFINITIONS)
    if(tp_defines)
        list(APPEND GODOT_THIRDPARTY_DEFINES ${tp_defines})
    endif()
endforeach()
list(REMOVE_DUPLICATES GODOT_THIRDPARTY_INCLUDES)
list(REMOVE_DUPLICATES GODOT_THIRDPARTY_DEFINES)
target_include_directories(godot_common SYSTEM INTERFACE ${GODOT_THIRDPARTY_INCLUDES})
target_compile_definitions(godot_common INTERFACE ${GODOT_THIRDPARTY_DEFINES})

file(GLOB_RECURSE GODOT_CORE_SOURCES CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/core/*.cpp)
file(GLOB_RECURSE GODOT_SERVERS_SOURCES CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/servers/*.cpp)
file(GLOB_RECURSE GODOT_SCENE_SOURCES CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/scene/*.cpp)
file(GLOB GODOT_MAIN_SOURCES ${CMAKE_SOURCE_DIR}/main/*.cpp)

set(GODOT_DRIVER_SOURCES
    ${CMAKE_SOURCE_DIR}/drivers/register_driver_types.cpp
    ${CMAKE_SOURCE_DIR}/drivers/unix
    ${CMAKE_SOURCE_DIR}/drivers/png
)
if(FEATURE_ALSA)
    list(APPEND GODOT_DRIVER_SOURCES ${CMAKE_SOURCE_DIR}/drivers/alsa ${CMAKE_SOURCE_DIR}/drivers/alsamidi)
endif()
if(FEATURE_PULSEAUDIO)
    list(APPEND GODOT_DRIVER_SOURCES ${CMAKE_SOURCE_DIR}/drivers/pulseaudio)
endif()
if(FEATURE_VULKAN)
    list(APPEND GODOT_DRIVER_SOURCES ${CMAKE_SOURCE_DIR}/drivers/vulkan)
endif()
if(FEATURE_OPENGL)
    list(APPEND GODOT_DRIVER_SOURCES
        ${CMAKE_SOURCE_DIR}/drivers/gl_context
        ${CMAKE_SOURCE_DIR}/drivers/gles3
        ${CMAKE_SOURCE_DIR}/drivers/egl
    )
endif()
if(FEATURE_SDL)
    list(APPEND GODOT_DRIVER_SOURCES ${CMAKE_SOURCE_DIR}/drivers/sdl)
endif()

set(GODOT_DRIVER_CPP "")
foreach(dir IN LISTS GODOT_DRIVER_SOURCES)
    if(IS_DIRECTORY ${dir})
        file(GLOB_RECURSE driver_src ${dir}/*.cpp)
        list(APPEND GODOT_DRIVER_CPP ${driver_src})
    elseif(EXISTS ${dir})
        list(APPEND GODOT_DRIVER_CPP ${dir})
    endif()
endforeach()
if(FEATURE_DYNAMIC_LOADING)
    file(GLOB DRIVER_WRAP_SOURCES
        ${CMAKE_SOURCE_DIR}/drivers/alsa/*-so_wrap.c
        ${CMAKE_SOURCE_DIR}/drivers/pulseaudio/*-so_wrap.c)
    list(APPEND GODOT_DRIVER_CPP ${DRIVER_WRAP_SOURCES})
endif()

set(GODOT_PLATFORM_SOURCES ${CMAKE_SOURCE_DIR}/platform/linuxbsd/godot_linuxbsd.cpp
                          ${CMAKE_SOURCE_DIR}/platform/linuxbsd/os_linuxbsd.cpp
                          ${CMAKE_SOURCE_DIR}/platform/linuxbsd/crash_handler_linuxbsd.cpp
                          ${CMAKE_SOURCE_DIR}/platform/linuxbsd/freedesktop_portal_desktop.cpp
                          ${CMAKE_SOURCE_DIR}/platform/linuxbsd/freedesktop_screensaver.cpp
                          ${CMAKE_SOURCE_DIR}/platform/linuxbsd/freedesktop_at_spi_monitor.cpp)
if(FEATURE_SPEECHD)
    list(APPEND GODOT_PLATFORM_SOURCES ${CMAKE_SOURCE_DIR}/platform/linuxbsd/tts_linux.cpp)
    if(FEATURE_DYNAMIC_LOADING)
        list(APPEND GODOT_PLATFORM_SOURCES ${CMAKE_SOURCE_DIR}/platform/linuxbsd/speechd-so_wrap.c)
    endif()
endif()
if(FEATURE_DYNAMIC_LOADING)
    file(GLOB LINUXBSD_WRAP_SOURCES ${CMAKE_SOURCE_DIR}/platform/linuxbsd/*-so_wrap.c)
    list(APPEND GODOT_PLATFORM_SOURCES ${LINUXBSD_WRAP_SOURCES})
endif()
if(FEATURE_X11)
    file(GLOB X11_SOURCES ${CMAKE_SOURCE_DIR}/platform/linuxbsd/x11/*.cpp)
    if(NOT FEATURE_VULKAN)
        list(FILTER X11_SOURCES EXCLUDE REGEX "rendering_context_driver_vulkan")
    endif()
    if(NOT FEATURE_OPENGL)
        list(FILTER X11_SOURCES EXCLUDE REGEX "gl_manager|detect_prime")
    endif()
    list(APPEND GODOT_PLATFORM_SOURCES ${X11_SOURCES})
    if(FEATURE_DYNAMIC_LOADING)
        file(GLOB X11_WRAP_SOURCES ${CMAKE_SOURCE_DIR}/platform/linuxbsd/x11/dynwrappers/*-so_wrap.c)
        list(APPEND GODOT_PLATFORM_SOURCES ${X11_WRAP_SOURCES})
    endif()
endif()
if(FEATURE_WAYLAND)
    file(GLOB WAYLAND_SOURCES ${CMAKE_SOURCE_DIR}/platform/linuxbsd/wayland/*.cpp)
    if(NOT FEATURE_VULKAN)
        list(FILTER WAYLAND_SOURCES EXCLUDE REGEX "rendering_context_driver_vulkan")
    endif()
    if(NOT FEATURE_OPENGL)
        list(FILTER WAYLAND_SOURCES EXCLUDE REGEX "egl_manager")
    endif()
    list(APPEND GODOT_PLATFORM_SOURCES ${WAYLAND_SOURCES})
    if(FEATURE_DYNAMIC_LOADING)
        file(GLOB WAYLAND_WRAP_SOURCES ${CMAKE_SOURCE_DIR}/platform/linuxbsd/wayland/dynwrappers/*-so_wrap.c)
        if(NOT FEATURE_LIBDECOR)
            list(FILTER WAYLAND_WRAP_SOURCES EXCLUDE REGEX "libdecor")
        endif()
        list(APPEND GODOT_PLATFORM_SOURCES ${WAYLAND_WRAP_SOURCES})
    endif()
    file(GLOB WAYLAND_GEN_C ${GEN_DIR}/platform/linuxbsd/wayland/protocol/*.gen.c)
    list(APPEND GODOT_PLATFORM_SOURCES ${WAYLAND_GEN_C})
endif()
if(FEATURE_EDITOR)
    file(GLOB LINUXBSD_EXPORT_SOURCES ${CMAKE_SOURCE_DIR}/platform/linuxbsd/export/*.cpp)
    list(APPEND GODOT_PLATFORM_SOURCES ${LINUXBSD_EXPORT_SOURCES})
endif()

if(FEATURE_EDITOR)
    file(GLOB_RECURSE GODOT_EDITOR_SOURCES CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/editor/*.cpp)
    list(FILTER GODOT_EDITOR_SOURCES EXCLUDE REGEX "shader_baker_export_plugin_platform_(d3d12|metal)\\.cpp$")
    if(NOT FEATURE_VULKAN)
        list(FILTER GODOT_EDITOR_SOURCES EXCLUDE REGEX "shader_baker_export_plugin_platform_vulkan\\.cpp$")
    endif()
endif()

set(GODOT_MODULE_SOURCES "")
foreach(module IN LISTS GODOT_ENABLED_MODULES)
    if(module STREQUAL "camera")
        set(module_src
            ${CMAKE_SOURCE_DIR}/modules/camera/register_types.cpp
            ${CMAKE_SOURCE_DIR}/modules/camera/camera_linux.cpp
            ${CMAKE_SOURCE_DIR}/modules/camera/camera_feed_linux.cpp
            ${CMAKE_SOURCE_DIR}/modules/camera/buffer_decoder.cpp
        )
        if(FEATURE_EDITOR)
            file(GLOB_RECURSE camera_editor CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/modules/camera/editor/*.cpp)
            list(APPEND module_src ${camera_editor})
        endif()
    else()
        file(GLOB_RECURSE module_src CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/modules/${module}/*.cpp)
    endif()
    list(FILTER module_src EXCLUDE REGEX "/tests/")
    # text_server_adv and text_server_fb ship an identical copy of this file.
    if(module STREQUAL "text_server_fb" AND FEATURE_MODULE_TEXT_SERVER_ADV)
        list(FILTER module_src EXCLUDE REGEX "/thorvg_svg_in_ot\\.cpp$")
    endif()
    # Owned by tp_icu; never compile it from the module glob.
    if(module STREQUAL "text_server_adv")
        list(FILTER module_src EXCLUDE REGEX "/icu_data/icudata_stub\\.cpp$")
    endif()
    if(NOT FEATURE_EDITOR)
        list(FILTER module_src EXCLUDE REGEX "modules/${module}/editor/")
    endif()
    list(APPEND GODOT_MODULE_SOURCES ${module_src})
endforeach()

# ---------------------------------------------------------------------------
# Engine libraries
# ---------------------------------------------------------------------------
godot_engine_library(godot_core
    SOURCES
        ${GODOT_CORE_SOURCES}
        ${GEN_DIR}/core/version_hash.gen.cpp
        ${GEN_DIR}/core/script_encryption_key.gen.cpp
        ${GEN_DIR}/core/input/default_controller_mappings.gen.cpp
        ${GEN_DIR}/modules/register_module_types.gen.cpp
)
godot_engine_library(godot_servers SOURCES ${GODOT_SERVERS_SOURCES})
godot_engine_library(godot_scene SOURCES ${GODOT_SCENE_SOURCES})
godot_engine_library(godot_drivers SOURCES ${GODOT_DRIVER_CPP})
godot_engine_library(godot_platform SOURCES ${GODOT_PLATFORM_SOURCES})
godot_engine_library(godot_modules SOURCES ${GODOT_MODULE_SOURCES})
if(FEATURE_EDITOR)
    godot_engine_library(godot_editor
        SOURCES
            ${GODOT_EDITOR_SOURCES}
            ${GEN_DIR}/editor/export/register_exporters.gen.cpp
            ${GEN_DIR}/platform/register_platform_apis.gen.cpp
            ${GEN_DIR}/editor/translations/editor_translations.gen.cpp
            ${GEN_DIR}/editor/translations/extractable_translations.gen.cpp
            ${GEN_DIR}/editor/translations/property_translations.gen.cpp
            ${GEN_DIR}/editor/translations/doc_translations.gen.cpp
        PUBLIC_INCLUDES ${CMAKE_SOURCE_DIR}/editor ${CMAKE_SOURCE_DIR}/editor/export
    )
endif()

# ---------------------------------------------------------------------------
# Executable
# ---------------------------------------------------------------------------
add_executable(godot ${GODOT_MAIN_SOURCES})

set_source_files_properties(
    ${GEN_DIR}/core/version_hash.gen.cpp
    ${GEN_DIR}/core/script_encryption_key.gen.cpp
    ${GEN_DIR}/core/input/default_controller_mappings.gen.cpp
    ${GEN_DIR}/modules/register_module_types.gen.cpp
    ${GEN_DIR}/editor/export/register_exporters.gen.cpp
    ${GEN_DIR}/platform/register_platform_apis.gen.cpp
    ${GEN_DIR}/editor/translations/editor_translations.gen.cpp
    ${GEN_DIR}/editor/translations/extractable_translations.gen.cpp
    ${GEN_DIR}/editor/translations/property_translations.gen.cpp
    ${GEN_DIR}/editor/translations/doc_translations.gen.cpp
    ${WAYLAND_GEN_C}
    PROPERTIES GENERATED TRUE
)

target_link_options(godot PRIVATE -pie -Wl,-z,relro -Wl,-z,now)

# The engine areas and the bundled libraries have circular dependencies on each
# other, so they have to be resolved as one group.
target_link_libraries(godot PRIVATE
    "-Wl,--start-group" ${GODOT_ENGINE_LIBS} ${THIRDPARTY_LIBS} "-Wl,--end-group"
    Threads::Threads
    ${CMAKE_DL_LIBS}
    m
)
if(FEATURE_WAYLAND)
    target_link_libraries(godot PRIVATE rt)
endif()

set_target_properties(godot PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)
# CMake injects -pie by default; SCons passes no PIE flag, so the toolchain
# default (non-PIE here) is what we want to reproduce.
target_link_options(godot PRIVATE -no-pie)

# ---------------------------------------------------------------------------
# Configuration summary
# ---------------------------------------------------------------------------
get_cmake_property(cache_variables CACHE_VARIABLES)
set(FEATURES_ON "")
set(FEATURES_OFF "")
foreach(var IN LISTS cache_variables)
    if(var MATCHES "^FEATURE_" AND NOT var MATCHES "^FEATURE_MODULE_")
        if(${var})
            list(APPEND FEATURES_ON ${var})
        else()
            list(APPEND FEATURES_OFF ${var})
        endif()
    endif()
endforeach()
list(SORT FEATURES_ON)
list(SORT FEATURES_OFF)
list(LENGTH FEATURES_ON FEATURES_ON_COUNT)
list(LENGTH FEATURES_OFF FEATURES_OFF_COUNT)

set(MODULES_ON "")
set(MODULES_OFF "")
foreach(module IN LISTS GODOT_MODULE_LIST)
    string(TOUPPER ${module} MODULE_UPPER)
    if(FEATURE_MODULE_${MODULE_UPPER})
        list(APPEND MODULES_ON ${module})
    else()
        list(APPEND MODULES_OFF ${module})
    endif()
endforeach()
list(LENGTH MODULES_ON MODULES_ON_COUNT)
list(LENGTH MODULES_OFF MODULES_OFF_COUNT)

message(STATUS "")
message(STATUS "${CMAKE_SYSTEM_NAME} ${CMAKE_SYSTEM_PROCESSOR} | ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION} | ${CMAKE_BUILD_TYPE}")
message(STATUS "Features ON (${FEATURES_ON_COUNT})")
foreach(feature IN LISTS FEATURES_ON)
    message(STATUS "    + ${feature}")
endforeach()
message(STATUS "Features OFF (${FEATURES_OFF_COUNT})")
foreach(feature IN LISTS FEATURES_OFF)
    message(STATUS "    - ${feature}")
endforeach()
list(LENGTH GODOT_MODULE_LIST MODULES_TOTAL)
message(STATUS "Modules ON (${MODULES_ON_COUNT}/${MODULES_TOTAL})")
foreach(module IN LISTS MODULES_ON)
    message(STATUS "    + ${module}")
endforeach()
message(STATUS "Modules OFF")
foreach(module IN LISTS MODULES_OFF)
    message(STATUS "    - ${module}")
endforeach()
message(STATUS "")

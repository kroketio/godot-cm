#!/usr/bin/env python3
"""Generate every `*.gen.*` source Godot needs, for the CMake build.

Mirrors the SCons builders, writing into a generated tree that is added to the
include path next to the source root.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


class Node:
    """Minimal stand-in for a SCons file node."""

    def __init__(self, path):
        self.path = str(path)
        self.name = os.path.basename(self.path)
        self.abspath = os.path.abspath(self.path)

    def __str__(self):
        return self.path

    def read(self):
        with open(self.path, encoding="utf-8") as f:
            return f.read()


class Value:
    """A node whose "content" is an in-memory Python object."""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "<value>"

    def read(self):
        return self.value


class Env:
    def NoCache(self, *args):
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--editor", action="store_true")
    ap.add_argument("--gles3", action="store_true")
    ap.add_argument("--wayland", action="store_true")
    ap.add_argument("--icu-data", action="store_true")
    ap.add_argument("--editor-splash", action="store_true")
    ap.add_argument("--module-icons", action="append", default=[])
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    os.chdir(root)
    sys.path.insert(0, str(root))

    for sub in (
        ".",
        "core",
        "core/extension",
        "core/input",
        "core/object",
        "main",
        "scene/theme",
        "scene/theme/icons",
        "servers/rendering/storage",
        "editor",
        "editor/icons",
        "editor/themes",
        "modules/text_server_adv",
        "platform",
    ):
        sys.path.insert(0, str(root / sub))

    import core_builders
    import default_theme_builders
    import default_theme_icons_builders
    import editor_builders
    import editor_icons_builders
    import editor_theme_builders
    import gles3_builders
    import glsl_builders
    import input_builders
    import main_builders
    import make_interface_dumper
    import make_interface_header
    import make_ltc_lut
    import make_virtuals
    import make_wrappers
    import methods
    import platform_builders
    import template_builders
    import text_server_adv_builders

    env = Env()

    def emit(rel, fn, sources):
        rel = Path(rel)
        if rel.is_absolute():
            rel = rel.relative_to(root)
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        wrapped = [s if isinstance(s, (Node, Value)) else Node(s) for s in sources]
        fn([Node(target)], wrapped, env)

    def write(rel, content):
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with methods.generated_wrapper(str(target)) as f:
            f.write(content)

    def glsl(rel_in, kind):
        src = root / rel_in
        tgt = out / rel_in.with_suffix(".glsl.gen.h")
        tgt.parent.mkdir(parents=True, exist_ok=True)
        if kind == "rd":
            glsl_builders.build_rd_header(str(tgt), str(src))
        elif kind == "raw":
            glsl_builders.build_raw_header(str(tgt), str(src))
        else:
            gles3_builders.build_gles3_header(str(tgt), str(src))

    # ---------------------------------------------------------------- core
    write("core/disabled_classes.gen.h", "")

    version_info = methods.get_version_info("", silent=True)
    emit("core/version_generated.gen.h", core_builders.version_info_builder, [Value(version_info)])
    emit("core/version_hash.gen.cpp", core_builders.version_hash_builder, [Value(methods.get_git_info())])

    key = os.environ.get("SCRIPT_AES256_ENCRYPTION_KEY") or os.environ.get("GODOT_SCRIPT_ENCRYPTION_KEY")
    emit("core/script_encryption_key.gen.cpp", core_builders.encryption_key_builder, [Value(key)])

    emit(
        "core/io/certs_compressed.gen.h",
        core_builders.make_certs_header,
        [root / "thirdparty/certs/ca-bundle.crt", Value(True), Value("")],
    )
    emit("core/authors.gen.h", core_builders.make_authors_header, [root / "AUTHORS.md"])
    emit("core/donors.gen.h", core_builders.make_donors_header, [root / "DONORS.md"])
    emit(
        "core/license.gen.h",
        core_builders.make_license_header,
        [root / "COPYRIGHT.txt", root / "LICENSE.txt"],
    )

    emit(
        "core/input/default_controller_mappings.gen.cpp",
        input_builders.make_default_controller_mappings,
        [
            root / "core/input/gamecontrollerdb.txt",
            root / "core/input/godotcontrollerdb.txt",
        ],
    )

    emit("core/object/gdvirtual.gen.h", make_virtuals.run, [])
    write("core/profiling/profiling.gen.h", "")
    emit("core/extension/ext_wrappers.gen.h", make_wrappers.run, [])
    gdext_json = root / "core/extension/gdextension_interface.json"
    emit("core/extension/gdextension_interface_dump.gen.h", make_interface_dumper.run, [gdext_json])
    emit("core/extension/gdextension_interface.gen.h", make_interface_header.run, [gdext_json])

    # ---------------------------------------------------------------- main
    emit("main/splash.gen.h", main_builders.make_splash, [root / "main/splash.png"])
    emit("main/app_icon.gen.h", main_builders.make_app_icon, [root / "main/app_icon.png"])
    if args.editor_splash and (root / "main/splash_editor.png").exists():
        emit("main/splash_editor.gen.h", main_builders.make_splash_editor, [root / "main/splash_editor.png"])

    # ------------------------------------------------------------- scene
    emit(
        "scene/theme/default_font.gen.h",
        default_theme_builders.make_fonts_header,
        [root / "thirdparty/fonts/OpenSans_SemiBold.woff2"],
    )
    theme_icons = sorted(glob(root, "scene/theme/icons/*.svg"))
    if args.editor:
        theme_icons += sorted(glob(root, "scene/theme/icons/debug_icons/*.svg"))
    emit("scene/theme/default_theme_icons.gen.h", default_theme_icons_builders.make_default_theme_icons_action, theme_icons)

    # ----------------------------------------------------------- servers
    for shader in sorted(glob(root, "servers/rendering/**/*.glsl")):
        rel = shader.relative_to(root)
        glsl(rel, "raw" if rel.stem.endswith("_inc") else "rd")

    emit("servers/rendering/storage/ltc_lut.gen.h", make_ltc_lut.run, [
        root / "servers/rendering/storage/make_ltc_lut.py",
        root / "servers/rendering/storage/ltc/ltc_lut1.dds",
        root / "servers/rendering/storage/ltc/ltc_lut2.dds",
    ])
    emit("servers/rendering/renderer_rd/effects/smaa_area_tex.gen.h", smaa_area_tex, [root / "thirdparty/smaa/AreaTex.png"])
    emit("servers/rendering/renderer_rd/effects/smaa_search_tex.gen.h", smaa_search_tex, [root / "thirdparty/smaa/SearchTex.png"])

    for shader in sorted(glob(root, "modules/*/*.glsl")):
        glsl(shader.relative_to(root), "raw")

    # ---------------------------------------------------------- drivers
    if args.gles3:
        named = [
            "canvas.glsl", "feed.glsl", "scene.glsl", "sky.glsl", "canvas_occlusion.glsl",
            "canvas_sdf.glsl", "particles.glsl", "particles_copy.glsl", "skeleton.glsl", "tex_blit.glsl",
        ]
        for name in named:
            glsl(Path("drivers/gles3/shaders") / name, "gles3")
        for shader in sorted(glob(root, "drivers/gles3/shaders/effects/*.glsl")):
            if shader.stem.endswith("_inc"):
                continue
            glsl(shader.relative_to(root), "gles3")

    # ------------------------------------------------------------- icu4c
    if args.icu_data:
        emit(
            "thirdparty/icu4c/icudata.gen.h",
            text_server_adv_builders.make_icu_data,
            [root / "thirdparty/icu4c/icudt_godot.dat"],
        )

    # ------------------------------------------------------------- editor
    if args.editor:
        fonts = []
        for pattern in ("*.ttf", "*.otf", "*.woff", "*.woff2"):
            fonts += glob(root, f"thirdparty/fonts/{pattern}")
        emit("editor/themes/builtin_fonts.gen.h", editor_theme_builders.make_fonts_header, sorted(fonts))

        icons = sorted(glob(root, "editor/icons/*.svg"))
        for module_icons in args.module_icons:
            icons += sorted(glob(root, f"{module_icons}/*.svg"))
        emit("editor/themes/editor_icons.gen.h", editor_icons_builders.make_editor_icons_action, icons)

        # Documentation and translations are stubbed out: no doc generation.
        write("editor/doc/doc_data_class_path.gen.h", """
struct _DocDataClassPath {
\tconst char *name;
\tconst char *path;
};

inline constexpr int _doc_data_class_path_count = 0;
inline constexpr _DocDataClassPath _doc_data_class_paths[1] = {
\t{ nullptr, nullptr },
};
""")
        write("editor/doc/doc_data_compressed.gen.h", """
inline constexpr const char *_doc_data_hash = "";
inline constexpr int _doc_data_compressed_size = 0;
inline constexpr int _doc_data_uncompressed_size = 0;
inline constexpr const unsigned char _doc_data_compressed[] = { 0 };
""")

        emit("editor/export/register_exporters.gen.cpp", editor_builders.register_exporters_builder, [Value(["linuxbsd"])])

        for svg in sorted(glob(root, "platform/linuxbsd/export/*.svg")):
            emit(svg.with_name(svg.stem + "_svg.gen.h"), platform_builders.export_icon_builder, [svg])

        emit("platform/register_platform_apis.gen.cpp", platform_builders.register_platform_apis_builder, [Value([])])

        templates = sorted(glob(root, "modules/gdscript/editor/script_templates/*/*.gd"))
        emit("modules/gdscript/editor/script_templates/templates.gen.h", template_builders.make_templates, templates)

        for category in ("editor", "extractable", "property", "doc"):
            write(f"editor/translations/{category}_translations.gen.h", f"""
#ifndef EDITOR_TRANSLATION_LIST
#define EDITOR_TRANSLATION_LIST

struct EditorTranslationList {{
\tconst char *lang;
\tint comp_size;
\tint uncomp_size;
\tconst unsigned char *data;
}};

#endif

extern const EditorTranslationList _{category}_translations[];
""")
            write(f"editor/translations/{category}_translations.gen.cpp", f"""
#include "editor/translations/{category}_translations.gen.h"

const EditorTranslationList _{category}_translations[] = {{
\t{{ nullptr, 0, 0, nullptr }},
}};
""")

    # ------------------------------------------------------------ wayland
    if args.wayland:
        generate_wayland(root, out)

    return 0


def glob(root: Path, pattern: str):
    return [p for p in root.glob(pattern) if p.is_file()]


def smaa_area_tex(target, source, env):
    import methods

    buffer = open(str(source[0]), "rb").read()
    format_buffer = methods.format_buffer

    with methods.generated_wrapper(str(target[0])) as file:
        file.write(f"""\
#define AREATEX_WIDTH 160
#define AREATEX_HEIGHT 560
#define AREATEX_PITCH (AREATEX_WIDTH * 2)
#define AREATEX_SIZE (AREATEX_HEIGHT * AREATEX_PITCH)

inline constexpr const unsigned char area_tex_png[] = {{
\t{format_buffer(buffer, 1)}
}};
""")


def smaa_search_tex(target, source, env):
    import methods

    buffer = open(str(source[0]), "rb").read()
    format_buffer = methods.format_buffer

    with methods.generated_wrapper(str(target[0])) as file:
        file.write(f"""\
#define SEARCHTEX_WIDTH 64
#define SEARCHTEX_HEIGHT 16
#define SEARCHTEX_PITCH SEARCHTEX_WIDTH
#define SEARCHTEX_SIZE (SEARCHTEX_HEIGHT * SEARCHTEX_PITCH)

inline constexpr const unsigned char search_tex_png[] = {{
\t{format_buffer(buffer, 1)}
}};
""")


WAYLAND_PROTOCOLS = [
    ("wayland", "thirdparty/wayland/protocol/wayland.xml"),
    ("tablet", "thirdparty/wayland-protocols/stable/tablet/tablet-v2.xml"),
    ("viewporter", "thirdparty/wayland-protocols/stable/viewporter/viewporter.xml"),
    ("xdg_shell", "thirdparty/wayland-protocols/stable/xdg-shell/xdg-shell.xml"),
    ("color_management", "thirdparty/wayland-protocols/staging/color-management/color-management-v1.xml"),
    ("cursor_shape", "thirdparty/wayland-protocols/staging/cursor-shape/cursor-shape-v1.xml"),
    ("fractional_scale", "thirdparty/wayland-protocols/staging/fractional-scale/fractional-scale-v1.xml"),
    ("xdg_activation", "thirdparty/wayland-protocols/staging/xdg-activation/xdg-activation-v1.xml"),
    ("xdg_system_bell", "thirdparty/wayland-protocols/staging/xdg-system-bell/xdg-system-bell-v1.xml"),
    ("xdg_toplevel_icon", "thirdparty/wayland-protocols/staging/xdg-toplevel-icon/xdg-toplevel-icon-v1.xml"),
    ("pointer_warp", "thirdparty/wayland-protocols/staging/pointer-warp/pointer-warp-v1.xml"),
    ("idle_inhibit", "thirdparty/wayland-protocols/unstable/idle-inhibit/idle-inhibit-unstable-v1.xml"),
    ("pointer_constraints", "thirdparty/wayland-protocols/unstable/pointer-constraints/pointer-constraints-unstable-v1.xml"),
    ("pointer_gestures", "thirdparty/wayland-protocols/unstable/pointer-gestures/pointer-gestures-unstable-v1.xml"),
    ("primary_selection", "thirdparty/wayland-protocols/unstable/primary-selection/primary-selection-unstable-v1.xml"),
    ("relative_pointer", "thirdparty/wayland-protocols/unstable/relative-pointer/relative-pointer-unstable-v1.xml"),
    ("text_input", "thirdparty/wayland-protocols/unstable/text-input/text-input-unstable-v3.xml"),
    ("xdg_decoration", "thirdparty/wayland-protocols/unstable/xdg-decoration/xdg-decoration-unstable-v1.xml"),
    ("xdg_foreign_v1", "thirdparty/wayland-protocols/unstable/xdg-foreign/xdg-foreign-unstable-v1.xml"),
    ("xdg_foreign_v2", "thirdparty/wayland-protocols/unstable/xdg-foreign/xdg-foreign-unstable-v2.xml"),
    ("linux_dmabuf_v1", "thirdparty/wayland-protocols/stable/linux-dmabuf/linux-dmabuf-v1.xml"),
    (
        "linux_explicit_synchronization_unstable_v1",
        "thirdparty/wayland-protocols/unstable/linux-explicit-synchronization/linux-explicit-synchronization-unstable-v1.xml",
    ),
    ("fifo_v1", "thirdparty/wayland-protocols/staging/fifo/fifo-v1.xml"),
    ("commit_timing_v1", "thirdparty/wayland-protocols/staging/commit-timing/commit-timing-v1.xml"),
    ("linux_drm_syncobj_v1", "thirdparty/wayland-protocols/staging/linux-drm-syncobj/linux-drm-syncobj-v1.xml"),
    ("tearing_control_v1", "thirdparty/wayland-protocols/staging/tearing-control/tearing-control-v1.xml"),
    ("wayland-drm", "thirdparty/wayland-protocols/mesa/wayland-drm.xml"),
    ("godot_embedding_compositor", "platform/linuxbsd/wayland/godot-embedding-compositor.xml"),
]


def generate_wayland(root: Path, out: Path) -> None:
    import subprocess

    scanner = shutil.which("wayland-scanner")
    if not scanner:
        print("wayland-scanner not found, Wayland support unavailable", file=sys.stderr)
        raise SystemExit(1)

    proto_dir = out / "platform/linuxbsd/wayland/protocol"
    proto_dir.mkdir(parents=True, exist_ok=True)

    wrap_out = out / "platform/linuxbsd/wayland/dynwrappers"
    wrap_out.mkdir(parents=True, exist_ok=True)
    for header in sorted((root / "platform/linuxbsd/wayland/dynwrappers").glob("*.h")):
        shutil.copyfile(header, wrap_out / header.name)

    def scan(name, xml, mode, replace):
        src = root / xml
        with open(src, "rb") as fin:
            with open(proto_dir / name, "wb") as fout:
                proc = subprocess.run([scanner, "-c", mode], stdin=fin, stdout=fout, stderr=subprocess.PIPE)
                if proc.returncode != 0:
                    sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
                    raise SystemExit(proc.returncode)
        data = (proto_dir / name).read_text(encoding="utf-8")
        for needle, repl in replace:
            data = data.replace(needle, repl)
        (proto_dir / name).write_text(data, encoding="utf-8")

    header_sub = [("wayland-client-core.h", "../dynwrappers/wayland-client-core-so_wrap.h")]
    code_sub = [("wayland-util.h", "../dynwrappers/wayland-client-core-so_wrap.h")]

    for name, xml in WAYLAND_PROTOCOLS:
        scan(f"{name}.gen.h", xml, "client-header", header_sub)
        scan(f"{name}.gen.c", xml, "private-code", code_sub)


if __name__ == "__main__":
    sys.exit(main())

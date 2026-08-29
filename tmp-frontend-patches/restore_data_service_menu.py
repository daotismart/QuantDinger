#!/usr/bin/env python3
"""Restore Data Service admin menu entry lost from Vite fe-compat build."""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path("/database/ai/QuantDinger/ops/hotfixes")
FE = ROOT / "fe-compat"
ASSETS = FE / "assets"
HTML_SRC = ROOT / "data-service.html"
HTML_DST = FE / "data-service.html"
INDEX = ASSETS / "index-DyNteJsg.js"
ZH = ASSETS / "zh-CN-DeugDBb3.js"
EN_CANDIDATES = sorted(ASSETS.glob("en-US*.js"))
CHUNK = ASSETS / "data-service-menu-Bx7kQ2pA.js"

CHUNK_JS = (
    'import{N as n}from"./index-DyNteJsg.js";'
    'const s={name:"DataService"};'
    "const m=function(e){"
    'return e("div",{staticClass:"data-service-embed",'
    'staticStyle:{height:"calc(100vh - 112px)",minHeight:"640px",padding:"0 4px"}},['
    'e("iframe",{attrs:{src:"/data-service.html",title:"数据服务"},'
    'staticStyle:{width:"100%",height:"100%",border:"0",borderRadius:"12px",background:"transparent"}})'
    "])};"
    "const o=[];"
    'const a=n(s,m,o,!1,null,"ds-embed-01");'
    "const t=a.exports;export{t as default};\n"
)


def backup(path: Path, stamp: str) -> None:
    if path.exists():
        shutil.copy2(path, str(path) + f".bak.pre-data-service.{stamp}")


def patch_index(js: str) -> str:
    if 'path:"/data-service"' in js and "DataService" in js:
        print("index already has data-service route")
        return js

    m = re.search(r"topAdminPaths\(\)\{return\[[^\]]+\]\}", js)
    if not m:
        raise SystemExit("topAdminPaths not found")
    old_paths = m.group(0)
    if '"/data-service"' not in old_paths:
        # insert before /settings
        if '"/settings"]}' not in old_paths:
            raise SystemExit(f"unexpected topAdminPaths: {old_paths}")
        new_paths = old_paths.replace('"/settings"]}', '"/data-service","/settings"]}')
        js = js.replace(old_paths, new_paths, 1)
        print("updated topAdminPaths", new_paths)

    m = re.search(
        r'\{path:"/settings",name:"Settings",component:\(\)=>f\(\(\)=>import\("\./[^"]+"\)',
        js,
    )
    if not m:
        raise SystemExit("settings route not found")
    settings_prefix = m.group(0)
    data_route = (
        '{path:"/data-service",name:"DataService",'
        'component:()=>f(()=>import("./data-service-menu-Bx7kQ2pA.js"),void 0,import.meta.url),'
        'meta:{title:"menu.dashboard.dataService",keepAlive:!1,icon:"database",permission:["admin"]}},'
        + settings_prefix
    )
    js = js.replace(settings_prefix, data_route, 1)
    if 'path:"/data-service"' not in js:
        raise SystemExit("route insert failed")
    print("inserted /data-service route before /settings")
    return js


def patch_locale(text: str, *, label: str) -> str:
    if "menu.dashboard.dataService" in text:
        return text
    for needle in (
        '"menu.dashboard":"仪表盘"',
        '"menu.dashboard":"Dashboard"',
        '"menu.settings":"系统设置"',
        '"menu.settings":"Settings"',
        '"menu.dashboard"',
        '"menu.settings"',
    ):
        if needle in text:
            return text.replace(
                needle,
                f'"menu.dashboard.dataService":"{label}",{needle}',
                1,
            )
    raise SystemExit("locale insert needle not found")


def main() -> None:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    if not HTML_SRC.exists():
        raise SystemExit(f"missing {HTML_SRC}")
    if not INDEX.exists():
        raise SystemExit(f"missing {INDEX}")

    backup(INDEX, stamp)
    backup(ZH, stamp)
    if HTML_DST.exists():
        backup(HTML_DST, stamp)

    shutil.copy2(HTML_SRC, HTML_DST)
    CHUNK.write_text(CHUNK_JS)
    print("wrote", CHUNK.name, HTML_DST.name)

    INDEX.write_text(patch_index(INDEX.read_text()))
    ZH.write_text(patch_locale(ZH.read_text(), label="数据服务"))
    print("patched zh-CN")

    for en in EN_CANDIDATES:
        text = en.read_text()
        if "menu.settings" not in text and "menu.dashboard" not in text:
            continue
        if "menu.dashboard.dataService" in text:
            print("en already", en.name)
            continue
        backup(en, stamp)
        try:
            en.write_text(patch_locale(text, label="Data Service"))
            print("patched", en.name)
        except SystemExit as exc:
            print("skip", en.name, exc)

    js = INDEX.read_text()
    zh = ZH.read_text()
    print(
        "verify",
        "route=",
        js.count('path:"/data-service"'),
        "paths=",
        js.count("/data-service"),
        "i18n=",
        "menu.dashboard.dataService" in zh,
        "html=",
        HTML_DST.exists(),
        "chunk=",
        CHUNK.exists(),
    )


if __name__ == "__main__":
    main()

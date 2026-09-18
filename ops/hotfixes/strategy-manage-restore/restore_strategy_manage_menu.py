#!/usr/bin/env python3
"""Restore Strategy Management menu + inventory page on production fe-compat."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path("/database/ai/QuantDinger/ops/hotfixes")
FE = ROOT / "fe-compat"
ASSETS = FE / "assets"
SRC_DIR = ROOT / "strategy-manage-restore"
HTML_SRC = SRC_DIR / "strategy-manage.html"
HTML_DST = FE / "strategy-manage.html"
CHUNK = ASSETS / "strategy-manage-menu-Rk4mP8wQ.js"

OLD_STRATEGY_GROUP = (
    '{name:"MenuGroupStrategy",path:"/menu-group/strategy-lab",'
    'title:this.$t("menu.group.strategyLab")||"Strategy Lab",icon:"experiment",'
    'paths:["/strategy-ide"],singleAsItem:!0}'
)
NEW_STRATEGY_GROUP = (
    '{name:"MenuGroupStrategy",path:"/menu-group/strategy-manage",'
    'title:this.$t("menu.group.strategyManage")||"Strategy Management",icon:"experiment",'
    'paths:["/strategy-manage","/strategy-ide","/backtest-center"],singleAsItem:!1}'
)
OLD_BACKTEST_GROUP = (
    '{name:"MenuGroupBacktest",path:"/menu-group/backtest-center",'
    'title:this.$t("menu.dashboard.backtestCenter")||"Backtest Center",icon:"bar-chart",'
    'paths:["/backtest-center"],singleAsItem:!0},'
)


def find_index() -> Path:
    for path in sorted(ASSETS.glob("index-*.js"), key=lambda p: p.stat().st_size, reverse=True):
        if ".bak." in path.name:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if 'name:"MenuGroupStrategy"' in text and 'path:"/strategy-ide"' in text:
            return path
    raise SystemExit("main index chunk with MenuGroupStrategy not found")


def find_zh() -> Path | None:
    for path in ASSETS.glob("zh-CN*.js"):
        if ".bak." in path.name:
            continue
        return path
    return None


def backup(path: Path, stamp: str) -> None:
    if path.exists():
        shutil.copy2(path, str(path) + f".bak.pre-strategy-manage.{stamp}")


def patch_index(js: str, index_name: str) -> str:
    if 'path:"/strategy-manage"' in js and "menu-group/strategy-manage" in js:
        print("index already has strategy-manage menu/route")
        return js

    if OLD_STRATEGY_GROUP not in js:
        raise SystemExit("MenuGroupStrategy block not found (already patched or unexpected build)")
    js = js.replace(OLD_STRATEGY_GROUP, NEW_STRATEGY_GROUP, 1)
    print("updated MenuGroupStrategy -> Strategy Management")

    if OLD_BACKTEST_GROUP in js:
        js = js.replace(OLD_BACKTEST_GROUP, "", 1)
        print("removed standalone MenuGroupBacktest (nested under Strategy Management)")

    if 'path:"/strategy-manage"' not in js:
        needle = '{path:"/strategy-ide",name:"StrategyIDE",component:()=>f(()=>import("./'
        idx = js.find(needle)
        if idx < 0:
            raise SystemExit("strategy-ide route not found")
        route = (
            '{path:"/strategy-manage",name:"StrategyManage",'
            f'component:()=>f(()=>import("./{CHUNK.name}"),void 0,import.meta.url),'
            'meta:{title:"menu.dashboard.strategyManage",keepAlive:!1,icon:"appstore",permission:["dashboard"]}},'
        )
        js = js[:idx] + route + js[idx:]
        print("inserted /strategy-manage route")
    return js


def patch_zh(js: str) -> str:
    if '"menu.group.strategyManage"' not in js:
        anchor = '"menu.group.strategyLab"'
        if anchor in js:
            js = js.replace(anchor, '"menu.group.strategyManage":"策略管理",' + anchor, 1)
            print("added zh menu.group.strategyManage")
        else:
            anchor2 = '"menu.dashboard.strategyIde"'
            if anchor2 not in js:
                raise SystemExit("zh-CN locale anchors missing")
            js = js.replace(
                anchor2,
                '"menu.group.strategyManage":"策略管理","menu.dashboard.strategyManage":"策略清单",' + anchor2,
                1,
            )
            print("added zh strategyManage keys near strategyIde")
    if '"menu.dashboard.strategyManage"' not in js:
        anchor = '"menu.dashboard.strategyIde"'
        if anchor not in js:
            raise SystemExit("menu.dashboard.strategyIde missing in zh-CN")
        js = js.replace(anchor, '"menu.dashboard.strategyManage":"策略清单",' + anchor, 1)
        print("added zh menu.dashboard.strategyManage")
    return js


def main() -> None:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    if not HTML_SRC.exists():
        raise SystemExit(f"missing {HTML_SRC}")

    index_path = find_index()
    zh_path = find_zh()
    print("index=", index_path.name, "zh=", zh_path.name if zh_path else None)

    backup(index_path, stamp)
    if zh_path:
        backup(zh_path, stamp)
    if HTML_DST.exists():
        backup(HTML_DST, stamp)

    shutil.copy2(HTML_SRC, HTML_DST)
    print("wrote", HTML_DST)

    chunk_js = (
        f'import{{N as n}}from"./{index_path.name}";'
        'const s={name:"StrategyManage"};'
        "const m=function(e){"
        'return e("div",{staticClass:"strategy-manage-embed",'
        'staticStyle:{height:"calc(100vh - 112px)",minHeight:"640px",padding:"0 4px"}},['
        'e("iframe",{attrs:{src:"/strategy-manage.html",title:"策略管理"},'
        'staticStyle:{width:"100%",height:"100%",border:"0",borderRadius:"12px",background:"transparent"}})'
        "])};"
        "const o=[];"
        'const a=n(s,m,o,!1,null,"sm-embed-01");'
        "const t=a.exports;export{t as default};\n"
    )
    CHUNK.write_text(chunk_js, encoding="utf-8")
    print("wrote", CHUNK)

    index_path.write_text(
        patch_index(index_path.read_text(encoding="utf-8", errors="replace"), index_path.name),
        encoding="utf-8",
    )
    if zh_path:
        zh_path.write_text(
            patch_zh(zh_path.read_text(encoding="utf-8", errors="replace")),
            encoding="utf-8",
        )

    compose = Path("/database/ai/QuantDinger/docker-compose.hotfix.yml")
    volume = (
        "      - ./ops/hotfixes/fe-compat/strategy-manage.html:"
        "/usr/share/nginx/html/strategy-manage.html:ro\n"
    )
    if compose.exists():
        text = compose.read_text(encoding="utf-8")
        if "strategy-manage.html" not in text:
            needle = (
                "      - ./ops/hotfixes/fe-compat/assets:"
                "/usr/share/nginx/html/assets:ro\n"
            )
            if needle not in text:
                raise SystemExit(
                    "frontend assets volume not found; add a bind-mount for "
                    "ops/hotfixes/fe-compat/strategy-manage.html yourself, "
                    "then recreate quantdinger-frontend"
                )
            backup(compose, stamp)
            compose.write_text(text.replace(needle, needle + volume, 1), encoding="utf-8")
            print("mounted strategy-manage.html in", compose)
        else:
            print("compose already mounts strategy-manage.html")
    print("recreate frontend so nginx serves /strategy-manage.html, then hard-refresh.")
    print("done. Open 策略管理 → 策略清单.")


if __name__ == "__main__":
    main()

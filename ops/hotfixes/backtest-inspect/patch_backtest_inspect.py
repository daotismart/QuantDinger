#!/usr/bin/env python3
"""Embed process visualization under the Backtest Center result panel."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path("/database/ai/QuantDinger/ops/hotfixes")
FE = ROOT / "fe-compat"
ASSETS = FE / "assets"
SRC = ROOT / "backtest-inspect" / "backtest-inspect.html"
DST = FE / "backtest-inspect.html"
COMPOSE = Path("/database/ai/QuantDinger/docker-compose.hotfix.yml")

OLD = (
    't.activeResult?t.mode==="portfolio"?e("portfolio-result",'
    '{attrs:{result:t.result,"is-dark":t.isDarkTheme}})'
)
NEW = (
    't.activeResult?t.mode==="portfolio"?e("div",{staticClass:"qd-bt-process-viz"},['
    'e("portfolio-result",{attrs:{result:t.result,"is-dark":t.isDarkTheme}}),'
    't.selectedRun?e("iframe",{attrs:{'
    'src:"/backtest-inspect.html?embed=1&runId="+String(t.selectedRun.id||t.selectedRun.runId||""),'
    'title:"决策过程 / 成交 / 持仓"},'
    'staticStyle:{width:"100%",minHeight:"980px",height:"980px",border:"0",display:"block",'
    'marginTop:"12px",borderRadius:"12px",background:"transparent"}}):t._e()'
    '],1)'
)


def find_index() -> Path:
    for path in sorted(ASSETS.glob("index-*.js"), key=lambda item: item.stat().st_size):
        if ".bak." in path.name:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if OLD in text or (NEW[:40] in text and "backtest-inspect.html" in text):
            return path
    raise SystemExit("backtest-center result chunk not found")


def main() -> None:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    if not SRC.exists():
        raise SystemExit(f"missing {SRC}")
    index_path = find_index()
    shutil.copy2(SRC, DST)
    print("wrote", DST)
    text = index_path.read_text(encoding="utf-8", errors="replace")
    if "backtest-inspect.html" in text and NEW[:48] in text:
        print("index already patched")
    elif OLD not in text:
        raise SystemExit(f"portfolio-result mount not found in {index_path.name}")
    else:
        shutil.copy2(index_path, str(index_path) + f".bak.pre-bt-inspect.{stamp}")
        index_path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
        print("patched", index_path.name)

    if COMPOSE.exists():
        compose = COMPOSE.read_text(encoding="utf-8")
        volume = (
            "      - ./ops/hotfixes/fe-compat/backtest-inspect.html:"
            "/usr/share/nginx/html/backtest-inspect.html:ro\n"
        )
        if "backtest-inspect.html" not in compose:
            needle = (
                "      - ./ops/hotfixes/fe-compat/assets:"
                "/usr/share/nginx/html/assets:ro\n"
            )
            if needle not in compose:
                raise SystemExit("frontend assets volume not found")
            shutil.copy2(COMPOSE, str(COMPOSE) + f".bak.pre-bt-inspect.{stamp}")
            COMPOSE.write_text(compose.replace(needle, needle + volume, 1), encoding="utf-8")
            print("mounted backtest-inspect.html in compose")
        else:
            print("compose already mounts backtest-inspect.html")
    print("recreate frontend with --no-deps, then hard-refresh Backtest Center.")


if __name__ == "__main__":
    main()

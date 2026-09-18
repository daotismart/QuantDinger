#!/usr/bin/env python3
"""Hotfix production ETF options bundle: top capital summary cards."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

JS_PATH = Path(
    "/database/ai/QuantDinger/ops/hotfixes/fe-compat/assets/etf-derivatives-h8andvEF.js"
)
ZH_PATH = Path(
    "/database/ai/QuantDinger/ops/hotfixes/fe-compat/assets/zh-CN-DeugDBb3.js"
)


def main() -> None:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    shutil.copy2(JS_PATH, str(JS_PATH) + f".bak.pre-capital-summary.{stamp}")
    shutil.copy2(ZH_PATH, str(ZH_PATH) + f".bak.pre-capital-summary.{stamp}")

    js = JS_PATH.read_text()
    zh = ZH_PATH.read_text()

    if "capitalSummaryMetrics" in js and "fda-metrics-capital" in js:
        print("already patched")
        return

    needle = (
        '},{key:"maxPain",label:"Max Pain",display:this.fmt(t&&t.strike)}]},aiMarket(){'
    )
    if needle not in js:
        idx = js.find('key:"maxPain"')
        raise SystemExit(f"needle1 not found near: {js[idx:idx+160]!r}")

    insert_fn = (
        '},{key:"maxPain",label:"Max Pain",display:this.fmt(t&&t.strike)}]},'
        "capitalSummaryMetrics(){"
        "const e=(this.optionsData&&this.optionsData.capital_curve)||{},"
        "a=e.total||{},"
        "l=a.margin_total!=null?a.margin_total:a.margin_short_total;"
        "return["
        '{key:"margin",label:this.$t("marketComposite.futures.options.totalMargin"),'
        "display:this.fmtMoney(l)},"
        '{key:"premium",label:this.$t("marketComposite.futures.options.premiumTotal"),'
        "display:this.fmtMoney(a.premium_total)},"
        '{key:"timeValue",label:this.$t("marketComposite.futures.options.timeValueTotal"),'
        "display:this.fmtMoney(a.time_value_total)}"
        "]},"
        "aiMarket(){"
    )
    js = js.replace(needle, insert_fn, 1)

    tpl_needle = (
        't._l(t.gexMetrics,function(a){return e("div",{key:a.key,staticClass:"fda-metric"},'
        '[e("span",[t._v(t._s(a.label))]),e("strong",[t._v(t._s(a.display))])])}),0),'
        'e("div",{staticClass:"fda-charts fda-charts-options"}'
    )
    if tpl_needle not in js:
        idx = js.find("t._l(t.gexMetrics")
        raise SystemExit(f"tpl needle not found near: {js[idx:idx+280]!r}")

    tpl_new = (
        't._l(t.gexMetrics,function(a){return e("div",{key:a.key,staticClass:"fda-metric"},'
        '[e("span",[t._v(t._s(a.label))]),e("strong",[t._v(t._s(a.display))])])}),0),'
        'e("div",{staticClass:"fda-metrics fda-metrics-capital",'
        '"data-testid":"etf-options-capital-summary"},'
        't._l(t.capitalSummaryMetrics,function(a){return e("div",'
        '{key:a.key,staticClass:"fda-metric"},'
        '[e("span",[t._v(t._s(a.label))]),e("strong",[t._v(t._s(a.display))])])}),0),'
        'e("div",{staticClass:"fda-charts fda-charts-options"}'
    )
    js = js.replace(tpl_needle, tpl_new, 1)

    css_mark = ".fda-metrics-gex{margin-bottom:16px}"
    if css_mark in js:
        js = js.replace(
            css_mark,
            ".fda-metrics-gex{margin-bottom:12px}.fda-metrics-capital{margin-bottom:16px}",
            1,
        )

    if "fmtMoney" not in js:
        raise SystemExit("fmtMoney missing in prod bundle")

    JS_PATH.write_text(js)
    print(
        "js patched",
        js.count("capitalSummaryMetrics"),
        js.count("fda-metrics-capital"),
        js.count("totalMargin"),
    )

    if "totalMargin" not in zh:
        key = '"marketComposite.futures.options.marginTotal":"空头保证金"'
        if key in zh:
            zh = zh.replace(
                key,
                key + ',"marketComposite.futures.options.totalMargin":"总保证金"',
                1,
            )
        else:
            key2 = '"marketComposite.futures.options.premiumTotal":"权利金"'
            if key2 not in zh:
                raise SystemExit("zh keys not found")
            zh = zh.replace(
                key2,
                key2 + ',"marketComposite.futures.options.totalMargin":"总保证金"',
                1,
            )
        ZH_PATH.write_text(zh)
        print("zh patched")
    else:
        print("zh already has totalMargin")


if __name__ == "__main__":
    main()

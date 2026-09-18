#!/usr/bin/env python3
"""Hotfix production ETF page: show constituent holdings table."""
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
EN_CANDIDATES = sorted(
    Path("/database/ai/QuantDinger/ops/hotfixes/fe-compat/assets").glob("en-US*.js")
)


def patch_js(js: str) -> str:
    if "etfHoldings()" in js and "fda-constituents" in js:
        return js

    cards_end = (
        'label:this.$t("marketComposite.etf.metrics.premiumRate"),'
        'display:s.premium_rate!=null?`${this.fmt(s.premium_rate,2)}%`:"-"}]},'
        "optionMonths(){"
    )
    if cards_end not in js:
        raise SystemExit("etfMetricCards -> optionMonths needle not found")

    computeds = (
        'label:this.$t("marketComposite.etf.metrics.premiumRate"),'
        'display:s.premium_rate!=null?`${this.fmt(s.premium_rate,2)}%`:"-"}]},'
        "etfHoldings(){const e=this.etfSpot;return e.holdings||e.holdings_sample||[]},"
        "etfHoldingsMeta(){const e=this.etfSpot,t=[];"
        "return e.holdings_count&&t.push(`${e.holdings_count}${this.$t(\"marketComposite.etf.metrics.constituentCountUnit\")}`),"
        "e.holdings_quarter&&t.push(e.holdings_quarter),"
        "e.pe_coverage&&t.push(`${this.$t(\"marketComposite.etf.metrics.peCoverage\")}: ${e.pe_coverage}`),"
        "e.margin_coverage&&t.push(`${this.$t(\"marketComposite.etf.metrics.marginCoverage\")}: ${e.margin_coverage}`),"
        "t.join(\" · \")},"
        "etfHoldingsPagination(){return{pageSize:20,showSizeChanger:!0,"
        'pageSizeOptions:["20","50","100"],showTotal:e=>`${e}`}},'
        "etfConstituentColumns(){return["
        '{title:this.$t("marketComposite.etf.metrics.colCode"),dataIndex:"code",width:92},'
        '{title:this.$t("marketComposite.etf.metrics.colName"),dataIndex:"name",ellipsis:!0},'
        '{title:this.$t("marketComposite.etf.metrics.colWeight"),dataIndex:"weight_pct",width:88,'
        'customRender:e=>null!=e?`${this.fmt(e,2)}%`:"-"},'
        '{title:this.$t("marketComposite.etf.metrics.colHoldingValue"),dataIndex:"market_value",'
        "customRender:e=>this.fmtMoney(e)},"
        '{title:this.$t("marketComposite.etf.metrics.colShares"),dataIndex:"shares",'
        "customRender:e=>this.fmtCompact(e)},"
        '{title:this.$t("marketComposite.etf.metrics.colNetProfit"),dataIndex:"net_profit",'
        "customRender:e=>this.fmtMoney(e)},"
        '{title:this.$t("marketComposite.etf.metrics.colMarketCap"),dataIndex:"market_cap",'
        "customRender:e=>this.fmtMoney(e)},"
        '{title:this.$t("marketComposite.etf.metrics.colPe"),dataIndex:"pe_ratio",width:72,'
        'customRender:e=>null!=e?this.fmt(e,2):"-"},'
        '{title:this.$t("marketComposite.etf.metrics.colProfitMargin"),dataIndex:"profit_margin",width:96,'
        'customRender:e=>null!=e?`${this.fmt(e,2)}%`:"-"}'
        "]},"
        "optionMonths(){"
    )
    js = js.replace(cards_end, computeds, 1)

    tpl_old = (
        't.etfMetricsNote?e("p",{staticClass:"fda-muted fda-etf-note"},'
        "[t._v(t._s(t.etfMetricsNote))]):t._e(),"
        'e("div",{staticClass:"fda-section"},'
        '[e("h3",[t._v(t._s(t.$t("marketComposite.futures.spot.analysis")))])'
    )
    if tpl_old not in js:
        raise SystemExit("template insert needle not found")

    tpl_new = (
        't.etfMetricsNote?e("p",{staticClass:"fda-muted fda-etf-note"},'
        "[t._v(t._s(t.etfMetricsNote))]):t._e(),"
        't.etfHoldings.length?e("div",{staticClass:"fda-section fda-constituents"},['
        'e("h3",[t._v(t._s(t.$t("marketComposite.etf.metrics.constituentList")))]),'
        't.etfHoldingsMeta?e("p",{staticClass:"fda-muted"},[t._v(t._s(t.etfHoldingsMeta))]):t._e(),'
        'e("a-table",{staticClass:"fda-table",attrs:{size:"small",'
        "pagination:t.etfHoldingsPagination,columns:t.etfConstituentColumns,"
        '"data-source":t.etfHoldings,"row-key":"code"}})'
        "],1):t._e(),"
        'e("div",{staticClass:"fda-section"},'
        '[e("h3",[t._v(t._s(t.$t("marketComposite.futures.spot.analysis")))])'
    )
    js = js.replace(tpl_old, tpl_new, 1)

    if "etfHoldings()" not in js or "fda-constituents" not in js:
        raise SystemExit("patch verification failed")
    return js


def patch_locale(text: str, *, col_name: str) -> str:
    if "marketComposite.etf.metrics.colName" in text:
        return text
    for key, label in (
        ('"marketComposite.etf.metrics.colCode":"代码"', col_name),
        ('"marketComposite.etf.metrics.colCode":"Code"', col_name),
    ):
        if key in text:
            return text.replace(
                key,
                key + f',"marketComposite.etf.metrics.colName":"{label}"',
                1,
            )
    raise SystemExit("locale colCode needle not found")


def main() -> None:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    js = JS_PATH.read_text()
    if "etfHoldings()" in js and "fda-constituents" in js:
        print("js already patched")
    else:
        shutil.copy2(JS_PATH, str(JS_PATH) + f".bak.pre-constituents.{stamp}")
        JS_PATH.write_text(patch_js(js))
        js2 = JS_PATH.read_text()
        print("js patched", js2.count("etfHoldings"), js2.count("fda-constituents"))

    zh = ZH_PATH.read_text()
    if "marketComposite.etf.metrics.colName" not in zh:
        shutil.copy2(ZH_PATH, str(ZH_PATH) + f".bak.pre-constituents.{stamp}")
        ZH_PATH.write_text(patch_locale(zh, col_name="名称"))
        print("zh patched colName")
    else:
        print("zh already has colName")

    for en in EN_CANDIDATES:
        text = en.read_text()
        if "marketComposite.etf.metrics.colCode" not in text:
            continue
        if "marketComposite.etf.metrics.colName" in text:
            print("en already", en.name)
            continue
        shutil.copy2(en, str(en) + f".bak.pre-constituents.{stamp}")
        en.write_text(patch_locale(text, col_name="Name"))
        print("en patched", en.name)


if __name__ == "__main__":
    main()

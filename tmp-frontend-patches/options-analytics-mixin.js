/**
 * Shared ETF / futures options analytics charts and history playback UI.
 * Components mix this in and may override optionsHistoryExtraParams().
 */
import {
  buildCallPutGexTrendSeries,
  buildCallPutStackedGexSeries as createCallPutStackedGexSeries
} from './gex-chart-series'

export default {
  data () {
    return {
      historyBars: 60,
      historyInterval: 'day',
      historyLevelsSeries: [],
      historyNearMonthIvKlines: [],
      historyNearMonthMaxPainSeries: []
    }
  },
  computed: {
    isGexHistory () {
      return this.historyKey === 'options.gex'
    },
    isGexCallPutHistory () {
      return this.historyKey === 'options.gexCallPut'
    },
    isGexFamilyHistory () {
      return this.isGexHistory || this.isGexCallPutHistory
    },
    isIvHistory () {
      return this.historyKey === 'options.iv'
    },
    isMaxPainHistory () {
      return this.historyKey === 'options.maxPain'
    },
    isCapitalHistory () {
      return this.historyKey === 'options.capital'
    },
    isSurfaceHistory () {
      return ['options.iv', 'options.oi', 'options.tv', 'options.maxPain'].includes(this.historyKey)
    },
    isPlaybackHistory () {
      return this.isGexFamilyHistory || this.isCapitalHistory || this.isSurfaceHistory
    },
    capitalSummaryMetrics () {
      const curve = (this.optionsData && this.optionsData.capital_curve) || {}
      const total = curve.total || {}
      const margin =
        total.margin_total != null
          ? total.margin_total
          : total.margin_short_total
      return [
        {
          key: 'margin',
          label: this.$t('marketComposite.futures.options.totalMargin'),
          display: this.fmtMoney(margin)
        },
        {
          key: 'premium',
          label: this.$t('marketComposite.futures.options.premiumTotal'),
          display: this.fmtMoney(total.premium_total)
        },
        {
          key: 'timeValue',
          label: this.$t('marketComposite.futures.options.timeValueTotal'),
          display: this.fmtMoney(total.time_value_total)
        }
      ]
    }
  },
  methods: {
    optionsHistoryExtraParams () {
      return {}
    },
    optionsHistoryRoot () {
      return this.selectedRoot
    },
    formatCurrentPrice (value) {
      return this.fmt(value, 3, true)
    },
    optionsCurrentPrice (panel = this.optionsData) {
      if (!panel) return null
      const summary = panel.gex_summary || {}
      const price = panel.current_price || panel.underlying || summary.underlying
      const n = Number(price)
      return Number.isFinite(n) ? n : null
    },
    buildOptionsMarkDefs (summary, price) {
      return [
        { name: 'Price', value: price, color: '#1890ff', width: 2 },
        { name: 'Flip', value: summary.flip, color: '#faad14', width: 1.5 },
        { name: 'Call Wall', value: summary.call_wall, color: '#52c41a', width: 1.5 },
        { name: 'Put Wall', value: summary.put_wall, color: '#ff4d4f', width: 1.5 },
        { name: 'Pin', value: summary.pin, color: '#722ed1', width: 1.5 }
      ]
    },
    buildCurrentPriceValueAxisMarkData (price) {
      const n = Number(price)
      if (!Number.isFinite(n)) return []
      const text = this.formatCurrentPrice(n)
      return [{
        name: 'Price',
        xAxis: n,
        lineStyle: { color: '#1890ff', width: 2, type: 'solid' },
        label: {
          show: true,
          formatter: `Price ${text}`,
          color: '#1890ff',
          position: 'insideEndTop',
          lineHeight: 14,
          fontSize: 11,
          backgroundColor: 'rgba(0,0,0,0.45)',
          padding: [2, 4],
          borderRadius: 2
        }
      }]
    },
    appendValueAxisPriceMark (series, price, preferSeriesName) {
      const entries = this.buildCurrentPriceValueAxisMarkData(price)
      if (!entries.length || !Array.isArray(series) || !series.length) return series
      const host = series.find(item => preferSeriesName && item.name === preferSeriesName)
        || series.find(item => item.markLine)
        || series.find(item => (item.data || []).length)
        || series[0]
      const markLine = host.markLine || { symbol: 'none', data: [] }
      const data = Array.isArray(markLine.data) ? [...markLine.data] : []
      data.push(...entries)
      host.markLine = { ...markLine, symbol: 'none', data }
      return series
    },
    fmtMoney (value) {
      if (value === null || value === undefined || value === '') return '-'
      const n = Number(value)
      if (!Number.isFinite(n)) return '-'
      const abs = Math.abs(n)
      if (abs >= 1e8) return `${(n / 1e8).toFixed(2)}亿元`
      if (abs >= 1e4) return `${(n / 1e4).toFixed(2)}万元`
      return `${this.fmt(n, 0)}元`
    },
    fmtCompact (value) {
      if (value === null || value === undefined || value === '') return '-'
      const n = Number(value)
      if (!Number.isFinite(n)) return '-'
      const abs = Math.abs(n)
      if (abs >= 1e8) return `${(n / 1e8).toFixed(2)}亿`
      if (abs >= 1e4) return `${(n / 1e4).toFixed(2)}万`
      return this.fmt(n, 0)
    },
    formatStrikeMark (value) {
      const n = Number(value)
      if (!Number.isFinite(n)) return ''
      const abs = Math.abs(n)
      let s
      if (abs >= 100) s = n.toFixed(0)
      else if (abs >= 10) s = n.toFixed(1)
      else s = n.toFixed(3)
      return s.replace(/\.0+$/, '').replace(/(\.[0-9]*?)0+$/, '$1').replace(/\.$/, '')
    },
    buildStrikeMarkLineData (markDefs, strikes) {
      const groups = new Map()
      markDefs.forEach((item) => {
        if (item.value == null) return
        const x = this.nearestStrikeLabel(strikes, item.value)
        if (x == null) return
        const key = String(x)
        if (!groups.has(key)) groups.set(key, [])
        groups.get(key).push(item)
      })
      const out = []
      let groupIdx = 0
      groups.forEach((items, x) => {
        const primary = items.find(i => i.name === 'Price') || items[0]
        const lines = items.map((item) => {
          const raw = item.value != null ? item.value : x
          const v = item.name === 'Price'
            ? this.formatCurrentPrice(raw)
            : this.formatStrikeMark(raw)
          return v && v !== '-' ? `${item.name} ${v}` : item.name
        })
        out.push({
          name: items.map(i => i.name).join('/'),
          xAxis: String(x),
          lineStyle: {
            color: primary.color,
            width: primary.name === 'Price' ? 2 : (primary.width || 1.5),
            type: primary.name === 'Price' ? 'solid' : 'dashed'
          },
          label: {
            show: true,
            formatter: lines.join('\n'),
            color: primary.color,
            position: 'end',
            distance: 8 + groupIdx * 4,
            lineHeight: 14,
            fontSize: 11,
            backgroundColor: 'rgba(0,0,0,0.45)',
            padding: [2, 4],
            borderRadius: 2
          }
        })
        groupIdx += 1
      })
      return out
    },
    buildStackedGexSeries (monthSeries, points, palette, buildMarks) {
      const months = (monthSeries || []).filter(ms => (ms.gex_distribution || []).length)
      if (months.length > 1) {
        const strikeNums = new Set()
        months.forEach(ms => {
          (ms.gex_distribution || []).forEach(p => {
            const k = Number(p.strike)
            if (Number.isFinite(k)) strikeNums.add(k)
          })
        })
        const strikes = Array.from(strikeNums).sort((a, b) => a - b).map(k => String(k))
        const series = months.map((ms, idx) => {
          const byK = new Map(
            (ms.gex_distribution || []).map(p => [String(Number(p.strike)), Number(p.net_gex) || 0])
          )
          return {
            name: String(ms.month || `M${idx + 1}`),
            type: 'bar',
            stack: 'gex',
            barMaxWidth: 18,
            data: strikes.map(k => byK.get(k) || 0),
            itemStyle: { color: palette[idx % palette.length], opacity: 0.78 }
          }
        })
        const aggByK = new Map(
          (points || []).map(p => [String(Number(p.strike)), Number(p.net_gex) || 0])
        )
        const netData = strikes.map((k, i) => {
          if (aggByK.has(k)) return aggByK.get(k)
          return series.reduce((sum, ser) => sum + (Number(ser.data[i]) || 0), 0)
        })
        series.push({
          name: 'Net GEX',
          type: 'line',
          data: netData,
          itemStyle: { color: '#fa8c16' },
          markLine: { symbol: 'none', data: buildMarks(strikes) }
        })
        return { strikes, series }
      }
      const strikes = (points || []).map(p => String(p.strike))
      return {
        strikes,
        series: [
          { name: 'Call GEX', type: 'bar', stack: 'gex', barMaxWidth: 18, data: (points || []).map(p => p.call_gex), itemStyle: { color: '#52c41a', opacity: 0.55 } },
          { name: 'Put GEX', type: 'bar', stack: 'gex', barMaxWidth: 18, data: (points || []).map(p => p.put_gex), itemStyle: { color: '#ff4d4f', opacity: 0.55 } },
          { name: 'Net GEX', type: 'line', data: (points || []).map(p => p.net_gex), itemStyle: { color: '#fa8c16' }, markLine: { symbol: 'none', data: buildMarks(strikes) } }
        ]
      }
    },
    applyCallPutGexChart (chart, monthSeries, points, buildMarks) {
      if (!chart) return
      const stacked = createCallPutStackedGexSeries(monthSeries, points, buildMarks)
      chart.setOption({
        ...this.baseChartOption(),
        legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
        grid: { left: 56, right: 36, top: 56, bottom: 40 },
        xAxis: { type: 'category', data: stacked.strikes, axisLabel: { color: this.chartText } },
        yAxis: { type: 'value', name: 'GEX', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
        series: stacked.series
      }, true)
    },
    renderCapitalCurveChart (chart, capitalCurve, xKey = 'month') {
      if (!chart) return
      const points = (capitalCurve && capitalCurve.points) || []
      const labels = points.map(p => p[xKey] || p.date || p.ts || '')
      const splitLine = { lineStyle: { color: this.chartGrid, type: 'dashed' } }
      chart.setOption({
        ...this.baseChartOption(),
        legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
        grid: { left: 56, right: 56, top: 48, bottom: 40 },
        tooltip: {
          trigger: 'axis',
          confine: true,
          formatter: (params) => {
            const rows = Array.isArray(params) ? params : [params]
            if (!rows.length) return ''
            const head = rows[0].axisValueLabel || rows[0].name || ''
            const lines = rows.map((row) => {
              const val = row.data
              const name = String(row.seriesName || '')
              const isRatio = name.includes('/') || name.toLowerCase().includes('long')
              const text = val == null || val === ''
                ? '-'
                : (isRatio ? Number(val).toFixed(4) : this.fmtCompact(val))
              return `${row.marker}${row.seriesName}: ${text}`
            })
            return [head].concat(lines).join('<br/>')
          }
        },
        xAxis: { type: 'category', data: labels, axisLabel: { color: this.chartText, hideOverlap: true } },
        yAxis: [
          {
            type: 'value',
            name: this.$t('marketComposite.futures.options.capitalAmountAxis'),
            scale: true,
            splitLine
          },
          {
            type: 'value',
            name: this.$t('marketComposite.futures.options.capitalRatioAxis'),
            scale: true,
            min: 0,
            axisLabel: { formatter: v => Number(v).toFixed(2) },
            splitLine: { show: false }
          }
        ],
        series: [
          {
            name: this.$t('marketComposite.futures.options.marginShortTotal'),
            type: 'line',
            showSymbol: true,
            symbolSize: 4,
            data: points.map(p => p.margin_short_total != null ? p.margin_short_total : p.margin_total),
            itemStyle: { color: '#ef4444' },
            lineStyle: { width: 2 }
          },
          {
            name: this.$t('marketComposite.futures.options.premiumTotal'),
            type: 'line',
            showSymbol: true,
            symbolSize: 4,
            data: points.map(p => p.premium_total),
            itemStyle: { color: '#2563eb' },
            lineStyle: { width: 2 }
          },
          {
            name: this.$t('marketComposite.futures.options.timeValueTotal'),
            type: 'line',
            showSymbol: false,
            data: points.map(p => p.time_value_total),
            itemStyle: { color: '#f97316' },
            lineStyle: { type: 'dotted', width: 2 }
          },
          {
            name: this.$t('marketComposite.futures.options.intrinsicTotal'),
            type: 'line',
            showSymbol: false,
            data: points.map(p => p.intrinsic_total),
            itemStyle: { color: '#22c55e' },
            lineStyle: { type: 'dotted', width: 2 }
          },
          {
            name: this.$t('marketComposite.futures.options.longShortRatio'),
            type: 'line',
            yAxisIndex: 1,
            showSymbol: true,
            symbolSize: 4,
            data: points.map(p => p.long_short_ratio != null ? p.long_short_ratio : p.premium_margin_ratio),
            itemStyle: { color: '#7c3aed' },
            lineStyle: { type: 'dashed', width: 2 }
          }
        ]
      }, true)
    },
    optionsHistoryTitleFor (chartKey) {
      const titleMap = {
        'options.capital': this.$t('marketComposite.futures.options.capitalCurve'),
        'options.gex': this.$t('marketComposite.futures.options.gexDist'),
        'options.gexCallPut': this.$t('marketComposite.futures.options.gexCallPutDist')
      }
      return titleMap[chartKey] || chartKey
    },
    optionsHistoryChartKey () {
      return this.isGexCallPutHistory ? 'options.gex' : this.historyKey
    },
    openOptionsHistory (chartKey) {
      this.historyKey = chartKey
      this.historyTitle = `${this.$t('marketComposite.futures.history')} · ${this.optionsHistoryTitleFor(chartKey)}`
      this.historySlices = []
      this.historySliceIndex = 0
      this.historyVisible = true
      this.$nextTick(() => this.loadOptionsHistory())
    },
    closeOptionsHistory () {
      this.historyVisible = false
      this.historySlices = []
      this.historySliceIndex = 0
      this.historyLevelsSeries = []
      this.historyNearMonthIvKlines = []
      this.historyNearMonthMaxPainSeries = []
      ;['historyChart', 'historyLevelsChart'].forEach(key => {
        if (this.charts[key]) {
          this.charts[key].dispose()
          delete this.charts[key]
        }
      })
    },
    onOptionsHistorySliceChange () {
      this.renderOptionsHistorySlice()
      if (this.isIvHistory) this.renderNearMonthIvKlines()
      if (this.isMaxPainHistory) this.renderNearMonthMaxPainTrend()
    },
    async loadOptionsHistory () {
      if (!this.optionsHistoryRoot() || !this.historyKey) return
      this.historyLoading = true
      try {
        const params = {
          root: this.optionsHistoryRoot(),
          chart: this.optionsHistoryChartKey(),
          month: this.selectedMonth || 'all',
          ...this.optionsHistoryExtraParams()
        }
        if (this.isPlaybackHistory) {
          params.bars = this.historyBars
          params.interval = this.historyInterval
          params.frequency = this.historyInterval
        } else {
          params.days = this.historyDays
          params.frequency = this.historyFrequency
        }
        const res = await this.$optionsHistoryApi(params)
        const data = (res && res.data) || {}
        this.historyNote = data.note || ''
        this.historyLevelsSeries = data.levels_series || []
        this.historyNearMonthIvKlines = data.near_month_iv_klines || []
        this.historyNearMonthMaxPainSeries = data.near_month_max_pain_series || []
        if (data.mode === 'slices' || data.mode === 'gex_playback') {
          this.historySlices = data.slices || []
          this.historySliceIndex = Math.max(this.historySlices.length - 1, 0)
          this.$nextTick(() => {
            this.renderOptionsHistorySlice()
            if (this.isGexHistory) this.renderGexLevelsHistory()
            if (this.isGexCallPutHistory) this.renderCallPutGexTrend()
            if (this.isIvHistory) this.renderNearMonthIvKlines()
            if (this.isMaxPainHistory) this.renderNearMonthMaxPainTrend()
          })
        } else {
          this.historySlices = []
          this.$nextTick(() => this.renderOptionsHistoryChart(data))
        }
      } catch (e) {
        this.$message.error((e && e.message) || this.$t('marketComposite.futures.loadFailed'))
      } finally {
        this.historyLoading = false
      }
    },
    renderGexLevelsHistory () {
      const chart = this.ensureChart('historyLevelsChart')
      if (!chart) return
      const rows = this.historyLevelsSeries || []
      const labels = rows.map(r => r.label || r.ts)
      const slice = this.historySlices[this.historySliceIndex] || {}
      const markLabel = slice.label || slice.ts || labels[this.historySliceIndex]
      chart.setOption({
        ...this.baseChartOption(),
        legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
        grid: { left: 56, right: 24, top: 48, bottom: 48 },
        xAxis: { type: 'category', data: labels, axisLabel: { color: this.chartText, hideOverlap: true } },
        yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
        series: [
          {
            name: 'Underlying',
            type: 'line',
            showSymbol: false,
            data: rows.map(r => r.underlying),
            itemStyle: { color: '#1890ff' },
            lineStyle: { width: 2 },
            markLine: labels.length && markLabel
              ? {
                symbol: 'none',
                label: { formatter: String(markLabel), color: this.chartText },
                lineStyle: { color: '#8c8c8c', type: 'dashed' },
                data: [{ xAxis: markLabel }]
              }
              : undefined
          },
          { name: 'Call Wall', type: 'line', showSymbol: false, data: rows.map(r => r.call_wall), itemStyle: { color: '#52c41a' } },
          { name: 'Put Wall', type: 'line', showSymbol: false, data: rows.map(r => r.put_wall), itemStyle: { color: '#ff4d4f' } },
          { name: 'Gamma Flip', type: 'line', showSymbol: false, data: rows.map(r => r.flip), itemStyle: { color: '#faad14' }, lineStyle: { type: 'dashed' } },
          { name: 'Gamma Pin', type: 'line', showSymbol: false, data: rows.map(r => r.pin), itemStyle: { color: '#722ed1' }, lineStyle: { type: 'dotted' } }
        ]
      }, true)
    },
    renderNearMonthIvKlines () {
      const chart = this.ensureChart('historyLevelsChart')
      if (!chart) return
      const rows = this.historyNearMonthIvKlines || []
      const labels = rows.map(r => r.label || r.ts)
      const candles = rows.map(r => {
        if (r.open == null || r.close == null) return [null, null, null, null]
        return [r.open, r.close, r.low, r.high]
      })
      const slice = this.historySlices[this.historySliceIndex] || {}
      const markLabel = slice.label || slice.ts || labels[this.historySliceIndex]
      const month = (rows.find(r => r.month) || {}).month
      chart.setOption({
        ...this.baseChartOption(),
        legend: { top: 0, textStyle: { color: this.chartText } },
        grid: { left: 56, right: 24, top: 48, bottom: 48 },
        xAxis: { type: 'category', data: labels, axisLabel: { color: this.chartText, hideOverlap: true } },
        yAxis: {
          type: 'value',
          scale: true,
          axisLabel: { formatter: v => `${(Number(v) * 100).toFixed(1)}%`, color: this.chartText },
          splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' },
          formatter: params => {
            const item = Array.isArray(params) ? params[0] : params
            if (!item || !item.data) return ''
            const [o, c, l, h] = item.data
            if (o == null) return `${item.axisValue}<br/>--`
            const pct = v => `${(Number(v) * 100).toFixed(2)}%`
            return [
              item.axisValue,
              `O ${pct(o)} / C ${pct(c)}`,
              `L ${pct(l)} / H ${pct(h)}`
            ].join('<br/>')
          }
        },
        series: [
          {
            name: month
              ? `${this.$t('marketComposite.futures.options.nearMonthIvKline')} (${month})`
              : this.$t('marketComposite.futures.options.nearMonthIvKline'),
            type: 'candlestick',
            data: candles,
            itemStyle: {
              color: '#ef5350',
              color0: '#26a69a',
              borderColor: '#ef5350',
              borderColor0: '#26a69a'
            },
            markLine: labels.length && markLabel
              ? {
                symbol: 'none',
                label: { formatter: String(markLabel), color: this.chartText },
                lineStyle: { color: '#8c8c8c', type: 'dashed' },
                data: [{ xAxis: markLabel }]
              }
              : undefined
          }
        ]
      }, true)
    },
    renderNearMonthMaxPainTrend () {
      const chart = this.ensureChart('historyLevelsChart')
      if (!chart) return
      const rows = this.historyNearMonthMaxPainSeries || []
      const labels = rows.map(r => r.label || r.ts)
      const slice = this.historySlices[this.historySliceIndex] || {}
      const markLabel = slice.label || slice.ts || labels[this.historySliceIndex]
      const month = (rows.find(r => r.month) || {}).month
      const maxPainName = month
        ? `${this.$t('marketComposite.futures.options.nearMonthMaxPain')} (${month})`
        : this.$t('marketComposite.futures.options.nearMonthMaxPain')
      chart.setOption({
        ...this.baseChartOption(),
        legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
        grid: { left: 56, right: 24, top: 48, bottom: 48 },
        xAxis: { type: 'category', data: labels, axisLabel: { color: this.chartText, hideOverlap: true } },
        yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
        tooltip: { trigger: 'axis', confine: true },
        series: [
          {
            name: this.$t('marketComposite.futures.options.underlyingPrice'),
            type: 'line',
            showSymbol: false,
            data: rows.map(r => r.underlying),
            itemStyle: { color: '#1890ff' },
            lineStyle: { width: 2 },
            markLine: labels.length && markLabel
              ? {
                symbol: 'none',
                label: { formatter: String(markLabel), color: this.chartText },
                lineStyle: { color: '#8c8c8c', type: 'dashed' },
                data: [{ xAxis: markLabel }]
              }
              : undefined
          },
          {
            name: maxPainName,
            type: 'line',
            showSymbol: false,
            data: rows.map(r => r.max_pain),
            itemStyle: { color: '#fa8c16' },
            lineStyle: { width: 2 }
          }
        ]
      }, true)
      this.$nextTick(() => chart.resize())
    },
    renderCallPutGexTrend () {
      const chart = this.ensureChart('historyLevelsChart')
      if (!chart) return
      const { labels, series } = buildCallPutGexTrendSeries(this.historySlices || [])
      const slice = this.historySlices[this.historySliceIndex] || {}
      const markLabel = slice.label || slice.ts || labels[this.historySliceIndex]
      const marked = series.map((item, idx) => {
        if (idx !== series.length - 1) return item
        return {
          ...item,
          markLine: labels.length && markLabel
            ? {
              symbol: 'none',
              label: { formatter: String(markLabel), color: this.chartText },
              lineStyle: { color: '#8c8c8c', type: 'dashed' },
              data: [{ xAxis: markLabel }]
            }
            : undefined
        }
      })
      chart.setOption({
        ...this.baseChartOption(),
        legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
        grid: { left: 56, right: 24, top: 48, bottom: 48 },
        xAxis: { type: 'category', data: labels, axisLabel: { color: this.chartText, hideOverlap: true } },
        yAxis: { type: 'value', name: 'GEX', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
        series: marked
      }, true)
      this.$nextTick(() => chart.resize())
    },
    renderOptionsHistorySlice () {
      const slice = this.historySlices[this.historySliceIndex]
      if (!slice) return
      const chart = this.ensureChart('historyChart')
      if (!chart) return
      const key = this.historyKey

      if (key === 'options.gex' || key === 'options.gexCallPut') {
        const points = slice.gex_distribution || []
        const monthSeries = (slice.month_series || []).map(ms => ({
          month: ms.month,
          gex_distribution: ms.gex_distribution || []
        }))
        const palette = ['#1677ff', '#52c41a', '#fa8c16', '#eb2f96', '#13c2c2', '#722ed1', '#2f54eb']
        const summary = slice.gex_summary || {}
        const price = slice.current_price || slice.underlying || summary.underlying
        const markDefs = this.buildOptionsMarkDefs(summary, price)
        const buildMarks = (strikes) => this.buildStrikeMarkLineData(markDefs, strikes)
        if (key === 'options.gexCallPut') {
          this.applyCallPutGexChart(chart, monthSeries, points, buildMarks)
          this.$nextTick(() => chart.resize())
          this.renderCallPutGexTrend()
          return
        }
        const stacked = this.buildStackedGexSeries(monthSeries, points, palette, buildMarks)
        chart.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
          grid: { left: 56, right: 36, top: 72, bottom: 40 },
          xAxis: { type: 'category', data: stacked.strikes, axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', name: 'GEX', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: stacked.series
        }, true)
        this.$nextTick(() => chart.resize())
        this.renderGexLevelsHistory()
        return
      }

      if (key === 'options.oi' || key === 'options.gex') {
        const points = slice.gex_distribution || []
        let strikes = points.map(p => String(p.strike))
        let series
        if (key === 'options.oi') {
          series = [
            { name: 'Call OI', type: 'bar', stack: 'oi', data: points.map(p => p.call_oi) },
            { name: 'Put OI', type: 'bar', stack: 'oi', data: points.map(p => -p.put_oi) },
            { name: 'Net OI', type: 'line', data: points.map(p => p.net_oi) }
          ]
        } else {
          const stacked = this.buildStackedGexSeries(slice.month_series || [], points, ['#1677ff', '#52c41a', '#fa8c16', '#eb2f96', '#13c2c2', '#722ed1', '#2f54eb'], () => [])
          strikes = stacked.strikes
          series = stacked.series
        }
        chart.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          xAxis: { type: 'category', data: strikes, axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series
        }, true)
        return
      }

      const seriesList = slice.month_series || []
      const palette = ['#1677ff', '#52c41a', '#fa8c16', '#eb2f96', '#13c2c2', '#722ed1']
      const series = []
      seriesList.forEach((item, idx) => {
        const color = palette[idx % palette.length]
        if (key === 'options.tv') {
          const tv = item.time_value_yield || {}
          series.push({ name: `Call ${item.month}`, type: 'line', showSymbol: false, data: (tv.call || []).map(r => [r.strike, r.yield]), itemStyle: { color } })
          series.push({ name: `Put ${item.month}`, type: 'line', showSymbol: false, data: (tv.put || []).map(r => [r.strike, r.yield]), itemStyle: { color }, lineStyle: { type: 'dashed' } })
        } else if (key === 'options.iv') {
          const rows = item.iv_smile || []
          series.push({ name: `Call ${item.month}`, type: 'line', data: rows.filter(r => r.side === 'call').map(r => [r.strike, r.iv]), itemStyle: { color } })
          series.push({ name: `Put ${item.month}`, type: 'line', data: rows.filter(r => r.side === 'put').map(r => [r.strike, r.iv]), itemStyle: { color }, lineStyle: { type: 'dashed' } })
        } else if (key === 'options.maxPain') {
          const curve = (item.max_pain && item.max_pain.curve) || []
          series.push({ name: item.month, type: 'line', data: curve.map(r => [r.strike, r.pain]), itemStyle: { color } })
        }
      })
      if (key === 'options.tv') {
        const marketTv = (slice.time_value_yield || (this.optionsData && this.optionsData.time_value_yield) || {})
        const marketYield = marketTv.market_yield
        const marketWeight = marketTv.market_yield_weight || this.$t('marketComposite.futures.options.tvYieldMarketWeight')
        const sliceSummary = slice.gex_summary || {}
        const slicePrice = slice.current_price || slice.underlying || sliceSummary.underlying
        const tvMarkData = []
        if (marketYield != null && Number.isFinite(Number(marketYield))) {
          tvMarkData.push({
            yAxis: Number(marketYield),
            label: {
              formatter: () => `${this.$t('marketComposite.futures.options.tvYieldMarket')}=${(Number(marketYield) * 100).toFixed(2)}% (${marketWeight})`,
              color: '#f97316',
              position: 'insideStartTop'
            },
            lineStyle: { color: '#f97316', width: 2, type: 'solid' }
          })
        }
        tvMarkData.push(...this.buildCurrentPriceValueAxisMarkData(slicePrice))
        if (tvMarkData.length) {
          series.push({
            name: this.$t('marketComposite.futures.options.tvYieldMarket'),
            type: 'line',
            markLine: { symbol: 'none', data: tvMarkData },
            data: []
          })
        }
      } else if (key === 'options.iv' || key === 'options.maxPain') {
        const sliceSummary = slice.gex_summary || {}
        const slicePrice = slice.current_price || slice.underlying || sliceSummary.underlying
        this.appendValueAxisPriceMark(series, slicePrice)
      }
      chart.setOption({
        ...this.baseChartOption(),
        legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
        xAxis: { type: 'value', scale: true, axisLabel: { color: this.chartText } },
        yAxis: {
          type: 'value',
          axisLabel: key === 'options.tv' || key === 'options.iv'
            ? { formatter: v => `${(Number(v) * 100).toFixed(0)}%`, color: this.chartText }
            : { color: this.chartText },
          splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } }
        },
        series
      }, true)
    },
    renderOptionsHistoryChart (data) {
      const chart = this.ensureChart('historyChart')
      if (!chart) return
      if (data.mode === 'daily' && this.isCapitalHistory) {
        this.renderCapitalCurveChart(chart, { points: data.points || [] }, 'date')
      }
    },
    renderOptionsChartsShared () {
      if (!this.optionsData || this.optionsData.available === false) return
      const points = this.optionsData.gex_distribution || []
      const summary = this.optionsData.gex_summary || {}
      const price = this.optionsCurrentPrice(this.optionsData)
      const monthSeries = this.optionsData.month_series || []
      const palette = ['#1677ff', '#52c41a', '#fa8c16', '#eb2f96', '#13c2c2', '#722ed1', '#2f54eb']

      const markDefs = this.buildOptionsMarkDefs(summary, price)
      const buildStrikeMarks = (strikes) => this.buildStrikeMarkLineData(markDefs, strikes)

      const oi = this.ensureChart('oiChart')
      if (oi) {
        const strikes = points.map(p => String(p.strike))
        const strikeMarks = buildStrikeMarks(strikes)
        oi.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          grid: { left: 56, right: 24, top: 48, bottom: 40 },
          xAxis: { type: 'category', data: strikes, axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', name: 'OI', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: [
            { name: 'Call OI', type: 'bar', stack: 'oi', data: points.map(p => p.call_oi), itemStyle: { color: '#52c41a', opacity: 0.7 } },
            { name: 'Put OI', type: 'bar', stack: 'oi', data: points.map(p => -p.put_oi), itemStyle: { color: '#ff4d4f', opacity: 0.7 } },
            { name: 'Net OI', type: 'line', data: points.map(p => p.net_oi), itemStyle: { color: '#2f54eb' }, markLine: strikeMarks.length ? { symbol: 'none', data: strikeMarks } : undefined }
          ]
        }, true)
      }

      const gexCallPut = this.ensureChart('gexCallPutChart')
      if (gexCallPut) {
        this.applyCallPutGexChart(gexCallPut, monthSeries, points, buildStrikeMarks)
      }

      const gex = this.ensureChart('gexChart')
      if (gex) {
        const stacked = this.buildStackedGexSeries(monthSeries, points, palette, buildStrikeMarks)
        gex.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
          grid: { left: 56, right: 24, top: 48, bottom: 40 },
          xAxis: { type: 'category', data: stacked.strikes, axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', name: 'GEX', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: stacked.series
        }, true)
      }

      const tv = this.ensureChart('tvYieldChart')
      if (tv) {
        const series = []
        const source = monthSeries.length ? monthSeries : [{ month: this.optionsData.month, time_value_yield: this.optionsData.time_value_yield }]
        source.forEach((item, idx) => {
          const tvData = item.time_value_yield || {}
          const color = palette[idx % palette.length]
          series.push({ name: `Call ${item.month || ''}`.trim(), type: 'line', showSymbol: false, data: (tvData.call || []).map(r => [r.strike, r.yield]), itemStyle: { color } })
          series.push({ name: `Put ${item.month || ''}`.trim(), type: 'line', showSymbol: false, data: (tvData.put || []).map(r => [r.strike, r.yield]), itemStyle: { color }, lineStyle: { type: 'dashed' } })
        })
        const marketTv = (this.optionsData && this.optionsData.time_value_yield) || {}
        const marketYield = marketTv.market_yield
        const marketWeight = marketTv.market_yield_weight || this.$t('marketComposite.futures.options.tvYieldMarketWeight')
        const tvMarkData = []
        if (marketYield != null && Number.isFinite(Number(marketYield))) {
          tvMarkData.push({
            yAxis: Number(marketYield),
            label: {
              formatter: () => `${this.$t('marketComposite.futures.options.tvYieldMarket')}=${(Number(marketYield) * 100).toFixed(2)}% (${marketWeight})`,
              color: '#f97316',
              position: 'insideStartTop'
            },
            lineStyle: { color: '#f97316', width: 2, type: 'solid' }
          })
        }
        tvMarkData.push(...this.buildCurrentPriceValueAxisMarkData(price))
        if (tvMarkData.length) {
          series.push({
            name: this.$t('marketComposite.futures.options.tvYieldMarket'),
            type: 'line',
            markLine: { symbol: 'none', data: tvMarkData },
            data: []
          })
        }
        tv.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
          grid: { left: 56, right: 24, top: 56, bottom: 40 },
          tooltip: {
            trigger: 'axis',
            confine: true,
            formatter: (params) => {
              const rows = Array.isArray(params) ? params : [params]
              if (!rows.length) return ''
              const head = rows[0].axisValueLabel || rows[0].name || ''
              const lines = rows.map((row) => {
                const val = row.data && Array.isArray(row.data) ? row.data[1] : row.data
                const text = val == null || val === '' ? '-' : `${(Number(val) * 100).toFixed(2)}%`
                return `${row.marker}${row.seriesName}: ${text}`
              })
              return [head].concat(lines).join('<br/>')
            }
          },
          xAxis: { type: 'value', name: this.$t('marketComposite.futures.options.strike'), scale: true, axisLabel: { color: this.chartText } },
          yAxis: {
            type: 'value',
            name: this.$t('marketComposite.futures.options.tvYieldAxis'),
            axisLabel: { formatter: v => `${(Number(v) * 100).toFixed(0)}%`, color: this.chartText },
            splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } }
          },
          series
        }, true)
      }

      const capital = this.ensureChart('capitalCurveChart')
      if (capital) {
        this.renderCapitalCurveChart(capital, this.optionsData.capital_curve)
      }

      const smile = this.ensureChart('smileChart')
      if (smile) {
        const series = []
        const source = monthSeries.length ? monthSeries : [{ month: this.optionsData.month, iv_smile: this.optionsData.iv_smile }]
        source.forEach((item, idx) => {
          const color = palette[idx % palette.length]
          const rows = item.iv_smile || []
          series.push({ name: `Call IV ${item.month || ''}`.trim(), type: 'line', showSymbol: true, data: rows.filter(r => r.side === 'call').map(r => [r.strike, r.iv]), itemStyle: { color } })
          series.push({ name: `Put IV ${item.month || ''}`.trim(), type: 'line', showSymbol: true, data: rows.filter(r => r.side === 'put').map(r => [r.strike, r.iv]), itemStyle: { color }, lineStyle: { type: 'dashed' } })
        })
        this.appendValueAxisPriceMark(series, price)
        smile.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
          xAxis: { type: 'value', name: 'K', scale: true, axisLabel: { color: this.chartText } },
          yAxis: {
            type: 'value',
            name: 'IV',
            axisLabel: { formatter: v => `${(Number(v) * 100).toFixed(0)}%`, color: this.chartText },
            splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } }
          },
          series
        }, true)
      }

      const pain = this.ensureChart('painChart')
      if (pain) {
        const series = []
        const source = monthSeries.length ? monthSeries : [{ month: this.optionsData.month, max_pain: this.optionsData.max_pain }]
        source.forEach((item, idx) => {
          const curve = (item.max_pain && item.max_pain.curve) || []
          series.push({ name: `${item.month || 'pain'}`, type: 'line', showSymbol: false, data: curve.map(r => [r.strike, r.pain]), itemStyle: { color: palette[idx % palette.length] } })
        })
        this.appendValueAxisPriceMark(series, price)
        pain.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
          xAxis: { type: 'value', scale: true, axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series
        }, true)
      }
    }
  }
}

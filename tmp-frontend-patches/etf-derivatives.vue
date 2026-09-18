<template>
  <div class="fda-page" :class="{ 'theme-dark': isDarkTheme }" data-testid="market-composite-etf">
    <header class="fda-header">
      <div>
        <div class="fda-kicker">{{ $t('marketComposite.kicker') }}</div>
        <h1>{{ $t('marketComposite.etf.title') }}</h1>
        <p>{{ $t('marketComposite.etf.subtitle') }}</p>
      </div>
      <div class="fda-picker">
        <span class="fda-picker-label">{{ $t('marketComposite.etf.pickerLabel') }}</span>
        <a-select
          v-model="selectedRoot"
          show-search
          option-filter-prop="children"
          :loading="loadingProducts"
          :placeholder="$t('marketComposite.etf.pickerPlaceholder')"
          style="min-width: 280px"
          @change="onProductChange"
        >
          <a-select-option v-for="item in products" :key="item.root" :value="item.root">
            {{ productLabel(item) }}
          </a-select-option>
        </a-select>
        <a-button :loading="loadingTab" icon="reload" @click="reloadActiveTab">
          {{ $t('marketComposite.futures.refresh') }}
        </a-button>
      </div>
    </header>

    <a-tabs v-model="activeTab" class="fda-tabs" :animated="false" @change="onTabChange">
      <a-tab-pane key="index" :tab="$t('marketComposite.etf.tabs.index')" />
      <a-tab-pane key="etf" :tab="$t('marketComposite.etf.tabs.etf')" />
      <a-tab-pane key="etfOptions" :tab="$t('marketComposite.etf.tabs.etfOptions')" />
    </a-tabs>

    <a-spin :spinning="loadingTab">
      <div v-if="!selectedRoot" class="fda-empty">
        {{ $t('marketComposite.futures.selectPrompt') }}
      </div>

      <!-- ETF -->
      <div v-else-if="activeTab === 'etf'" class="fda-panel">
        <div class="fda-metrics">
          <div class="fda-metric">
            <span>{{ $t('marketComposite.futures.spot.spotPrice') }}</span>
            <strong>{{ fmt(spotData && spotData.spot_price) }}</strong>
          </div>
          <div class="fda-metric" v-if="spotData && spotData.spot && spotData.spot.etf && spotData.spot.etf.iopv">
            <span>IOPV</span>
            <strong>{{ fmt(spotData.spot.etf.iopv, 4) }}</strong>
          </div>
          <div class="fda-metric" v-if="spotData && spotData.spot && spotData.spot.index">
            <span>{{ spotData.spot.index.name || 'Index' }}</span>
            <strong>{{ fmt(spotData.spot.index.price) }}</strong>
          </div>
          <div class="fda-metric" v-if="spotData && spotData.spot && spotData.spot.etf">
            <span>折价率</span>
            <strong>{{ fmt(spotData.spot.etf.premium_rate, 2) }}%</strong>
          </div>
        </div>
        <div class="fda-section">
          <h3>{{ $t('marketComposite.futures.spot.analysis') }}</h3>
          <ul class="fda-analysis">
            <li v-for="(line, idx) in ((spotData && spotData.analysis) || [])" :key="idx">{{ line }}</li>
          </ul>
          <p v-if="!(spotData && spotData.analysis && spotData.analysis.length)" class="fda-muted">
            {{ $t('marketComposite.futures.noData') }}
          </p>
        </div>
      </div>

      <!-- Index: corresponding benchmark for the selected ETF -->
      <div v-else-if="activeTab === 'index'" class="fda-panel">
        <div class="fda-metrics">
          <div class="fda-metric">
            <span>{{ selectedIndexName || $t('marketComposite.etf.labels.spotIndex') }}</span>
            <strong>{{ fmt(spotData && spotData.spot_price) }}</strong>
          </div>
          <div class="fda-metric" v-if="selectedProduct && selectedProduct.root">
            <span>{{ $t('marketComposite.etf.tabs.etf') }}</span>
            <strong>{{ selectedProduct.name_cn || selectedProduct.root }}</strong>
          </div>
          <div class="fda-metric" v-if="selectedFuturesRoot">
            <span>{{ $t('marketComposite.etf.labels.indexFutures') }}</span>
            <strong>{{ selectedFuturesRoot }}</strong>
          </div>
        </div>
        <div class="fda-section">
          <h3>{{ $t('marketComposite.futures.spot.analysis') }}</h3>
          <ul class="fda-analysis">
            <li v-for="(line, idx) in ((spotData && spotData.analysis) || [])" :key="'idx-' + idx">{{ line }}</li>
          </ul>
          <p v-if="!(spotData && spotData.analysis && spotData.analysis.length)" class="fda-muted">
            {{ $t('marketComposite.futures.noData') }}
          </p>
        </div>
        <template v-if="futuresData">
          <div class="fda-metrics">
            <div class="fda-metric">
              <span>{{ $t('marketComposite.futures.futures.spotPrice') }}</span>
              <strong>{{ fmt(futuresData && futuresData.basis && futuresData.basis.spot_price) }}</strong>
            </div>
            <div class="fda-metric">
              <span>{{ $t('marketComposite.futures.futures.nearBasis') }}</span>
              <strong :class="tone(futuresData && futuresData.basis && futuresData.basis.near_basis)">
                {{ fmt(futuresData && futuresData.basis && futuresData.basis.near_basis) }}
              </strong>
            </div>
            <div class="fda-metric">
              <span>{{ $t('marketComposite.futures.futures.domBasis') }}</span>
              <strong :class="tone(futuresData && futuresData.basis && futuresData.basis.dom_basis)">
                {{ fmt(futuresData && futuresData.basis && futuresData.basis.dom_basis) }}
              </strong>
            </div>
          </div>
          <div class="fda-charts">
            <div class="fda-chart-box">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.futures.termStructure') }}</h3>
                                <div class="fda-chart-actions">
                  <a-button size="small" @click="openHistory('futures.term')">{{ $t('marketComposite.futures.history') }}</a-button>
                  <a-button
                    size="small"
                    :icon="isChartFullscreen('termChart') ? 'fullscreen-exit' : 'fullscreen'"
                    @click="toggleChartFullscreen('termChart')"
                  >
                    {{ isChartFullscreen('termChart') ? $t('marketComposite.futures.exitFullscreen') : $t('marketComposite.futures.fullscreen') }}
                  </a-button>
                </div>
              </div>
              <div ref="termChart" class="fda-chart" />
            </div>
            <div class="fda-chart-box">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.futures.monthlyActivity') }}</h3>
                                <div class="fda-chart-actions">
                  <a-button size="small" @click="openHistory('futures.activity')">{{ $t('marketComposite.futures.history') }}</a-button>
                  <a-button
                    size="small"
                    :icon="isChartFullscreen('activityChart') ? 'fullscreen-exit' : 'fullscreen'"
                    @click="toggleChartFullscreen('activityChart')"
                  >
                    {{ isChartFullscreen('activityChart') ? $t('marketComposite.futures.exitFullscreen') : $t('marketComposite.futures.fullscreen') }}
                  </a-button>
                </div>
              </div>
              <div ref="activityChart" class="fda-chart fda-chart-tall" />
            </div>
            <div class="fda-chart-box">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.futures.optionsNotional') }}</h3>
                                <div class="fda-chart-actions">
                  <a-button size="small" @click="openHistory('futures.notional')">{{ $t('marketComposite.futures.history') }}</a-button>
                  <a-button
                    size="small"
                    :icon="isChartFullscreen('notionalChart') ? 'fullscreen-exit' : 'fullscreen'"
                    @click="toggleChartFullscreen('notionalChart')"
                  >
                    {{ isChartFullscreen('notionalChart') ? $t('marketComposite.futures.exitFullscreen') : $t('marketComposite.futures.fullscreen') }}
                  </a-button>
                </div>
              </div>
              <div ref="notionalChart" class="fda-chart" />
            </div>
            <div class="fda-chart-box">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.futures.optionsPremium') }}</h3>
                                <div class="fda-chart-actions">
                  <a-button size="small" @click="openHistory('futures.premium')">{{ $t('marketComposite.futures.history') }}</a-button>
                  <a-button
                    size="small"
                    :icon="isChartFullscreen('premiumChart') ? 'fullscreen-exit' : 'fullscreen'"
                    @click="toggleChartFullscreen('premiumChart')"
                  >
                    {{ isChartFullscreen('premiumChart') ? $t('marketComposite.futures.exitFullscreen') : $t('marketComposite.futures.fullscreen') }}
                  </a-button>
                </div>
              </div>
              <div ref="premiumChart" class="fda-chart" />
            </div>
          </div>
          <a-table
            class="fda-table"
            size="small"
            :pagination="false"
            :columns="futuresColumns"
            :data-source="(futuresData && futuresData.monthly_activity) || []"
            row-key="symbol"
          />
        </template>
      </div>

      <!-- Options -->
      <div v-else class="fda-panel">
        <div v-if="optionsData && optionsData.available === false" class="fda-empty">
          {{ optionsData.message || $t('marketComposite.futures.options.unavailable') }}
        </div>
        <template v-else>
          <div class="fda-options-toolbar">
            <span>{{ $t('marketComposite.futures.options.month') }}</span>
            <a-select
              v-model="selectedMonth"
              style="min-width: 180px"
              :placeholder="$t('marketComposite.futures.options.monthPlaceholder')"
              @change="loadOptions"
            >
              <a-select-option value="all">{{ $t('marketComposite.futures.options.monthAll') }}</a-select-option>
              <a-select-option v-for="m in optionMonths" :key="m" :value="m">{{ m }}</a-select-option>
            </a-select>
          </div>

          <div class="fda-metrics">
            <div class="fda-metric fda-metric-price">
              <span>{{ $t('marketComposite.futures.options.currentPrice') }}</span>
              <strong>{{ fmt(optionsData && (optionsData.current_price || optionsData.underlying)) }}</strong>
            </div>
            <div class="fda-metric" v-for="item in greeksMetrics" :key="item.key">
              <span>{{ item.label }}</span>
              <strong>{{ fmt(item.value, 4) }}</strong>
            </div>
          </div>

          <div class="fda-metrics fda-metrics-gex">
            <div class="fda-metric" v-for="item in gexMetrics" :key="item.key">
              <span>{{ item.label }}</span>
              <strong>{{ item.display }}</strong>
            </div>
          </div>

          <div class="fda-charts fda-charts-options">
            <div class="fda-chart-box fda-chart-box-wide">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.oiDist') }}</h3>
                                <div class="fda-chart-actions">
                  <a-button size="small" @click="openHistory('options.oi')">{{ $t('marketComposite.futures.history') }}</a-button>
                  <a-button
                    size="small"
                    :icon="isChartFullscreen('oiChart') ? 'fullscreen-exit' : 'fullscreen'"
                    @click="toggleChartFullscreen('oiChart')"
                  >
                    {{ isChartFullscreen('oiChart') ? $t('marketComposite.futures.exitFullscreen') : $t('marketComposite.futures.fullscreen') }}
                  </a-button>
                </div>
              </div>
              <div ref="oiChart" class="fda-chart fda-chart-tall" />
            </div>
            <div class="fda-chart-box fda-chart-box-wide">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.gexDist') }}</h3>
                                <div class="fda-chart-actions">
                  <a-button size="small" @click="openHistory('options.gex')">{{ $t('marketComposite.futures.history') }}</a-button>
                  <a-button
                    size="small"
                    :icon="isChartFullscreen('gexChart') ? 'fullscreen-exit' : 'fullscreen'"
                    @click="toggleChartFullscreen('gexChart')"
                  >
                    {{ isChartFullscreen('gexChart') ? $t('marketComposite.futures.exitFullscreen') : $t('marketComposite.futures.fullscreen') }}
                  </a-button>
                </div>
              </div>
              <div ref="gexChart" class="fda-chart fda-chart-tall" />
            </div>
            <div class="fda-chart-box fda-chart-box-wide">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.timeValueYield') }}</h3>
                                <div class="fda-chart-actions">
                  <a-button size="small" @click="openHistory('options.tv')">{{ $t('marketComposite.futures.history') }}</a-button>
                  <a-button
                    size="small"
                    :icon="isChartFullscreen('tvYieldChart') ? 'fullscreen-exit' : 'fullscreen'"
                    @click="toggleChartFullscreen('tvYieldChart')"
                  >
                    {{ isChartFullscreen('tvYieldChart') ? $t('marketComposite.futures.exitFullscreen') : $t('marketComposite.futures.fullscreen') }}
                  </a-button>
                </div>
              </div>
              <div ref="tvYieldChart" class="fda-chart fda-chart-tall" />
            </div>
            <div class="fda-chart-box">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.ivSmile') }}</h3>
                                <div class="fda-chart-actions">
                  <a-button size="small" @click="openHistory('options.iv')">{{ $t('marketComposite.futures.history') }}</a-button>
                  <a-button
                    size="small"
                    :icon="isChartFullscreen('smileChart') ? 'fullscreen-exit' : 'fullscreen'"
                    @click="toggleChartFullscreen('smileChart')"
                  >
                    {{ isChartFullscreen('smileChart') ? $t('marketComposite.futures.exitFullscreen') : $t('marketComposite.futures.fullscreen') }}
                  </a-button>
                </div>
              </div>
              <div ref="smileChart" class="fda-chart" />
            </div>
            <div class="fda-chart-box">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.maxPain') }}</h3>
                                <div class="fda-chart-actions">
                  <a-button size="small" @click="openHistory('options.maxPain')">{{ $t('marketComposite.futures.history') }}</a-button>
                  <a-button
                    size="small"
                    :icon="isChartFullscreen('painChart') ? 'fullscreen-exit' : 'fullscreen'"
                    @click="toggleChartFullscreen('painChart')"
                  >
                    {{ isChartFullscreen('painChart') ? $t('marketComposite.futures.exitFullscreen') : $t('marketComposite.futures.fullscreen') }}
                  </a-button>
                </div>
              </div>
              <div ref="painChart" class="fda-chart" />
            </div>
          </div>
        </template>
      </div>
    </a-spin>

    <a-modal
      :title="historyTitle"
      :visible="historyVisible"
      :footer="null"
      :width="920"
      destroy-on-close
      @cancel="closeHistory"
    >
      <div class="fda-history-toolbar">
        <span>{{ $t('marketComposite.futures.historyPeriod') }}</span>
        <a-radio-group v-model="historyDays" button-style="solid" size="small" @change="loadHistory">
          <a-radio-button :value="30">30D</a-radio-button>
          <a-radio-button :value="90">90D</a-radio-button>
          <a-radio-button :value="180">180D</a-radio-button>
        </a-radio-group>
        <span>{{ $t('marketComposite.futures.historyFrequency') }}</span>
        <a-radio-group v-model="historyFrequency" button-style="solid" size="small" @change="loadHistory">
          <a-radio-button value="day">{{ $t('marketComposite.futures.freqDay') }}</a-radio-button>
          <a-radio-button value="week">{{ $t('marketComposite.futures.freqWeek') }}</a-radio-button>
          <a-radio-button value="month">{{ $t('marketComposite.futures.freqMonth') }}</a-radio-button>
        </a-radio-group>
      </div>
      <a-spin :spinning="historyLoading">
        <p v-if="historyNote" class="fda-muted">{{ historyNote }}</p>
        <div v-if="historySlices.length" class="fda-history-slider">
          <div class="fda-history-slider-meta">
            <span>{{ $t('marketComposite.futures.historySlice') }}</span>
            <strong>{{ historySliceLabel }}</strong>
          </div>
          <a-slider
            v-model="historySliceIndex"
            :min="0"
            :max="Math.max(historySlices.length - 1, 0)"
            :tip-formatter="historyTipFormatter"
            @change="onHistorySliceChange"
          />
        </div>
        <div ref="historyChart" class="fda-chart fda-chart-history" />
      </a-spin>
    </a-modal>

    <a-collapse class="fda-ai" :bordered="false">
      <a-collapse-panel key="ai" :header="$t('marketComposite.futures.aiPanel')">
        <AnalysisView
          :key="`futures-ai-${activeTab}`"
          :embedded="true"
          :allowed-markets="aiMarkets"
          :market-label-overrides="aiLabelOverrides"
          :scope-title="$t('marketComposite.etf.title')"
          :scope-subtitle="aiHint"
          :preset-market="aiMarket"
          :symbol-search-filters="symbolSearchFilters"
        />
      </a-collapse-panel>
    </a-collapse>
  </div>
</template>

<script>
import { mapState } from 'vuex'
import * as echarts from 'echarts'
import AnalysisView from '@/views/ai-analysis'
import {
  listDerivativeProducts,
  getSpotPanel,
  getFuturesPanel,
  getOptionsPanel,
  getChartHistory
} from '@/api/cnDerivatives'

export default {
  name: 'EtfDerivativesAnalysis',
  components: { AnalysisView },
  data () {
    return {
      activeTab: 'index',
      products: [],
      selectedRoot: undefined,
      selectedMonth: 'all',
      loadingProducts: false,
      loadingTab: false,
      spotData: null,
      futuresData: null,
      optionsData: null,
      charts: {},
      fullscreenChartRef: null,
      historyVisible: false,
      historyLoading: false,
      historyKey: '',
      historyDays: 90,
      historyFrequency: 'week',
      historyNote: '',
      historyTitle: '',
      historySlices: [],
      historySliceIndex: 0
    }
  },
  computed: {
    ...mapState({
      navTheme: state => state.app.theme
    }),
    historySliceLabel () {
      const slice = this.historySlices[this.historySliceIndex]
      return (slice && (slice.label || slice.date)) || '--'
    },
    isDarkTheme () {
      return this.navTheme === 'dark' || this.navTheme === 'realdark'
    },
    optionMonths () {
      return (this.optionsData && this.optionsData.months) || []
    },
    selectedProduct () {
      return this.findSelectedProduct()
    },
    selectedIndexSymbol () {
      const product = this.selectedProduct || {}
      return product.index_symbol || ''
    },
    selectedIndexName () {
      const product = this.selectedProduct || {}
      return product.index_name || product.index_symbol || ''
    },
    selectedFuturesRoot () {
      const product = this.selectedProduct || {}
      return product.index_futures_root || ''
    },
    selectedUnderlyingCode () {
      const product = this.selectedProduct || {}
      return product.underlying_code || this.selectedRoot
    },
    selectedPickerKind () {
      const product = this.selectedProduct
      return (product && product.picker_kind) || ''
    },
    futuresColumns () {
      return [
        { title: this.$t('marketComposite.futures.futures.symbol'), dataIndex: 'symbol' },
        { title: this.$t('marketComposite.futures.futures.price'), dataIndex: 'price', customRender: v => this.fmt(v) },
        { title: this.$t('marketComposite.futures.futures.volume'), dataIndex: 'volume', customRender: v => this.fmt(v, 0) },
        { title: this.$t('marketComposite.futures.futures.openInterest'), dataIndex: 'open_interest', customRender: v => this.fmt(v, 0) }
      ]
    },
    greeksMetrics () {
      const g = (this.optionsData && this.optionsData.greeks) || {}
      return [
        { key: 'delta', label: 'Delta', value: g.delta },
        { key: 'gamma', label: 'Gamma', value: g.gamma },
        { key: 'vega', label: 'Vega', value: g.vega },
        { key: 'theta', label: 'Theta', value: g.theta }
      ]
    },
    gexMetrics () {
      const ind = ((this.optionsData && this.optionsData.indicators) || {}).gex || {}
      const s = ind.summary || (this.optionsData && this.optionsData.gex_summary) || {}
      const mp = this.optionsData && this.optionsData.max_pain
      return [
        { key: 'net', label: 'Net GEX', display: this.fmt(s.net_gex, 0) },
        { key: 'call', label: 'Call GEX', display: this.fmt(s.call_gex, 0) },
        { key: 'put', label: 'Put GEX', display: this.fmt(s.put_gex, 0) },
        { key: 'flip', label: 'Flip', display: this.fmt(s.flip) },
        { key: 'callWall', label: 'Call Wall', display: this.fmt(s.call_wall) },
        { key: 'putWall', label: 'Put Wall', display: this.fmt(s.put_wall) },
        { key: 'pin', label: 'Pin', display: this.fmt(s.pin) },
        { key: 'maxPain', label: 'Max Pain', display: this.fmt(mp && mp.strike) }
      ]
    },
    aiMarket () {
      if (this.activeTab === 'index') return 'CNIndexFutures'
      if (this.activeTab === 'etf') return 'CNStock'
      return 'CNIndexOptions'
    },
    aiMarkets () {
      if (this.activeTab === 'index') return ['CNIndexFutures', 'CNStock']
      if (this.activeTab === 'etf') return ['CNStock', 'USStock', 'HKStock']
      return ['CNIndexOptions']
    },
    aiLabelOverrides () {
      return {
        CNIndexFutures: 'marketComposite.etf.labels.indexFutures',
        CNStock: 'marketComposite.etf.labels.spotIndex',
        USStock: 'marketComposite.etf.labels.usEtf',
        HKStock: 'marketComposite.etf.labels.hkEtf',
        CNIndexOptions: 'marketComposite.etf.tabs.etfOptions'
      }
    },
    symbolSearchFilters () {
      if (this.activeTab === 'index') return { CNStock: { asset_class: 'index' } }
      if (this.activeTab === 'etf') {
        return {
          CNStock: { asset_class: 'etf' },
          USStock: { asset_class: 'etf' },
          HKStock: { asset_class: 'etf' }
        }
      }
      return { CNIndexOptions: { etf_only: true } }
    },
    aiHint () {
      if (this.activeTab === 'index') return this.$t('marketComposite.etf.hints.index')
      if (this.activeTab === 'etf') return this.$t('marketComposite.etf.hints.etf')
      return this.$t('marketComposite.etf.hints.etfOptions')
    },
    chartText () {
      return this.isDarkTheme ? '#8c8c8c' : '#64748b'
    },
    chartGrid () {
      return this.isDarkTheme ? '#242424' : '#e8edf3'
    }
  },
  created () {
    this.syncTabFromRoute()
    this.loadProducts()
  },
  mounted () {
    window.addEventListener('resize', this.resizeCharts)
    document.addEventListener('fullscreenchange', this.onFullscreenChange)
    document.addEventListener('webkitfullscreenchange', this.onFullscreenChange)
  },
  beforeDestroy () {
    window.removeEventListener('resize', this.resizeCharts)
    document.removeEventListener('fullscreenchange', this.onFullscreenChange)
    document.removeEventListener('webkitfullscreenchange', this.onFullscreenChange)
    Object.values(this.charts).forEach(chart => chart && chart.dispose())
  },
  watch: {
    '$route.query.tab' () {
      this.syncTabFromRoute()
    },
    isDarkTheme () {
      this.$nextTick(() => this.renderActiveCharts())
    }
  },
  methods: {
    etfScopeParams () {
      return { scope: 'etf' }
    },
    findSelectedProduct () {
      const root = this.selectedRoot
      if (!root) return null
      return (this.products || []).find(item => item.root === root) || null
    },
    matchProductRoot (rows, qRoot) {
      const q = String(qRoot || '').trim().toUpperCase()
      if (!q) return null
      const code6 = q.replace(/[^0-9]/g, '').slice(0, 6)
      return (rows || []).find(item => {
        const root = String(item.root || '').toUpperCase()
        const sym = String(item.stock_symbol || '').toUpperCase()
        const underlying = String(item.underlying_code || '')
        return root === q || sym === q || underlying === code6 || root === code6
      })
    },
    pickDefaultProduct (rows) {
      const list = rows || []
      if (!list.length) return null
      return list.find(r => r.root === '510050.SH' || r.underlying_code === '510050')
        || list.find(r => r.picker_kind === 'cn_etf')
        || list[0]
    },
    productLabel (item) {
      const sym = item.stock_symbol || item.root
      const name = item.name_cn || item.name || sym
      const indexName = item.index_name ? ` / ${item.index_name}` : ''
      return `${sym} · ${name}${indexName}`
    },
    fmt (value, digits = 2) {
      if (value === null || value === undefined || value === '') return '-'
      const n = Number(value)
      if (!Number.isFinite(n)) return '-'
      return n.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: 0 })
    },
    pct (value) {
      if (value === null || value === undefined || value === '') return '-'
      const n = Number(value)
      if (!Number.isFinite(n)) return '-'
      return `${(n * 100).toFixed(2)}%`
    },
    tone (value) {
      const n = Number(value)
      if (!Number.isFinite(n) || n === 0) return ''
      return n > 0 ? 'positive' : 'negative'
    },
    syncTabFromRoute () {
      const tab = this.$route && this.$route.query && this.$route.query.tab
      if (tab && ['index', 'etf', 'etfOptions'].includes(tab)) {
        this.activeTab = tab
      }
    },
    onTabChange (key) {
      this.activeTab = key
      if (this.$router) {
        const query = { ...(this.$route.query || {}), tab: key }
        if (this.selectedRoot) query.root = this.selectedRoot
        this.$router.replace({ query }).catch(() => {})
      }
      // Keep the same ETF selection across tabs; only reload the active panel.
      this.spotData = null
      this.futuresData = null
      this.optionsData = null
      this.reloadActiveTab()
    },
    async loadProducts () {
      this.loadingProducts = true
      try {
        // Shared ETF-only picker list (tab ignored by backend).
        const res = await listDerivativeProducts({ scope: 'etf', tab: 'etf' })
        const rows = (res && res.data && res.data.products) || []
        this.products = rows
        const qRoot = this.$route && this.$route.query && this.$route.query.root
        const matched = qRoot ? this.matchProductRoot(rows, qRoot) : null
        if (matched) {
          this.selectedRoot = matched.root
        } else if (!this.selectedRoot || !rows.some(r => r.root === this.selectedRoot)) {
          const preferred = this.pickDefaultProduct(rows)
          this.selectedRoot = preferred ? preferred.root : undefined
        }
        if (this.selectedRoot) {
          await this.reloadActiveTab()
        }
      } catch (e) {
        this.$message.error((e && e.message) || this.$t('marketComposite.futures.loadFailed'))
      } finally {
        this.loadingProducts = false
      }
    },
    onProductChange (root) {
      this.selectedRoot = root
      this.spotData = null
      this.futuresData = null
      this.optionsData = null
      this.selectedMonth = 'all'
      if (this.$router) {
        const query = { ...(this.$route.query || {}), root, tab: this.activeTab }
        this.$router.replace({ query }).catch(() => {})
      }
      this.reloadActiveTab()
    },
    async reloadActiveTab () {
      if (!this.selectedRoot) return
      if (this.activeTab === 'index') {
        await this.loadIndexTab()
      } else if (this.activeTab === 'etf') {
        await this.loadSpot()
      } else {
        await this.loadOptions()
      }
    },
    async loadIndexTab () {
      // Spot panel for the ETF's corresponding benchmark index.
      this.loadingTab = true
      try {
        const indexSymbol = this.selectedIndexSymbol
        if (indexSymbol) {
          const res = await getSpotPanel(indexSymbol, {
            scope: 'etf',
            picker_kind: 'spot_index',
            market: 'CNStock'
          })
          this.spotData = (res && res.data) || null
        } else {
          // Fallback: ETF spot panel still carries the embedded index quote.
          await this.loadSpot()
        }
        const futuresRoot = this.selectedFuturesRoot
        if (futuresRoot) {
          try {
            const fres = await getFuturesPanel(futuresRoot)
            this.futuresData = (fres && fres.data) || null
            this.$nextTick(() => this.renderFuturesCharts())
          } catch (e) {
            this.futuresData = null
          }
        } else {
          this.futuresData = null
        }
      } catch (e) {
        this.$message.error((e && e.message) || this.$t('marketComposite.futures.loadFailed'))
      } finally {
        this.loadingTab = false
      }
    },
    spotRequestParams () {
      const product = this.selectedProduct || {}
      const params = { scope: 'etf' }
      params.picker_kind = 'cn_etf'
      if (product.market) params.market = product.market
      return params
    },
    spotRequestRoot () {
      return this.selectedUnderlyingCode || this.selectedRoot
    },
    async loadSpot () {
      this.loadingTab = true
      try {
        const res = await getSpotPanel(this.spotRequestRoot(), this.spotRequestParams())
        this.spotData = (res && res.data) || null
      } catch (e) {
        this.$message.error((e && e.message) || this.$t('marketComposite.futures.loadFailed'))
      } finally {
        this.loadingTab = false
      }
    },
    async loadFutures () {
      this.loadingTab = true
      try {
        const res = await getFuturesPanel(this.selectedRoot)
        this.futuresData = (res && res.data) || null
        this.$nextTick(() => this.renderFuturesCharts())
      } catch (e) {
        this.$message.error((e && e.message) || this.$t('marketComposite.futures.loadFailed'))
      } finally {
        this.loadingTab = false
      }
    },
    async loadOptions () {
      this.loadingTab = true
      try {
        const res = await getOptionsPanel(
          this.selectedProduct && this.selectedProduct.underlying_code
            ? this.selectedProduct.underlying_code
            : this.selectedRoot,
          this.selectedMonth,
          this.etfScopeParams()
        )
        this.optionsData = (res && res.data) || null
        if (this.optionsData && this.optionsData.month) {
          this.selectedMonth = this.optionsData.month
        }
      } catch (e) {
        this.$message.error((e && e.message) || this.$t('marketComposite.futures.loadFailed'))
      } finally {
        this.loadingTab = false
        this.scheduleOptionsChartRender()
      }
    },
    ensureChart (refName) {
      const el = this.$refs[refName]
      if (!el) return null
      if (!this.charts[refName]) {
        this.charts[refName] = echarts.init(el)
      }
      return this.charts[refName]
    },
    baseChartOption () {
      return {
        textStyle: { color: this.chartText },
        grid: { left: 48, right: 24, top: 36, bottom: 40 },
        tooltip: { trigger: 'axis', confine: true }
      }
    },
    renderFuturesCharts () {
      const term = this.ensureChart('termChart')
      const activity = this.ensureChart('activityChart')
      const notional = this.ensureChart('notionalChart')
      const premium = this.ensureChart('premiumChart')
      const curve = ((this.futuresData && this.futuresData.term_structure) || []).filter(p => !p.is_continuous)
      const activityRows = (this.futuresData && this.futuresData.monthly_activity) || curve
      const months = activityRows.map(p => p.symbol || p.label)
      const capitalRows = (this.futuresData && this.futuresData.options_settled_capital) || []

      if (term) {
        const termMonths = curve.map(p => p.label || p.symbol)
        term.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          xAxis: { type: 'category', data: termMonths, axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: [
            {
              name: this.$t('marketComposite.futures.futures.termStructure'),
              type: 'line',
              data: curve.map(p => p.price),
              smooth: true,
              showSymbol: true
            },
            {
              name: this.$t('marketComposite.futures.futures.basis'),
              type: 'bar',
              data: curve.map(p => p.basis),
              itemStyle: { color: '#69c0ff', opacity: 0.35 }
            }
          ]
        }, true)
      }

      if (activity) {
        activity.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          grid: { left: 52, right: 64, top: 48, bottom: 40 },
          xAxis: { type: 'category', data: months, axisLabel: { color: this.chartText } },
          yAxis: [
            { type: 'value', name: this.$t('marketComposite.futures.futures.openInterest'), splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
            { type: 'value', name: this.$t('marketComposite.futures.futures.capitalAxis'), splitLine: { show: false } }
          ],
          series: [
            { name: this.$t('marketComposite.futures.futures.volume'), type: 'bar', data: activityRows.map(p => p.volume) },
            { name: this.$t('marketComposite.futures.futures.openInterest'), type: 'line', data: activityRows.map(p => p.open_interest) },
            {
              name: this.$t('marketComposite.futures.futures.futuresCapital'),
              type: 'line',
              yAxisIndex: 1,
              data: activityRows.map(p => p.futures_capital),
              itemStyle: { color: '#1677ff' }
            },
            {
              name: this.$t('marketComposite.futures.futures.optionNotional'),
              type: 'line',
              yAxisIndex: 1,
              data: activityRows.map(p => p.option_notional),
              itemStyle: { color: '#fa8c16' }
            },
            {
              name: this.$t('marketComposite.futures.futures.combinedCapital'),
              type: 'line',
              yAxisIndex: 1,
              data: activityRows.map(p => p.combined_capital),
              itemStyle: { color: '#722ed1' },
              lineStyle: { width: 2.4 }
            }
          ]
        }, true)
      }

      if (notional) {
        notional.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          xAxis: { type: 'category', data: capitalRows.map(r => r.month), axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: [
            {
              name: this.$t('marketComposite.futures.futures.callNotional'),
              type: 'bar',
              stack: 'notional',
              data: capitalRows.map(r => r.call_notional),
              itemStyle: { color: '#52c41a' }
            },
            {
              name: this.$t('marketComposite.futures.futures.putNotional'),
              type: 'bar',
              stack: 'notional',
              data: capitalRows.map(r => r.put_notional),
              itemStyle: { color: '#ff4d4f' }
            }
          ]
        }, true)
      }

      if (premium) {
        premium.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          xAxis: { type: 'category', data: capitalRows.map(r => r.month), axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: [
            {
              name: this.$t('marketComposite.futures.futures.callPremium'),
              type: 'bar',
              stack: 'premium',
              data: capitalRows.map(r => r.call_premium != null ? r.call_premium : r.call_settled),
              itemStyle: { color: '#52c41a' }
            },
            {
              name: this.$t('marketComposite.futures.futures.putPremium'),
              type: 'bar',
              stack: 'premium',
              data: capitalRows.map(r => r.put_premium != null ? r.put_premium : r.put_settled),
              itemStyle: { color: '#ff4d4f' }
            }
          ]
        }, true)
      }
    },
    nearestStrikeLabel (strikes, value) {
      if (value == null || !strikes.length) return null
      const num = Number(value)
      if (!Number.isFinite(num)) return null
      let best = strikes[0]
      let bestDist = Math.abs(Number(best) - num)
      strikes.forEach(s => {
        const dist = Math.abs(Number(s) - num)
        if (dist < bestDist) {
          best = s
          bestDist = dist
        }
      })
      return best
    },

    resolveGexIndicatorView () {
      // Prefer chart-indicator contract (plots/layers/summary); fall back to legacy arrays.
      const data = this.optionsData || {}
      const ind = ((data.indicators || {}).gex) || null
      const calc = (ind && (ind.calculatedVars || ind.calculated_vars)) || {}
      const points = calc.points || data.gex_distribution || []
      const summary = (ind && ind.summary) || data.gex_summary || {}
      const categories = (ind && ind.categories && ind.categories.length)
        ? ind.categories
        : points.map(p => p.strike)
      const plotByName = {}
      ;((ind && ind.plots) || []).forEach(p => {
        if (p && p.name) plotByName[p.name] = p
      })
      const seriesFromPlot = (name, fallbackKey) => {
        const plot = plotByName[name]
        if (plot && Array.isArray(plot.data) && plot.data.length) return plot.data
        return points.map(p => p[fallbackKey])
      }
      const markDefs = ((ind && ind.layers) || []).map(layer => ({
        name: layer.text || layer.name || '',
        value: layer.strike,
        color: layer.color || '#1890ff',
        width: layer.dashed === false ? 2 : 1.5,
        dashed: layer.dashed !== false && String(layer.text || '') !== 'Price'
      }))
      return {
        points,
        summary,
        categories,
        callGex: seriesFromPlot('Call GEX', 'call_gex'),
        putGex: seriesFromPlot('Put GEX', 'put_gex'),
        netGex: seriesFromPlot('Net GEX', 'net_gex'),
        markDefs
      }
    },

    renderOptionsCharts () {
      if (!this.optionsData || this.optionsData.available === false) return
      const points = this.optionsData.gex_distribution || []
      const summary = this.optionsData.gex_summary || {}
      const price = this.optionsData.current_price || this.optionsData.underlying || summary.underlying
      const monthSeries = this.optionsData.month_series || []
      const palette = ['#1677ff', '#52c41a', '#fa8c16', '#eb2f96', '#13c2c2', '#722ed1', '#2f54eb']

      const markDefs = [
        { name: 'Price', value: price, color: '#1890ff', width: 2 },
        { name: 'Flip', value: summary.flip, color: '#faad14', width: 1.5 },
        { name: 'Call Wall', value: summary.call_wall, color: '#52c41a', width: 1.5 },
        { name: 'Put Wall', value: summary.put_wall, color: '#ff4d4f', width: 1.5 },
        { name: 'Pin', value: summary.pin, color: '#722ed1', width: 1.5 }
      ]

      const buildMarks = (strikes) => markDefs.map((item, idx) => {
        const x = this.nearestStrikeLabel(strikes, item.value)
        if (x == null) return null
        return {
          name: item.name,
          xAxis: x,
          lineStyle: { color: item.color, width: item.width, type: item.name === 'Price' ? 'solid' : 'dashed' },
          label: {
            formatter: item.name,
            color: item.color,
            position: 'insideEndTop',
            distance: idx * 16
          }
        }
      }).filter(Boolean)

      const oi = this.ensureChart('oiChart')
      if (oi) {
        const strikes = points.map(p => p.strike)
        oi.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          grid: { left: 56, right: 24, top: 48, bottom: 40 },
          xAxis: { type: 'category', data: strikes, axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', name: 'OI', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: [
            { name: 'Call OI', type: 'bar', stack: 'oi', data: points.map(p => p.call_oi), itemStyle: { color: '#52c41a', opacity: 0.7 } },
            { name: 'Put OI', type: 'bar', stack: 'oi', data: points.map(p => -p.put_oi), itemStyle: { color: '#ff4d4f', opacity: 0.7 } },
            { name: 'Net OI', type: 'line', data: points.map(p => p.net_oi), itemStyle: { color: '#2f54eb' }, markLine: { symbol: 'none', data: buildMarks(strikes) } }
          ]
        }, true)
      }

      const gex = this.ensureChart('gexChart')
      if (gex) {
        const gexView = this.resolveGexIndicatorView()
        const strikes = gexView.categories.length ? gexView.categories : gexView.points.map(p => p.strike)
        const markDefs = gexView.markDefs.length ? gexView.markDefs : [
          { name: 'Price', value: this.optionsData.current_price || this.optionsData.underlying || gexView.summary.underlying, color: '#1890ff', width: 2, dashed: false },
          { name: 'Flip', value: gexView.summary.flip, color: '#faad14', width: 1.5, dashed: true },
          { name: 'Call Wall', value: gexView.summary.call_wall, color: '#52c41a', width: 1.5, dashed: true },
          { name: 'Put Wall', value: gexView.summary.put_wall, color: '#ff4d4f', width: 1.5, dashed: true },
          { name: 'Pin', value: gexView.summary.pin, color: '#722ed1', width: 1.5, dashed: true }
        ]
        const buildGexMarks = (axis) => markDefs.map((item, idx) => {
          const x = this.nearestStrikeLabel(axis, item.value)
          if (x == null) return null
          return {
            name: item.name,
            xAxis: x,
            lineStyle: { color: item.color, width: item.width, type: (item.dashed === false || item.name === 'Price') ? 'solid' : 'dashed' },
            label: {
              show: true,
              formatter: this.buildMarkLabel(item.name, item.value),
              color: item.color,
              position: 'insideEndTop',
              distance: idx * 16
            }
          }
        }).filter(Boolean)
        gex.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          grid: { left: 56, right: 24, top: 48, bottom: 40 },
          xAxis: { type: 'category', data: strikes, axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', name: 'GEX', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: [
            { name: 'Call GEX', type: 'bar', data: gexView.callGex, itemStyle: { color: '#52c41a', opacity: 0.55 } },
            { name: 'Put GEX', type: 'bar', data: gexView.putGex, itemStyle: { color: '#ff4d4f', opacity: 0.55 } },
            { name: 'Net GEX', type: 'line', data: gexView.netGex, itemStyle: { color: '#fa8c16' }, markLine: { symbol: 'none', data: buildGexMarks(strikes) } }
          ]
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
        tv.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
          grid: { left: 56, right: 24, top: 56, bottom: 40 },
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
        pain.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
          xAxis: { type: 'value', scale: true, axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series
        }, true)
      }
    },
    openHistory (chartKey) {
      this.historyKey = chartKey
      this.historyTitle = `${this.$t('marketComposite.futures.history')} · ${chartKey}`
      this.historySlices = []
      this.historySliceIndex = 0
      this.historyVisible = true
      this.$nextTick(() => this.loadHistory())
    },
    closeHistory () {
      this.historyVisible = false
      this.historySlices = []
      this.historySliceIndex = 0
      if (this.charts.historyChart) {
        this.charts.historyChart.dispose()
        delete this.charts.historyChart
      }
    },
    historyTipFormatter (index) {
      const slice = this.historySlices[index]
      return (slice && (slice.label || slice.date)) || String(index)
    },
    onHistorySliceChange () {
      this.renderHistorySlice()
    },
    async loadHistory () {
      if (!this.selectedRoot || !this.historyKey) return
      this.historyLoading = true
      try {
        const res = await getChartHistory({
          root: this.selectedRoot,
          chart: this.historyKey,
          days: this.historyDays,
          frequency: this.historyFrequency,
          month: this.selectedMonth || 'all',
          ...this.etfScopeParams()
        })
        const data = (res && res.data) || {}
        this.historyNote = data.note || ''
        if (data.mode === 'slices') {
          this.historySlices = data.slices || []
          this.historySliceIndex = Math.max(this.historySlices.length - 1, 0)
          this.$nextTick(() => this.renderHistorySlice())
        } else {
          this.historySlices = []
          this.$nextTick(() => this.renderHistoryChart(data))
        }
      } catch (e) {
        this.$message.error((e && e.message) || this.$t('marketComposite.futures.loadFailed'))
      } finally {
        this.historyLoading = false
      }
    },
    renderHistorySlice () {
      const slice = this.historySlices[this.historySliceIndex]
      if (!slice) return
      const chart = this.ensureChart('historyChart')
      if (!chart) return
      const key = this.historyKey

      if (key === 'futures.term') {
        const curve = (slice.term_structure || []).filter(p => !p.is_continuous)
        chart.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          xAxis: { type: 'category', data: curve.map(p => p.label || p.symbol), axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: [
            {
              name: this.$t('marketComposite.futures.futures.termStructure'),
              type: 'line',
              data: curve.map(p => p.price),
              smooth: true,
              showSymbol: true
            },
            {
              name: this.$t('marketComposite.futures.futures.basis'),
              type: 'bar',
              data: curve.map(p => p.basis),
              itemStyle: { color: '#69c0ff', opacity: 0.35 }
            }
          ]
        }, true)
        return
      }

      if (key === 'futures.activity') {
        const rows = slice.monthly_activity || slice.term_structure || []
        chart.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          grid: { left: 52, right: 64, top: 48, bottom: 40 },
          xAxis: { type: 'category', data: rows.map(p => p.symbol || p.label), axisLabel: { color: this.chartText } },
          yAxis: [
            { type: 'value', name: this.$t('marketComposite.futures.futures.openInterest'), splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
            { type: 'value', name: this.$t('marketComposite.futures.futures.capitalAxis'), splitLine: { show: false } }
          ],
          series: [
            { name: this.$t('marketComposite.futures.futures.volume'), type: 'bar', data: rows.map(p => p.volume) },
            { name: this.$t('marketComposite.futures.futures.openInterest'), type: 'line', data: rows.map(p => p.open_interest) },
            {
              name: this.$t('marketComposite.futures.futures.futuresCapital'),
              type: 'line',
              yAxisIndex: 1,
              data: rows.map(p => p.futures_capital),
              itemStyle: { color: '#1677ff' }
            },
            {
              name: this.$t('marketComposite.futures.futures.optionNotional'),
              type: 'line',
              yAxisIndex: 1,
              data: rows.map(p => p.option_notional),
              itemStyle: { color: '#fa8c16' }
            },
            {
              name: this.$t('marketComposite.futures.futures.combinedCapital'),
              type: 'line',
              yAxisIndex: 1,
              data: rows.map(p => p.combined_capital),
              itemStyle: { color: '#722ed1' },
              lineStyle: { width: 2.4 }
            }
          ]
        }, true)
        return
      }

      if (key === 'futures.notional' || key === 'futures.premium') {
        const capitalRows = slice.options_settled_capital || []
        if (!capitalRows.length) {
          chart.setOption({
            ...this.baseChartOption(),
            title: {
              text: this.$t('marketComposite.futures.historyNoOptionSlice'),
              left: 'center',
              top: 'middle',
              textStyle: { color: this.chartText, fontSize: 14, fontWeight: 400 }
            },
            xAxis: { show: false },
            yAxis: { show: false },
            series: []
          }, true)
          return
        }
        const isNotional = key === 'futures.notional'
        chart.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          xAxis: { type: 'category', data: capitalRows.map(r => r.month), axisLabel: { color: this.chartText } },
          yAxis: { type: 'value', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: isNotional
            ? [
              {
                name: this.$t('marketComposite.futures.futures.callNotional'),
                type: 'bar',
                stack: 'notional',
                data: capitalRows.map(r => r.call_notional),
                itemStyle: { color: '#52c41a' }
              },
              {
                name: this.$t('marketComposite.futures.futures.putNotional'),
                type: 'bar',
                stack: 'notional',
                data: capitalRows.map(r => r.put_notional),
                itemStyle: { color: '#ff4d4f' }
              }
            ]
            : [
              {
                name: this.$t('marketComposite.futures.futures.callPremium'),
                type: 'bar',
                stack: 'premium',
                data: capitalRows.map(r => r.call_premium),
                itemStyle: { color: '#52c41a' }
              },
              {
                name: this.$t('marketComposite.futures.futures.putPremium'),
                type: 'bar',
                stack: 'premium',
                data: capitalRows.map(r => r.put_premium),
                itemStyle: { color: '#ff4d4f' }
              }
            ]
        }, true)
        return
      }

      if (key === 'options.oi' || key === 'options.gex') {
        const points = slice.gex_distribution || []
        const strikes = points.map(p => p.strike)
        const series = key === 'options.oi'
          ? [
            { name: 'Call OI', type: 'bar', stack: 'oi', data: points.map(p => p.call_oi) },
            { name: 'Put OI', type: 'bar', stack: 'oi', data: points.map(p => -p.put_oi) },
            { name: 'Net OI', type: 'line', data: points.map(p => p.net_oi) }
          ]
          : [
            { name: 'Call GEX', type: 'bar', data: points.map(p => p.call_gex) },
            { name: 'Put GEX', type: 'bar', data: points.map(p => p.put_gex) },
            { name: 'Net GEX', type: 'line', data: points.map(p => p.net_gex) }
          ]
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
      chart.setOption({
        ...this.baseChartOption(),
        legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
        xAxis: { type: 'value', scale: true, axisLabel: { color: this.chartText } },
        yAxis: { type: 'value', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
        series
      }, true)
    },
    renderHistoryChart (data) {
      const chart = this.ensureChart('historyChart')
      if (!chart) return
      if (data.mode === 'daily') {
        const points = data.points || []
        chart.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          xAxis: { type: 'category', data: points.map(p => p.date), axisLabel: { color: this.chartText } },
          yAxis: [
            { type: 'value', name: 'OI / Vol', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
            { type: 'value', name: this.$t('marketComposite.futures.futures.capitalAxis'), splitLine: { show: false } }
          ],
          series: [
            { name: this.$t('marketComposite.futures.futures.openInterest'), type: 'line', data: points.map(p => p.open_interest) },
            { name: this.$t('marketComposite.futures.futures.volume'), type: 'bar', data: points.map(p => p.volume), itemStyle: { opacity: 0.35 } },
            { name: this.$t('marketComposite.futures.futures.futuresCapital'), type: 'line', yAxisIndex: 1, data: points.map(p => p.futures_capital) },
            { name: this.$t('marketComposite.futures.futures.price'), type: 'line', data: points.map(p => p.price) }
          ]
        }, true)
      }
    },
    renderActiveCharts () {
      if (this.activeTab === 'index') this.renderFuturesCharts()
      if (this.activeTab === 'etfOptions') this.renderOptionsCharts()
    },
    scheduleOptionsChartRender () {
      this.$nextTick(() => {
        this.renderOptionsCharts()
        requestAnimationFrame(() => {
          this.resizeCharts()
        })
      })
    },

    chartBoxEl (refName) {
      const el = this.$refs[refName]
      const node = Array.isArray(el) ? el[0] : el
      return node && node.closest ? node.closest('.fda-chart-box') : null
    },
    isChartFullscreen (refName) {
      return this.fullscreenChartRef === refName
    },
    async toggleChartFullscreen (refName) {
      const box = this.chartBoxEl(refName)
      if (!box) return
      const active = document.fullscreenElement || document.webkitFullscreenElement
      try {
        if (active === box) {
          if (document.exitFullscreen) await document.exitFullscreen()
          else if (document.webkitExitFullscreen) document.webkitExitFullscreen()
        } else {
          if (active) {
            if (document.exitFullscreen) await document.exitFullscreen()
            else if (document.webkitExitFullscreen) document.webkitExitFullscreen()
          }
          if (box.requestFullscreen) await box.requestFullscreen()
          else if (box.webkitRequestFullscreen) box.webkitRequestFullscreen()
          this.fullscreenChartRef = refName
        }
      } catch (err) {
        console.warn('chart fullscreen failed', err)
      }
      this.$nextTick(() => this.resizeCharts())
    },
    onFullscreenChange () {
      const active = document.fullscreenElement || document.webkitFullscreenElement
      if (!active) {
        this.fullscreenChartRef = null
      } else {
        const match = Object.keys(this.charts || {}).find(ref => this.chartBoxEl(ref) === active)
        if (match) this.fullscreenChartRef = match
      }
      this.$nextTick(() => {
        this.resizeCharts()
        requestAnimationFrame(() => this.resizeCharts())
      })
    },
    formatMarkValue (value) {
      const num = Number(value)
      if (!Number.isFinite(num)) return ''
      const abs = Math.abs(num)
      if (abs >= 1000) return num.toFixed(0)
      if (abs >= 100) return num.toFixed(1)
      if (abs >= 10) return num.toFixed(2)
      return num.toFixed(3)
    },
    buildMarkLabel (name, value) {
      const formatted = this.formatMarkValue(value)
      return formatted ? `${name} ${formatted}` : String(name || '')
    },
    resizeCharts () {
      Object.values(this.charts).forEach(chart => chart && chart.resize())
    }
  }
}
</script>

<style scoped lang="less">
.fda-page {
  padding: 16px 20px 24px;
  min-height: calc(100vh - 120px);
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow-x: hidden;
}

::v-deep .ant-spin-nested-loading,
::v-deep .ant-spin-container {
  width: 100%;
}

.fda-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.fda-kicker {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(0, 0, 0, 0.45);
  margin-bottom: 4px;
}

.fda-header h1 {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 650;
  color: rgba(0, 0, 0, 0.88);
}

.fda-header p {
  margin: 0;
  max-width: 720px;
  color: rgba(0, 0, 0, 0.55);
}

.fda-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.fda-picker-label {
  color: rgba(0, 0, 0, 0.55);
}

.fda-tabs {
  margin-bottom: 12px;
}

.fda-panel,
.fda-empty {
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  padding: 16px;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.fda-empty {
  color: rgba(0, 0, 0, 0.45);
  text-align: center;
  padding: 48px 16px;
}

.fda-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.fda-metric {
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #edf0f4;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.fda-metric span {
  font-size: 12px;
  color: #7c8ca1;
}

.fda-metric strong {
  font-size: 18px;
  color: #20324a;
  font-variant-numeric: tabular-nums;
}

.fda-metric-price {
  border-color: #91caff;
  background: #f0f7ff;
}

.fda-metric-price strong {
  font-size: 22px;
  color: #1677ff;
}

.fda-section h3,
.fda-chart-box h3 {
  margin: 0;
  font-size: 14px;
  color: #26364c;
}

.fda-chart-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.fda-history-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.fda-history-slider {
  margin: 4px 0 16px;
  padding: 0 8px;
}

.fda-history-slider-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
  color: rgba(0, 0, 0, 0.45);
  font-size: 13px;
}

.fda-history-slider-meta strong {
  color: rgba(0, 0, 0, 0.85);
  font-weight: 600;
}

.fda-chart-history {
  height: 420px;
}

.fda-metrics-gex {
  margin-bottom: 16px;
}

.fda-analysis {
  margin: 0;
  padding-left: 18px;
  color: rgba(0, 0, 0, 0.75);
  line-height: 1.7;
}

.fda-muted {
  color: rgba(0, 0, 0, 0.45);
}

.fda-charts {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  width: 100%;
}

.fda-chart-box-wide {
  grid-column: 1 / -1;
}

.fda-charts.fda-charts-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.fda-charts.fda-charts-options .fda-chart-box,
.fda-charts.fda-charts-options .fda-chart-box-wide {
  width: 100%;
  min-width: 0;
}

.fda-chart-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.fda-chart-box:fullscreen,
.fda-chart-box:-webkit-full-screen {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  padding: 16px 20px;
  background: #fff;
  display: flex;
  flex-direction: column;
  overflow: auto;
}

.fda-chart-box:fullscreen .fda-chart,
.fda-chart-box:-webkit-full-screen .fda-chart {
  flex: 1 1 auto;
  height: auto !important;
  min-height: calc(100vh - 72px);
}

.theme-dark .fda-chart-box:fullscreen,
.theme-dark .fda-chart-box:-webkit-full-screen {
  background: #0d0d0d;
}

.fda-chart-box {
  padding: 12px;
  border: 1px solid #edf0f4;
  border-radius: 8px;
  background: #fff;
  min-width: 0;
}

.fda-chart {
  width: 100%;
  min-width: 0;
  height: 300px;
}

.fda-chart-tall {
  height: 380px;
}

.fda-table {
  margin-top: 12px;
}

.fda-options-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.fda-ai {
  margin-top: 16px;
  background: transparent;
}

.positive { color: #16a34a !important; }
.negative { color: #dc2626 !important; }

.theme-dark {
  .fda-kicker,
  .fda-picker-label,
  .fda-muted {
    color: rgba(255, 255, 255, 0.45);
  }

  .fda-history-slider-meta {
    color: rgba(255, 255, 255, 0.45);
  }

  .fda-history-slider-meta strong {
    color: rgba(255, 255, 255, 0.88);
  }

  .fda-header h1 {
    color: rgba(255, 255, 255, 0.92);
  }

  .fda-header p,
  .fda-analysis {
    color: rgba(255, 255, 255, 0.65);
  }

  .fda-panel,
  .fda-empty,
  .fda-chart-box {
    background: rgba(255, 255, 255, 0.03);
    border-color: rgba(255, 255, 255, 0.08);
  }

  .fda-metric {
    background: #0d0d0d;
    border-color: rgba(255, 255, 255, 0.1);
  }

  .fda-metric strong,
  .fda-section h3,
  .fda-chart-box h3 {
    color: rgba(255, 255, 255, 0.88);
  }
}
</style>

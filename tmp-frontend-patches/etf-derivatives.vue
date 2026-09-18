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
          <div class="fda-metric" v-for="item in etfMetricCards" :key="item.key">
            <span>{{ item.label }}</span>
            <strong>{{ item.display }}</strong>
          </div>
        </div>
        <div class="fda-charts fda-charts-etf">
          <div class="fda-chart-box">
            <div class="fda-chart-head">
              <h3>{{ $t('marketComposite.etf.metrics.priceTrend') }}</h3>
              <a-button size="small" @click="openHistory('etf.price')">{{ $t('marketComposite.futures.history') }}</a-button>
            </div>
            <div ref="etfPriceChart" class="fda-chart" />
          </div>
          <div class="fda-chart-box">
            <div class="fda-chart-head">
              <h3>{{ $t('marketComposite.etf.metrics.volumeAmountTrend') }}</h3>
              <a-button size="small" @click="openHistory('etf.volume')">{{ $t('marketComposite.futures.history') }}</a-button>
            </div>
            <div ref="etfVolumeChart" class="fda-chart" />
          </div>
          <div class="fda-chart-box">
            <div class="fda-chart-head">
              <h3>{{ $t('marketComposite.etf.metrics.scaleTrend') }}</h3>
              <a-button size="small" @click="openHistory('etf.scale')">{{ $t('marketComposite.futures.history') }}</a-button>
            </div>
            <div ref="etfScaleChart" class="fda-chart" />
          </div>
          <div class="fda-chart-box">
            <div class="fda-chart-head">
              <h3>{{ $t('marketComposite.etf.metrics.feeProfitTrend') }}</h3>
              <a-button size="small" @click="openHistory('etf.metrics')">{{ $t('marketComposite.futures.history') }}</a-button>
            </div>
            <div ref="etfFeeProfitChart" class="fda-chart" />
          </div>
        </div>
        <p v-if="etfMetricsNote" class="fda-muted fda-etf-note">{{ etfMetricsNote }}</p>
        <div v-if="etfHoldings.length" class="fda-section fda-constituents">
          <h3>{{ $t('marketComposite.etf.metrics.constituentList') }}</h3>
          <p v-if="etfHoldingsMeta" class="fda-muted">{{ etfHoldingsMeta }}</p>
          <a-table
            class="fda-table"
            size="small"
            :pagination="etfHoldingsPagination"
            :columns="etfConstituentColumns"
            :data-source="etfHoldings"
            row-key="code"
          />
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
                <a-button size="small" @click="openHistory('futures.term')">{{ $t('marketComposite.futures.history') }}</a-button>
              </div>
              <div ref="termChart" class="fda-chart" />
            </div>
            <div class="fda-chart-box">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.futures.monthlyActivity') }}</h3>
                <a-button size="small" @click="openHistory('futures.activity')">{{ $t('marketComposite.futures.history') }}</a-button>
              </div>
              <div ref="activityChart" class="fda-chart fda-chart-tall" />
            </div>
            <div class="fda-chart-box">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.futures.optionsNotional') }}</h3>
                <a-button size="small" @click="openHistory('futures.notional')">{{ $t('marketComposite.futures.history') }}</a-button>
              </div>
              <div ref="notionalChart" class="fda-chart" />
            </div>
            <div class="fda-chart-box">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.futures.optionsPremium') }}</h3>
                <a-button size="small" @click="openHistory('futures.premium')">{{ $t('marketComposite.futures.history') }}</a-button>
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
              <strong>{{ fmt(optionsData && (optionsData.current_price || optionsData.underlying), 3, true) }}</strong>
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

          <div class="fda-metrics fda-metrics-capital" data-testid="etf-options-capital-summary">
            <div class="fda-metric" v-for="item in capitalSummaryMetrics" :key="item.key">
              <span>{{ item.label }}</span>
              <strong>{{ item.display }}</strong>
            </div>
          </div>

          <div class="fda-charts fda-charts-options">
            <div class="fda-chart-box fda-chart-box-wide">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.oiDist') }}</h3>
                <a-button size="small" @click="openHistory('options.oi')">{{ $t('marketComposite.futures.history') }}</a-button>
              </div>
              <div ref="oiChart" class="fda-chart fda-chart-tall" />
            </div>
            <div class="fda-chart-box fda-chart-box-wide">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.gexCallPutDist') }}</h3>
                <a-button size="small" @click="openHistory('options.gexCallPut')">{{ $t('marketComposite.futures.history') }}</a-button>
              </div>
              <div ref="gexCallPutChart" class="fda-chart fda-chart-tall" />
            </div>
            <div class="fda-chart-box fda-chart-box-wide">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.gexDist') }}</h3>
                <a-button size="small" @click="openHistory('options.gex')">{{ $t('marketComposite.futures.history') }}</a-button>
              </div>
              <div ref="gexChart" class="fda-chart fda-chart-tall" />
            </div>
            <div class="fda-chart-box fda-chart-box-wide">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.timeValueYield') }}</h3>
                <a-button size="small" @click="openHistory('options.tv')">{{ $t('marketComposite.futures.history') }}</a-button>
              </div>
              <div ref="tvYieldChart" class="fda-chart fda-chart-tall" />
            </div>
            <div class="fda-chart-box fda-chart-box-wide">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.capitalCurve') }}</h3>
                <a-button size="small" @click="openHistory('options.capital')">{{ $t('marketComposite.futures.history') }}</a-button>
              </div>
              <div ref="capitalCurveChart" class="fda-chart fda-chart-tall" />
            </div>
            <div class="fda-chart-box">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.ivSmile') }}</h3>
                <a-button size="small" @click="openHistory('options.iv')">{{ $t('marketComposite.futures.history') }}</a-button>
              </div>
              <div ref="smileChart" class="fda-chart" />
            </div>
            <div class="fda-chart-box">
              <div class="fda-chart-head">
                <h3>{{ $t('marketComposite.futures.options.maxPain') }}</h3>
                <a-button size="small" @click="openHistory('options.maxPain')">{{ $t('marketComposite.futures.history') }}</a-button>
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
      :width="(isGexFamilyHistory || isIvHistory || isMaxPainHistory) ? 1100 : 920"
      destroy-on-close
      @cancel="closeHistory"
    >
      <div class="fda-history-toolbar">
        <template v-if="isPlaybackHistory">
          <span>回看条数</span>
          <a-radio-group v-model="historyBars" button-style="solid" size="small" @change="loadHistory">
            <a-radio-button :value="30">30</a-radio-button>
            <a-radio-button :value="60">60</a-radio-button>
            <a-radio-button :value="90">90</a-radio-button>
            <a-radio-button :value="240">240</a-radio-button>
          </a-radio-group>
          <span>周期</span>
          <a-radio-group v-model="historyInterval" button-style="solid" size="small" @change="loadHistory">
            <a-radio-button value="1m">1m</a-radio-button>
            <a-radio-button value="30m">30m</a-radio-button>
            <a-radio-button value="day">日</a-radio-button>
            <a-radio-button value="week">周</a-radio-button>
          </a-radio-group>
        </template>
        <template v-else>
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
        </template>
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
        <div
          ref="historyChart"
          class="fda-chart"
          :class="(isGexFamilyHistory || isIvHistory || isMaxPainHistory) ? 'fda-chart-history-gex' : 'fda-chart-history'"
        />
        <div
          v-show="isGexFamilyHistory || isIvHistory || isMaxPainHistory"
          ref="historyLevelsChart"
          class="fda-chart fda-chart-history-levels"
        />
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
import {
  buildCallPutGexTrendSeries,
  buildCallPutStackedGexSeries as createCallPutStackedGexSeries,
  buildOiStrikeSeries,
  buildStackedNetGexSeries as createStackedNetGexSeries,
  callPutValueAxis
} from './gex-chart-series'
import {
  buildStrikeMarkLineData as createStrikeMarkLineData,
  markLineXValues,
  strikeValueAxis
} from './strike-mark-lines'

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
      historyVisible: false,
      historyLoading: false,
      historyKey: '',
      historyDays: 90,
      historyFrequency: 'week',
      historyBars: 60,
      historyInterval: 'day',
      historyNote: '',
      historyTitle: '',
      historySlices: [],
      historySliceIndex: 0,
      historyLevelsSeries: [],
      historyNearMonthIvKlines: [],
      historyNearMonthMaxPainSeries: [],
      etfHistoryPoints: [],
      etfMetricsNote: ''
    }
  },
  computed: {
    ...mapState({
      navTheme: state => state.app.theme
    }),
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
    isEtfMetricsHistory () {
      return String(this.historyKey || '').startsWith('etf.')
    },
    historySliceLabel () {
      const slice = this.historySlices[this.historySliceIndex]
      return (slice && (slice.label || slice.ts || slice.date)) || '--'
    },
    isDarkTheme () {
      return this.navTheme === 'dark' || this.navTheme === 'realdark'
    },
    etfSpot () {
      return (this.spotData && this.spotData.spot && this.spotData.spot.etf) || {}
    },
    etfHoldings () {
      const etf = this.etfSpot
      return etf.holdings || etf.holdings_sample || []
    },
    etfHoldingsMeta () {
      const etf = this.etfSpot
      const parts = []
      if (etf.holdings_count) {
        parts.push(`${etf.holdings_count}${this.$t('marketComposite.etf.metrics.constituentCountUnit')}`)
      }
      if (etf.holdings_quarter) parts.push(etf.holdings_quarter)
      if (etf.pe_coverage) {
        parts.push(`${this.$t('marketComposite.etf.metrics.peCoverage')}: ${etf.pe_coverage}`)
      }
      if (etf.margin_coverage) {
        parts.push(`${this.$t('marketComposite.etf.metrics.marginCoverage')}: ${etf.margin_coverage}`)
      }
      return parts.join(' · ')
    },
    etfHoldingsPagination () {
      return {
        pageSize: 20,
        showSizeChanger: true,
        pageSizeOptions: ['20', '50', '100'],
        showTotal: total => `${total}`
      }
    },
    etfMetricCards () {
      const etf = this.etfSpot
      const fee = etf.total_fee_pct
      const feeParts = []
      if (etf.management_fee_pct != null) feeParts.push(`${this.fmt(etf.management_fee_pct, 2)}%`)
      if (etf.custodian_fee_pct != null) feeParts.push(`${this.fmt(etf.custodian_fee_pct, 2)}%`)
      const feeDisplay = fee != null
        ? `${this.fmt(fee, 2)}%${feeParts.length ? ` (${feeParts.join('+')})` : ''}`
        : '-'
      return [
        { key: 'scale', label: this.$t('marketComposite.etf.metrics.scale'), display: this.fmtMoney(etf.scale) },
        { key: 'price', label: this.$t('marketComposite.etf.metrics.price'), display: this.fmt(this.spotData && this.spotData.spot_price, 4) },
        { key: 'volume', label: this.$t('marketComposite.etf.metrics.volume'), display: this.fmtCompact(etf.volume) },
        { key: 'amount', label: this.$t('marketComposite.etf.metrics.amount'), display: this.fmtMoney(etf.amount) },
        { key: 'fee', label: this.$t('marketComposite.etf.metrics.fee'), display: feeDisplay },
        { key: 'profit', label: this.$t('marketComposite.etf.metrics.constituentProfit'), display: this.fmtMoney(etf.constituent_profit_sum) },
        { key: 'holdingValue', label: this.$t('marketComposite.etf.metrics.constituentMarketValue'), display: this.fmtMoney(etf.constituent_market_value_sum) },
        { key: 'marketCap', label: this.$t('marketComposite.etf.metrics.constituentMarketCap'), display: this.fmtMoney(etf.constituent_market_cap_sum) },
        { key: 'avgMargin', label: this.$t('marketComposite.etf.metrics.avgProfitMargin'), display: etf.avg_profit_margin != null ? `${this.fmt(etf.avg_profit_margin, 2)}%` : '-' },
        { key: 'avgPe', label: this.$t('marketComposite.etf.metrics.avgPe'), display: etf.avg_pe != null ? this.fmt(etf.avg_pe, 2) : '-' },
        { key: 'iopv', label: 'IOPV', display: this.fmt(etf.iopv, 4) },
        { key: 'premium', label: this.$t('marketComposite.etf.metrics.premiumRate'), display: etf.premium_rate != null ? `${this.fmt(etf.premium_rate, 2)}%` : '-' }
      ]
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
    etfConstituentColumns () {
      return [
        { title: this.$t('marketComposite.etf.metrics.colCode'), dataIndex: 'code', width: 92 },
        { title: this.$t('marketComposite.etf.metrics.colName'), dataIndex: 'name', ellipsis: true },
        {
          title: this.$t('marketComposite.etf.metrics.colWeight'),
          dataIndex: 'weight_pct',
          width: 88,
          customRender: v => (v != null ? `${this.fmt(v, 2)}%` : '-')
        },
        {
          title: this.$t('marketComposite.etf.metrics.colHoldingValue'),
          dataIndex: 'market_value',
          customRender: v => this.fmtMoney(v)
        },
        {
          title: this.$t('marketComposite.etf.metrics.colShares'),
          dataIndex: 'shares',
          customRender: v => this.fmtCompact(v)
        },
        {
          title: this.$t('marketComposite.etf.metrics.colNetProfit'),
          dataIndex: 'net_profit',
          customRender: v => this.fmtMoney(v)
        },
        {
          title: this.$t('marketComposite.etf.metrics.colMarketCap'),
          dataIndex: 'market_cap',
          customRender: v => this.fmtMoney(v)
        },
        {
          title: this.$t('marketComposite.etf.metrics.colPe'),
          dataIndex: 'pe_ratio',
          width: 72,
          customRender: v => (v != null ? this.fmt(v, 2) : '-')
        },
        {
          title: this.$t('marketComposite.etf.metrics.colProfitMargin'),
          dataIndex: 'profit_margin',
          width: 96,
          customRender: v => (v != null ? `${this.fmt(v, 2)}%` : '-')
        }
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
      const s = (this.optionsData && this.optionsData.gex_summary) || {}
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
  },
  beforeDestroy () {
    window.removeEventListener('resize', this.resizeCharts)
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
    fmt (value, digits = 2, fixed = false) {
      if (value === null || value === undefined || value === '') return '-'
      const n = Number(value)
      if (!Number.isFinite(n)) return '-'
      return n.toLocaleString(undefined, {
        maximumFractionDigits: digits,
        minimumFractionDigits: fixed ? digits : 0
      })
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
    fmtCompact (value) {
      if (value === null || value === undefined || value === '') return '-'
      const n = Number(value)
      if (!Number.isFinite(n)) return '-'
      const abs = Math.abs(n)
      if (abs >= 1e8) return `${(n / 1e8).toFixed(2)}亿`
      if (abs >= 1e4) return `${(n / 1e4).toFixed(2)}万`
      return this.fmt(n, 0)
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
        await this.loadEtfMetricsHistory()
      } catch (e) {
        this.$message.error((e && e.message) || this.$t('marketComposite.futures.loadFailed'))
      } finally {
        this.loadingTab = false
      }
    },
    async loadEtfMetricsHistory () {
      if (!this.selectedRoot) return
      try {
        const res = await getChartHistory({
          root: this.spotRequestRoot(),
          chart: 'etf.metrics',
          days: 180,
          frequency: 'day',
          ...this.etfScopeParams()
        })
        const data = (res && res.data) || {}
        this.etfHistoryPoints = data.points || []
        this.etfMetricsNote = data.note || ''
        this.$nextTick(() => {
          this.renderEtfMetricsCharts()
          requestAnimationFrame(() => this.resizeCharts())
        })
      } catch (e) {
        this.etfHistoryPoints = []
        this.etfMetricsNote = ''
      }
    },
    renderEtfMetricsCharts () {
      const points = this.etfHistoryPoints || []
      const dates = points.map(p => p.date)
      const axisLabel = { color: this.chartText, hideOverlap: true }
      const splitLine = { lineStyle: { color: this.chartGrid, type: 'dashed' } }

      const price = this.ensureChart('etfPriceChart')
      if (price) {
        price.setOption({
          ...this.baseChartOption(),
          grid: { left: 52, right: 24, top: 36, bottom: 36 },
          xAxis: { type: 'category', data: dates, axisLabel },
          yAxis: { type: 'value', scale: true, splitLine },
          series: [{
            name: this.$t('marketComposite.etf.metrics.price'),
            type: 'line',
            showSymbol: false,
            data: points.map(p => p.price),
            itemStyle: { color: '#1677ff' }
          }]
        }, true)
      }

      const volume = this.ensureChart('etfVolumeChart')
      if (volume) {
        volume.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          grid: { left: 52, right: 56, top: 40, bottom: 36 },
          xAxis: { type: 'category', data: dates, axisLabel },
          yAxis: [
            { type: 'value', name: this.$t('marketComposite.etf.metrics.volume'), splitLine },
            { type: 'value', name: this.$t('marketComposite.etf.metrics.amount'), splitLine: { show: false } }
          ],
          series: [
            {
              name: this.$t('marketComposite.etf.metrics.volume'),
              type: 'bar',
              data: points.map(p => p.volume),
              itemStyle: { color: '#69c0ff', opacity: 0.55 }
            },
            {
              name: this.$t('marketComposite.etf.metrics.amount'),
              type: 'line',
              yAxisIndex: 1,
              showSymbol: false,
              data: points.map(p => p.amount),
              itemStyle: { color: '#fa8c16' }
            }
          ]
        }, true)
      }

      const scale = this.ensureChart('etfScaleChart')
      if (scale) {
        scale.setOption({
          ...this.baseChartOption(),
          grid: { left: 56, right: 24, top: 36, bottom: 36 },
          xAxis: { type: 'category', data: dates, axisLabel },
          yAxis: { type: 'value', scale: true, splitLine },
          series: [{
            name: this.$t('marketComposite.etf.metrics.scale'),
            type: 'line',
            showSymbol: false,
            areaStyle: { opacity: 0.12 },
            data: points.map(p => p.scale),
            itemStyle: { color: '#13c2c2' }
          }]
        }, true)
      }

      const feeProfit = this.ensureChart('etfFeeProfitChart')
      if (feeProfit) {
        feeProfit.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          grid: { left: 56, right: 56, top: 40, bottom: 36 },
          xAxis: { type: 'category', data: dates, axisLabel },
          yAxis: [
            { type: 'value', name: this.$t('marketComposite.etf.metrics.fee'), splitLine },
            { type: 'value', name: this.$t('marketComposite.etf.metrics.constituentProfit'), splitLine: { show: false } }
          ],
          series: [
            {
              name: this.$t('marketComposite.etf.metrics.fee'),
              type: 'line',
              showSymbol: false,
              data: points.map(p => p.fee_pct),
              itemStyle: { color: '#722ed1' }
            },
            {
              name: this.$t('marketComposite.etf.metrics.constituentProfit'),
              type: 'line',
              yAxisIndex: 1,
              showSymbol: false,
              data: points.map(p => p.constituent_profit_sum),
              itemStyle: { color: '#eb2f96' }
            }
          ]
        }, true)
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
      return createStrikeMarkLineData(markDefs, strikes, {
        formatPrice: value => this.formatCurrentPrice(value),
        formatStrike: value => this.formatStrikeMark(value)
      })
    },

    buildStackedGexSeries (monthSeries, points, palette, buildMarks) {
      return createStackedNetGexSeries(monthSeries, points, palette, buildMarks)
    },
    applyCallPutGexChart (chart, monthSeries, points, buildMarks) {
      if (!chart) return
      const stacked = createCallPutStackedGexSeries(monthSeries, points, buildMarks)
      chart.setOption({
        ...this.baseChartOption(),
        legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
        grid: { left: 56, right: 36, top: 56, bottom: 40 },
        xAxis: strikeValueAxis(stacked.strikes, markLineXValues(stacked.series), {
          axisLabel: { color: this.chartText },
          axisLine: { onZero: true }
        }),
        yAxis: callPutValueAxis(stacked.valueRange, {
          splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } }
        }),
        series: stacked.series
      }, true)
    },

    renderOptionsCharts () {
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
          xAxis: strikeValueAxis(strikes, markLineXValues(strikeMarks), {
            axisLabel: { color: this.chartText }
          }),
          yAxis: { type: 'value', name: 'OI', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: buildOiStrikeSeries(points, strikeMarks)
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
          xAxis: strikeValueAxis(stacked.strikes, markLineXValues(stacked.series), {
            axisLabel: { color: this.chartText }
          }),
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

      const capital = this.ensureChart('capitalCurveChart')
      if (capital) {
        this.renderCapitalCurveChart(capital, this.optionsData.capital_curve)
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
    openHistory (chartKey) {
      this.historyKey = chartKey
      const titleMap = {
        'etf.metrics': this.$t('marketComposite.etf.metrics.historyAll'),
        'etf.price': this.$t('marketComposite.etf.metrics.priceTrend'),
        'etf.volume': this.$t('marketComposite.etf.metrics.volumeAmountTrend'),
        'etf.amount': this.$t('marketComposite.etf.metrics.volumeAmountTrend'),
        'etf.scale': this.$t('marketComposite.etf.metrics.scaleTrend'),
        'etf.fee': this.$t('marketComposite.etf.metrics.feeProfitTrend'),
        'etf.profit': this.$t('marketComposite.etf.metrics.feeProfitTrend'),
        'options.capital': this.$t('marketComposite.futures.options.capitalCurve'),
        'options.gex': this.$t('marketComposite.futures.options.gexDist'),
        'options.gexCallPut': this.$t('marketComposite.futures.options.gexCallPutDist')
      }
      this.historyTitle = `${this.$t('marketComposite.futures.history')} · ${titleMap[chartKey] || chartKey}`
      this.historySlices = []
      this.historySliceIndex = 0
      this.historyVisible = true
      this.$nextTick(() => this.loadHistory())
    },
    closeHistory () {
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
    historyTipFormatter (index) {
      const slice = this.historySlices[index]
      return (slice && (slice.label || slice.ts || slice.date)) || String(index)
    },
    onHistorySliceChange () {
      this.renderHistorySlice()
      if (this.isIvHistory) this.renderNearMonthIvKlines()
      if (this.isMaxPainHistory) this.renderNearMonthMaxPainTrend()
    },
    async loadHistory () {
      if (!this.selectedRoot || !this.historyKey) return
      this.historyLoading = true
      try {
        const params = {
          root: this.selectedRoot,
          chart: this.isGexCallPutHistory ? 'options.gex' : this.historyKey,
          month: this.selectedMonth || 'all',
          ...this.etfScopeParams()
        }
        if (this.isPlaybackHistory) {
          params.bars = this.historyBars
          params.interval = this.historyInterval
          params.frequency = this.historyInterval
        } else {
          params.days = this.historyDays
          params.frequency = this.historyFrequency
        }
        const res = await getChartHistory(params)
        const data = (res && res.data) || {}
        this.historyNote = data.note || ''
        this.historyLevelsSeries = data.levels_series || []
        this.historyNearMonthIvKlines = data.near_month_iv_klines || []
        this.historyNearMonthMaxPainSeries = data.near_month_max_pain_series || []
        if (data.mode === 'slices' || data.mode === 'gex_playback') {
          this.historySlices = data.slices || []
          this.historySliceIndex = Math.max(this.historySlices.length - 1, 0)
          this.$nextTick(() => {
            this.renderHistorySlice()
            if (this.isGexHistory) this.renderGexLevelsHistory()
            if (this.isGexCallPutHistory) this.renderCallPutGexTrend()
            if (this.isIvHistory) this.renderNearMonthIvKlines()
            if (this.isMaxPainHistory) this.renderNearMonthMaxPainTrend()
          })
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
    renderCallPutGexTrend () {
      const chart = this.ensureChart('historyLevelsChart')
      if (!chart) return
      const { labels, series, valueRange } = buildCallPutGexTrendSeries(this.historySlices || [])
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
        grid: { left: 56, right: 36, top: 48, bottom: 48 },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: { color: this.chartText, hideOverlap: true },
          axisLine: { onZero: true }
        },
        yAxis: callPutValueAxis(valueRange, {
          splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } }
        }),
        series: marked
      }, true)
      this.$nextTick(() => chart.resize())
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

    renderHistorySlice () {
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
          xAxis: strikeValueAxis(stacked.strikes, markLineXValues(stacked.series), {
            axisLabel: { color: this.chartText }
          }),
          yAxis: { type: 'value', name: 'GEX', splitLine: { lineStyle: { color: this.chartGrid, type: 'dashed' } } },
          series: stacked.series
        }, true)
        this.$nextTick(() => chart.resize())
        this.renderGexLevelsHistory()
        return
      }

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
        const summary = slice.gex_summary || {}
        const price = slice.current_price || slice.underlying || summary.underlying
        const markDefs = this.buildOptionsMarkDefs(summary, price)
        let strikes = points.map(p => String(p.strike))
        let series
        if (key === 'options.oi') {
          const strikeMarks = this.buildStrikeMarkLineData(markDefs, strikes)
          series = buildOiStrikeSeries(points, strikeMarks)
        } else {
          const stacked = this.buildStackedGexSeries(slice.month_series || [], points, ['#1677ff', '#52c41a', '#fa8c16', '#eb2f96', '#13c2c2', '#722ed1', '#2f54eb'], (labels) => this.buildStrikeMarkLineData(markDefs, labels))
          strikes = stacked.strikes
          series = stacked.series
        }
        chart.setOption({
          ...this.baseChartOption(),
          legend: { top: 0, textStyle: { color: this.chartText } },
          xAxis: strikeValueAxis(strikes, markLineXValues(series), {
            axisLabel: { color: this.chartText }
          }),
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
    renderHistoryChart (data) {
      const chart = this.ensureChart('historyChart')
      if (!chart) return
      if (data.mode === 'daily') {
        const points = data.points || []
        if (this.isEtfMetricsHistory) {
          this.renderEtfHistoryModal(chart, points)
          return
        }
        if (this.isCapitalHistory) {
          this.renderCapitalCurveChart(chart, { points }, 'date')
          return
        }
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
    renderEtfHistoryModal (chart, points) {
      const key = this.historyKey
      const dates = points.map(p => p.date)
      const axisLabel = { color: this.chartText, hideOverlap: true }
      const splitLine = { lineStyle: { color: this.chartGrid, type: 'dashed' } }
      let series = []
      let yAxis = { type: 'value', scale: true, splitLine }

      if (key === 'etf.price') {
        series = [{ name: this.$t('marketComposite.etf.metrics.price'), type: 'line', showSymbol: false, data: points.map(p => p.price) }]
      } else if (key === 'etf.scale') {
        series = [{ name: this.$t('marketComposite.etf.metrics.scale'), type: 'line', showSymbol: false, areaStyle: { opacity: 0.12 }, data: points.map(p => p.scale) }]
      } else if (key === 'etf.volume' || key === 'etf.amount') {
        yAxis = [
          { type: 'value', name: this.$t('marketComposite.etf.metrics.volume'), splitLine },
          { type: 'value', name: this.$t('marketComposite.etf.metrics.amount'), splitLine: { show: false } }
        ]
        series = [
          { name: this.$t('marketComposite.etf.metrics.volume'), type: 'bar', data: points.map(p => p.volume), itemStyle: { opacity: 0.45 } },
          { name: this.$t('marketComposite.etf.metrics.amount'), type: 'line', yAxisIndex: 1, showSymbol: false, data: points.map(p => p.amount) }
        ]
      } else if (key === 'etf.fee') {
        series = [{ name: this.$t('marketComposite.etf.metrics.fee'), type: 'line', showSymbol: false, data: points.map(p => p.fee_pct) }]
      } else if (key === 'etf.profit') {
        series = [{ name: this.$t('marketComposite.etf.metrics.constituentProfit'), type: 'line', showSymbol: false, data: points.map(p => p.constituent_profit_sum) }]
      } else {
        yAxis = [
          { type: 'value', name: this.$t('marketComposite.etf.metrics.price'), splitLine },
          { type: 'value', name: this.$t('marketComposite.etf.metrics.scale'), splitLine: { show: false } }
        ]
        series = [
          { name: this.$t('marketComposite.etf.metrics.price'), type: 'line', showSymbol: false, data: points.map(p => p.price) },
          { name: this.$t('marketComposite.etf.metrics.volume'), type: 'bar', data: points.map(p => p.volume), itemStyle: { opacity: 0.3 } },
          { name: this.$t('marketComposite.etf.metrics.scale'), type: 'line', yAxisIndex: 1, showSymbol: false, data: points.map(p => p.scale) },
          { name: this.$t('marketComposite.etf.metrics.fee'), type: 'line', showSymbol: false, data: points.map(p => p.fee_pct) },
          { name: this.$t('marketComposite.etf.metrics.constituentProfit'), type: 'line', yAxisIndex: 1, showSymbol: false, data: points.map(p => p.constituent_profit_sum) }
        ]
      }

      chart.setOption({
        ...this.baseChartOption(),
        legend: { top: 0, type: 'scroll', textStyle: { color: this.chartText } },
        grid: { left: 56, right: 56, top: 48, bottom: 40 },
        xAxis: { type: 'category', data: dates, axisLabel },
        yAxis,
        series
      }, true)
    },
    renderActiveCharts () {
      if (this.activeTab === 'index') this.renderFuturesCharts()
      if (this.activeTab === 'etf') this.renderEtfMetricsCharts()
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

.fda-chart-history-gex {
  height: 380px;
}

.fda-chart-history-levels {
  height: 280px;
  margin-top: 12px;
}

.fda-metrics-gex {
  margin-bottom: 12px;
}

.fda-metrics-capital {
  margin-bottom: 16px;
}

.fda-metrics-capital .fda-metric strong {
  font-size: 18px;
  letter-spacing: 0.01em;
}

.fda-etf-note {
  margin: 0 0 12px;
}

.fda-charts-etf {
  margin-bottom: 8px;
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
}

@media (min-width: 1100px) {
  .fda-charts {
    grid-template-columns: 1fr 1fr;
  }

  .fda-chart-box-wide {
    grid-column: 1 / -1;
  }
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

@media (min-width: 1100px) {
  .fda-charts.fda-charts-options {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .fda-charts.fda-charts-options .fda-chart-box-wide {
    flex: 0 0 100%;
    width: 100%;
  }

  .fda-charts.fda-charts-options .fda-chart-box:not(.fda-chart-box-wide) {
    flex: 1 1 calc(50% - 6px);
    width: calc(50% - 6px);
  }
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

import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { TrendingUp, ShieldCheck, Search, ChevronDown, Loader2 } from 'lucide-react';

const TIMEFRAMES = [
  { label: '1분', value: '1m' },
  { label: '3분', value: '3m' },
  { label: '5분', value: '5m' },
  { label: '15분', value: '15m' },
  { label: '30분', value: '30m' },
  { label: '1시간', value: '1h' },
  { label: '4시간', value: '4h' },
  { label: '1일', value: '1d' },
  { label: '1주일', value: '1w' },
];

const calculateEMA = (data, period) => {
  const k = 2 / (period + 1);
  let emaArray = [];
  let prevEMA = data[0];
  
  data.forEach((val, index) => {
    if (index === 0) {
      emaArray.push(val);
      prevEMA = val;
    } else {
      const currentEMA = (val - prevEMA) * k + prevEMA;
      emaArray.push(currentEMA);
      prevEMA = currentEMA;
    }
  });
  return emaArray;
};

export default function App() {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const goyaLineSeriesRef = useRef(null);
  const upperLineSeriesRef = useRef(null);
  const smartLineSeriesRef = useRef(null);

  const [allCoins, setAllCoins] = useState([]);
  const [selectedCoin, setSelectedCoin] = useState('XRPUSDT');
  const [searchTerm, setSearchTerm] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h');
  const [activeSignals, setActiveSignals] = useState([]);
  const [isLoadingCoins, setIsLoadingCoins] = useState(true);

  useEffect(() => {
    const fetchBinanceExchangeInfo = async () => {
      try {
        const res = await fetch('https://api.binance.com/api/v3/exchangeInfo');
        const data = await res.json();
        const usdtPairs = data.symbols
          .filter(s => s.quoteAsset === 'USDT' && s.status === 'TRADING')
          .map(s => ({ symbol: s.symbol, baseAsset: s.baseAsset }));
        setAllCoins(usdtPairs);
        setIsLoadingCoins(false);
      } catch (err) {
        setAllCoins([
          { symbol: 'BTCUSDT', baseAsset: 'BTC' },
          { symbol: 'ETHUSDT', baseAsset: 'ETH' },
          { symbol: 'XRPUSDT', baseAsset: 'XRP' }
        ]);
        setIsLoadingCoins(false);
      }
    };
    fetchBinanceExchangeInfo();
  }, []);

  const filteredCoins = allCoins.filter(coin => 
    coin.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
    coin.baseAsset.toLowerCase().includes(searchTerm.toLowerCase())
  );

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 520,
      layout: {
        background: { color: '#131722' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#1f293d' },
        horzLines: { color: '#1f293d' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 12,
        barSpacing: 10,
        fixLeftEdge: false,
        fixRightEdge: false,
        lockVisibleTimeRangeOnResize: true,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
      localization: {
        timeFormatter: (time) => {
          const date = new Date(time * 1000);
          const hours = String(date.getUTCHours()).padStart(2, '0');
          const minutes = String(date.getUTCMinutes()).padStart(2, '0');
          const month = date.getUTCMonth() + 1;
          const day = date.getUTCDate();
          return `${month}월 ${day}일 ${hours}:${minutes}`;
        },
      },
    });

    const upperLineSeries = chart.addLineSeries({
      color: 'rgba(38, 166, 154, 0.7)',
      lineWidth: 1,
      title: 'Upper Line',
    });

    const smartLineSeries = chart.addLineSeries({
      color: 'yellow',
      lineWidth: 1.5,
      title: 'Smart Line',
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    const goyaLineSeries = chart.addLineSeries({
      color: '#ec4899', 
      lineWidth: 2,
      title: 'Goya Line',
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    goyaLineSeriesRef.current = goyaLineSeries;
    upperLineSeriesRef.current = upperLineSeries;
    smartLineSeriesRef.current = smartLineSeries;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    const fetchChartData = async () => {
      try {
        const res = await fetch(`https://api.binance.com/api/v3/klines?symbol=${selectedCoin}&interval=${selectedTimeframe}&limit=250`);
        const data = await res.json();
        
        if (!Array.isArray(data)) return;

        const opens = data.map(item => parseFloat(item[1]));
        const highs = data.map(item => parseFloat(item[2]));
        const lows = data.map(item => parseFloat(item[3]));
        const closes = data.map(item => parseFloat(item[4]));

        const goyaValues = calculateEMA(closes, 7);
        const smartValues = calculateEMA(closes, 25);

        const formattedCandles = [];
        const goyaLineData = [];
        const smartLineData = [];
        const upperLineData = [];
        const markers = [];

        let lastSignalType = null;
        let lastSignalIndex = -99;

        data.forEach((item, index) => {
          const time = (item[0] / 1000) + (9 * 60 * 60);
          const open = opens[index];
          const high = highs[index];
          const low = lows[index];
          const close = closes[index];

          formattedCandles.push({ time, open, high, low, close });

          const goyaVal = goyaValues[index];
          const smartVal = smartValues[index];

          goyaLineData.push({ time, value: goyaVal });

          const sliceHigh = highs.slice(Math.max(0, index - 15), index + 1);
          const sliceLow = lows.slice(Math.max(0, index - 15), index + 1);
          upperLineData.push({ time, value: Math.max(...sliceHigh) * 0.999 });
          smartLineData.push({ time, value: Math.min(...sliceLow) * 1.001 });

          if (index > 10 && (index - lastSignalIndex >= 2)) {
            const isGreen = close > open;
            const isRed = close < open;

            const isLL = isGreen && (close > goyaVal) && (goyaVal >= smartVal);
            const isSS = isRed && (close < goyaVal) && (goyaVal <= smartVal);

            if (isLL && lastSignalType !== 'LL') {
              markers.push({
                time,
                position: 'belowBar',
                color: '#22c55e',
                shape: 'arrowUp',
                text: 'LL',
              });
              lastSignalType = 'LL';
              lastSignalIndex = index;
            } else if (isSS && lastSignalType !== 'SS') {
              markers.push({
                time,
                position: 'aboveBar',
                color: '#ef4444',
                shape: 'arrowDown',
                text: 'SS',
              });
              lastSignalType = 'SS';
              lastSignalIndex = index;
            }
          }
        });

        candleSeries.setData(formattedCandles);
        goyaLineSeries.setData(goyaLineData);
        upperLineSeries.setData(upperLineData);
        smartLineSeries.setData(smartLineData);
        
        candleSeries.setMarkers(markers);

        if (formattedCandles.length > 0) {
          setCurrentPrice(formattedCandles[formattedCandles.length - 1].close);
        }
        setIsConnected(true);
        setActiveSignals([
          { type: lastSignalType === 'LL' ? 'LL (Long)' : 'SS (Short)', time: '실시간 적용됨', desc: `${selectedCoin} 고야선 트랩 필터 적용 완료` }
        ]);
      } catch (err) {
        setIsConnected(false);
      }
    };

    fetchChartData();
    const intervalId = setInterval(fetchChartData, 5000);

    return () => {
      window.removeEventListener('resize', handleResize);
      clearInterval(intervalId);
      chart.remove();
    };
  }, [selectedCoin, selectedTimeframe]);

  return (
    <div className="min-h-screen bg-[#0b0e11] text-white p-4 font-sans">
      <header className="bg-[#131722] p-4 rounded-xl border border-gray-800 shadow-xl mb-4 flex flex-col xl:flex-row justify-between items-center gap-4 relative z-20">
        <div className="flex items-center space-x-4 w-full xl:w-auto justify-between xl:justify-start">
          <div className="relative">
            <button 
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex items-center gap-2 bg-[#1e222d] hover:bg-gray-800 text-white px-3.5 py-2 rounded-lg border border-gray-700 font-bold transition-all shadow"
            >
              <span className="text-pink-500 font-mono text-base">⚡</span>
              <span>{selectedCoin}</span>
              <ChevronDown className="w-4 h-4 text-gray-400" />
            </button>

            {isDropdownOpen && (
              <div className="absolute top-12 left-0 w-72 bg-[#191c26] border border-gray-700 rounded-xl shadow-2xl p-2 z-50">
                <div className="relative mb-2 px-1 pt-1">
                  <Search className="absolute left-4 top-3.5 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="코인 검색..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-[#131722] text-white text-xs pl-9 pr-3 py-2 rounded-lg border border-gray-700 focus:outline-none uppercase"
                    autoFocus
                  />
                </div>
                <div className="max-h-72 overflow-y-auto space-y-1 pr-1">
                  {isLoadingCoins ? (
                    <div className="flex items-center justify-center py-6 text-xs text-gray-400 gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-500" /> 로딩 중...
                    </div>
                  ) : (
                    filteredCoins.map((coin) => (
                      <div
                        key={coin.symbol}
                        onClick={() => {
                          setSelectedCoin(coin.symbol);
                          setIsDropdownOpen(false);
                          setSearchTerm('');
                        }}
                        className={`w-full text-left px-3 py-2.5 text-xs rounded-lg transition-colors flex justify-between items-center cursor-pointer ${
                          selectedCoin === coin.symbol ? 'bg-blue-600 text-white font-bold' : 'text-gray-300 hover:bg-[#232837]'
                        }`}
                      >
                        <span className="font-mono">{coin.symbol}</span>
                        <span className="text-[10px] text-gray-400 uppercase">{coin.baseAsset}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          <div>
            <h1 className="text-sm md:text-base font-bold text-gray-100 flex items-center gap-2">
              고야 스마트 프리미엄 차트 <span className="text-xs text-pink-500 font-mono">(Pro Signal v3.3)</span>
            </h1>
          </div>
        </div>

        <div className="flex overflow-x-auto w-full xl:w-auto max-w-full gap-1 bg-[#1e222d] p-1.5 rounded-lg border border-gray-700/60">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.value}
              onClick={() => setSelectedTimeframe(tf.value)}
              className={`px-3 py-1.5 text-xs rounded-md transition-all font-semibold whitespace-nowrap ${
                selectedTimeframe === tf.value
                  ? 'bg-red-600 text-white shadow-md ring-2 ring-red-500/40'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>

        <div className="flex items-center justify-between w-full xl:w-auto xl:justify-end space-x-3">
          <div className="text-right">
            <div className="text-lg md:text-xl font-bold font-mono text-white tracking-tight">
              {currentPrice ? `$${currentPrice.toLocaleString()}` : '불러오는 중...'}
            </div>
            <div className="flex items-center justify-end text-[11px] text-emerald-400 space-x-1">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>{isConnected ? '거짓 신호 필터 작동 중' : '연결 끊김'}</span>
            </div>
          </div>
        </div>
      </header>

      <div className="bg-[#131722] p-4 rounded-xl border border-gray-800 shadow-2xl mb-4 relative z-10">
        <div ref={chartContainerRef} className="w-full rounded-lg overflow-hidden" />
      </div>

      <div className="bg-[#131722] p-4 rounded-xl border border-gray-800 shadow-lg relative z-10">
        <h3 className="text-xs md:text-sm font-bold text-gray-200 mb-3 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" /> 프리미엄 스마트 시그널 모니터링 ({selectedCoin})
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {activeSignals.map((sig, idx) => (
            <div key={idx} className="flex justify-between items-center bg-[#1e222d] p-3 rounded-lg border border-gray-700/60">
              <div className="flex items-center gap-3">
                <span className={`px-2.5 py-1 text-xs font-bold rounded ${sig.type.includes('LL') ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'}`}>
                  {sig.type}
                </span>
                <span className="text-xs md:text-sm text-gray-200 font-medium">{sig.desc}</span>
              </div>
              <span className="text-xs text-gray-400 font-mono">{sig.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

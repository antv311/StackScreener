/* StackScreener — shared UI atoms, icons, logos, mock data */

// ============ ICONS ============
const Icon = ({ name, size = 18, stroke = 1.75 }) => {
  const s = size;
  const common = { width: s, height: s, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: stroke, strokeLinecap: 'round', strokeLinejoin: 'round' };
  const paths = {
    home: <><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></>,
    research: <><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>,
    logistics: <><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>,
    chevronLeft: <path d="m15 18-6-6 6-6"/>,
    chevronRight: <path d="m9 18 6-6-6-6"/>,
    chevronDown: <path d="m6 9 6 6 6-6"/>,
    arrowUpRight: <><path d="M7 17 17 7M7 7h10v10"/></>,
    globe: <><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10Z"/></>,
    chevronUp: <path d="m18 15-6-6-6 6"/>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    x: <><path d="M18 6 6 18M6 6l18 18" transform="scale(.75) translate(4 4)"/></>,
    close: <><path d="M18 6 6 18M6 6l12 12"/></>,
    bell: <><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></>,
    user: <><circle cx="12" cy="7" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    users: <><circle cx="9" cy="7" r="4"/><path d="M3 21a6 6 0 0 1 12 0M17 3a4 4 0 0 1 0 8M23 21a6 6 0 0 0-5-5.92"/></>,
    key: <><circle cx="7.5" cy="15.5" r="5.5"/><path d="m11 12 9-9M15 7l3 3M19 3l2 2"/></>,
    shield: <path d="M12 3 4 6v6c0 5 3.5 9 8 10 4.5-1 8-5 8-10V6l-8-3Z"/>,
    moon: <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"/>,
    sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></>,
    logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></>,
    play: <polygon points="6 4 20 12 6 20 6 4"/>,
    pause: <><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></>,
    refresh: <><path d="M3 12a9 9 0 0 1 15.5-6.3L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.5 6.3L3 16"/><path d="M3 21v-5h5"/></>,
    filter: <path d="M3 5h18l-7 9v6l-4-2v-4L3 5Z"/>,
    trend: <><path d="M3 17 9 11l4 4 8-8"/><path d="M16 7h5v5"/></>,
    check: <path d="m5 12 4 4 10-10"/>,
    copy: <><rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></>,
    eye: <><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12Z"/><circle cx="12" cy="12" r="3"/></>,
    eyeOff: <><path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a19.2 19.2 0 0 1 4.22-5.06M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a19.2 19.2 0 0 1-2.16 3.19M6.12 6.12 1 1M23 23l-5.12-5.12"/><path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/></>,
    trash: <><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14"/></>,
    edit: <><path d="M11 4H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-6"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5Z"/></>,
    calendar: <><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></>,
    pin: <><path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7Z"/><circle cx="12" cy="9" r="2.5"/></>,
    alert: <><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/></>,
    download: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5M12 15V3"/></>,
    zap: <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>,
    dollar: <><path d="M12 1v22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></>,
    spark: <><path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/></>,
    menu: <><path d="M3 6h18M3 12h18M3 18h18"/></>,
    link: <><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></>,
    sliders: <><path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3"/><path d="M1 14h6M9 8h6M17 16h6"/></>,
    barChart: <><path d="M3 3v18h18"/><rect x="7" y="12" width="3" height="6"/><rect x="12" y="8" width="3" height="10"/><rect x="17" y="4" width="3" height="14"/></>,
    lock: <><rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></>,
  };
  return <svg {...common}>{paths[name]}</svg>;
};

// ============ LOGOS / BRAND VARIANTS ============
const Logo = ({ variant = 'stacked-bars', size = 20, showWord = true }) => {
  const h = size;
  const accent = 'var(--accent)';
  const ink = 'var(--ink)';
  let mark = null;
  if (variant === 'stacked-bars') {
    mark = (
      <svg width={h} height={h} viewBox="0 0 24 24" fill="none">
        <rect x="2" y="14" width="4" height="7" rx="1" fill={accent}/>
        <rect x="8" y="9" width="4" height="12" rx="1" fill={accent} opacity=".75"/>
        <rect x="14" y="5" width="4" height="16" rx="1" fill={accent} opacity=".5"/>
        <rect x="20" y="2" width="2" height="19" rx="1" fill={ink} opacity=".25"/>
      </svg>
    );
  } else if (variant === 'chevron-stack') {
    mark = (
      <svg width={h} height={h} viewBox="0 0 24 24" fill="none">
        <path d="M4 8 L12 3 L20 8" stroke={accent} strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M4 14 L12 9 L20 14" stroke={accent} strokeWidth="2.2" fill="none" opacity=".7" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M4 20 L12 15 L20 20" stroke={accent} strokeWidth="2.2" fill="none" opacity=".4" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    );
  } else if (variant === 'ss-mono') {
    mark = (
      <svg width={h} height={h} viewBox="0 0 24 24" fill="none">
        <rect x="2" y="2" width="20" height="20" rx="5" fill={accent}/>
        <text x="12" y="16" textAnchor="middle" fontFamily="var(--font-mono)" fontWeight="800" fontSize="11" fill="var(--accent-ink)">SS</text>
      </svg>
    );
  } else if (variant === 'candle') {
    mark = (
      <svg width={h} height={h} viewBox="0 0 24 24" fill="none">
        <path d="M7 2v20M17 2v20" stroke={ink} strokeWidth="1.2" opacity=".35"/>
        <rect x="4" y="9" width="6" height="9" rx="1" fill={accent}/>
        <rect x="14" y="5" width="6" height="12" rx="1" fill={accent} opacity=".55"/>
      </svg>
    );
  }
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      {mark}
      {showWord && (
        <span style={{ fontWeight: 700, fontSize: Math.max(13, size * 0.72), letterSpacing: '-0.01em' }}>
          Stack<span style={{ color: 'var(--accent)' }}>Screener</span>
        </span>
      )}
    </span>
  );
};

// ============ MOCK DATA ============
const MOCK_HEATMAP_SECTORS = [
  { name: 'Technology', weight: 28, stocks: [
    { t: 'MSFT', c: 2.42, mc: 3100 }, { t: 'AAPL', c: 3.30, mc: 3500 },
    { t: 'NVDA', c: 1.27, mc: 2900 }, { t: 'GOOGL', c: 0.92, mc: 2100 },
    { t: 'META', c: 1.24, mc: 1450 }, { t: 'AVGO', c: 1.25, mc: 820 },
    { t: 'ORCL', c: 0.18, mc: 410 }, { t: 'ADBE', c: -0.52, mc: 260 },
    { t: 'CRM', c: 0.65, mc: 290 }, { t: 'CSCO', c: 0.08, mc: 230 },
    { t: 'IBM', c: 0.34, mc: 180 }, { t: 'INTC', c: 1.40, mc: 140 },
    { t: 'AMD', c: 0.88, mc: 260 }, { t: 'PLTR', c: 3.10, mc: 95 },
  ]},
  { name: 'Communication', weight: 9, stocks: [
    { t: 'NFLX', c: -0.68, mc: 390 }, { t: 'DIS', c: 0.22, mc: 180 },
    { t: 'T', c: 0.29, mc: 160 }, { t: 'VZ', c: -0.34, mc: 170 },
    { t: 'TMUS', c: 0.40, mc: 210 }, { t: 'CMCSA', c: 0.12, mc: 160 },
  ]},
  { name: 'Consumer Disc.', weight: 12, stocks: [
    { t: 'AMZN', c: 1.84, mc: 1900 }, { t: 'TSLA', c: 5.00, mc: 860 },
    { t: 'HD', c: 1.50, mc: 390 }, { t: 'MCD', c: -1.20, mc: 210 },
    { t: 'LOW', c: 0.42, mc: 150 }, { t: 'NKE', c: -0.88, mc: 120 },
    { t: 'SBUX', c: 0.22, mc: 110 },
  ]},
  { name: 'Healthcare', weight: 13, stocks: [
    { t: 'LLY', c: 2.38, mc: 720 }, { t: 'JNJ', c: 0.37, mc: 390 },
    { t: 'UNH', c: 0.92, mc: 510 }, { t: 'ABBV', c: -0.10, mc: 310 },
    { t: 'MRK', c: 0.18, mc: 290 }, { t: 'PFE', c: -1.40, mc: 160 },
    { t: 'TMO', c: 0.55, mc: 220 },
  ]},
  { name: 'Financial', weight: 12, stocks: [
    { t: 'JPM', c: 0.89, mc: 590 }, { t: 'BAC', c: 1.19, mc: 290 },
    { t: 'WFC', c: 0.61, mc: 210 }, { t: 'V', c: 0.55, mc: 540 },
    { t: 'MA', c: 0.42, mc: 420 }, { t: 'BRK-B', c: 0.53, mc: 920 },
    { t: 'GS', c: 0.77, mc: 150 }, { t: 'MS', c: 1.44, mc: 170 },
  ]},
  { name: 'Consumer Staples', weight: 7, stocks: [
    { t: 'WMT', c: 0.13, mc: 510 }, { t: 'COST', c: 0.06, mc: 340 },
    { t: 'PG', c: 2.20, mc: 400 }, { t: 'KO', c: -0.29, mc: 280 },
    { t: 'PEP', c: -1.29, mc: 230 },
  ]},
  { name: 'Energy', weight: 5, stocks: [
    { t: 'XOM', c: -5.21, mc: 470 }, { t: 'CVX', c: -4.41, mc: 290 },
    { t: 'COP', c: -3.80, mc: 130 },
  ]},
  { name: 'Industrials', weight: 8, stocks: [
    { t: 'GE', c: 1.70, mc: 180 }, { t: 'CAT', c: 0.30, mc: 180 },
    { t: 'RTX', c: 0.62, mc: 140 }, { t: 'DE', c: -1.14, mc: 110 },
    { t: 'BA', c: 3.82, mc: 130 },
  ]},
  { name: 'Utilities', weight: 3, stocks: [
    { t: 'NEE', c: -1.20, mc: 160 }, { t: 'DUK', c: -5.75, mc: 80 },
  ]},
  { name: 'Materials', weight: 3, stocks: [
    { t: 'LIN', c: 0.24, mc: 220 }, { t: 'SHW', c: -0.50, mc: 80 },
  ]},
];

const MOCK_SCREENER_ROWS = [
  { rank:1, ticker:'NVDA', company:'NVIDIA Corp', sector:'Technology', industry:'Semiconductors', country:'USA', mc:2900, pe:38.2, price:795.12, change:1.27, volume:44_120_000, score:94, signal:'supply_chain' },
  { rank:2, ticker:'TSM',  company:'Taiwan Semiconductor', sector:'Technology', industry:'Semiconductors', country:'TW', mc:920, pe:28.1, price:168.40, change:1.25, volume:18_420_000, score:92, signal:'supply_chain' },
  { rank:3, ticker:'AVGO', company:'Broadcom Inc', sector:'Technology', industry:'Semiconductors', country:'USA', mc:820, pe:32.4, price:1632.08, change:1.25, volume:2_140_000, score:89, signal:'congress_buy' },
  { rank:4, ticker:'LMT',  company:'Lockheed Martin', sector:'Industrials', industry:'Aerospace & Defense', country:'USA', mc:112, pe:18.5, price:472.10, change:0.84, volume:1_030_000, score:88, signal:'supply_chain' },
  { rank:5, ticker:'CAT',  company:'Caterpillar Inc', sector:'Industrials', industry:'Machinery', country:'USA', mc:180, pe:15.8, price:342.80, change:0.30, volume:2_880_000, score:86, signal:'inst_flow' },
  { rank:6, ticker:'LLY',  company:'Eli Lilly & Co', sector:'Healthcare', industry:'Pharmaceuticals', country:'USA', mc:720, pe:62.4, price:772.50, change:2.38, volume:3_220_000, score:85, signal:'inst_flow' },
  { rank:7, ticker:'DE',   company:'Deere & Company', sector:'Industrials', industry:'Machinery', country:'USA', mc:112, pe:14.0, price:402.30, change:-1.14, volume:1_510_000, score:84, signal:'supply_chain' },
  { rank:8, ticker:'MSFT', company:'Microsoft Corp', sector:'Technology', industry:'Software', country:'USA', mc:3100, pe:36.7, price:412.40, change:2.42, volume:22_300_000, score:83, signal:'dark_pool' },
  { rank:9, ticker:'AAPL', company:'Apple Inc', sector:'Technology', industry:'Hardware', country:'USA', mc:3500, pe:30.2, price:228.15, change:3.30, volume:52_240_000, score:82, signal:'congress_buy' },
  { rank:10, ticker:'AMZN', company:'Amazon.com Inc', sector:'Consumer Disc.', industry:'Internet Retail', country:'USA', mc:1900, pe:44.1, price:184.20, change:1.84, volume:34_810_000, score:81, signal:'inst_flow' },
  { rank:11, ticker:'MU',  company:'Micron Technology', sector:'Technology', industry:'Semiconductors', country:'USA', mc:128, pe:22.6, price:116.70, change:0.64, volume:11_400_000, score:80, signal:'supply_chain' },
  { rank:12, ticker:'BA',  company:'Boeing Co', sector:'Industrials', industry:'Aerospace & Defense', country:'USA', mc:130, pe:null, price:188.90, change:3.82, volume:7_920_000, score:79, signal:'congress_buy' },
  { rank:13, ticker:'XOM', company:'Exxon Mobil Corp', sector:'Energy', industry:'Oil & Gas', country:'USA', mc:470, pe:13.2, price:108.80, change:-5.21, volume:19_300_000, score:76, signal:null },
  { rank:14, ticker:'FCX', company:'Freeport-McMoRan', sector:'Materials', industry:'Copper', country:'USA', mc:68, pe:32.1, price:48.22, change:0.55, volume:12_100_000, score:75, signal:'supply_chain' },
  { rank:15, ticker:'GOOGL', company:'Alphabet Inc', sector:'Communication', industry:'Internet Services', country:'USA', mc:2100, pe:26.8, price:171.30, change:0.92, volume:20_140_000, score:74, signal:null },
  { rank:16, ticker:'JPM', company:'JPMorgan Chase', sector:'Financial', industry:'Banks', country:'USA', mc:590, pe:12.4, price:220.80, change:0.89, volume:9_200_000, score:73, signal:'inst_flow' },
  { rank:17, ticker:'PLTR', company:'Palantir Technologies', sector:'Technology', industry:'Software', country:'USA', mc:95, pe:211.0, price:42.80, change:3.10, volume:38_220_000, score:72, signal:'congress_buy' },
  { rank:18, ticker:'RTX', company:'RTX Corporation', sector:'Industrials', industry:'Aerospace & Defense', country:'USA', mc:140, pe:19.2, price:112.40, change:0.62, volume:3_880_000, score:71, signal:'supply_chain' },
];

const MOCK_CALENDAR_EVENTS = [
  { date: '2026-04-19', type: 'earnings', ticker: 'AAPL', title: 'Apple Q2 Earnings', est: 1.52 },
  { date: '2026-04-20', type: 'earnings', ticker: 'MSFT', title: 'Microsoft Q3 Earnings', est: 2.84 },
  { date: '2026-04-20', type: 'ipo', ticker: 'KLAR', title: 'Klarna Group IPO', lo: 18, hi: 22 },
  { date: '2026-04-21', type: 'split', ticker: 'NVDA', title: 'NVIDIA 10:1 Stock Split', ratio: '10:1' },
  { date: '2026-04-21', type: 'earnings', ticker: 'TSLA', title: 'Tesla Q1 Earnings', est: 0.68 },
  { date: '2026-04-22', type: 'economic', title: 'FOMC Rate Decision' },
  { date: '2026-04-22', type: 'earnings', ticker: 'META', title: 'Meta Q1 Earnings', est: 4.92 },
  { date: '2026-04-23', type: 'earnings', ticker: 'GOOGL', title: 'Alphabet Q1 Earnings', est: 1.78 },
  { date: '2026-04-23', type: 'ipo', ticker: 'STRP', title: 'Stripe Inc IPO', lo: 42, hi: 48 },
  { date: '2026-04-24', type: 'earnings', ticker: 'AMZN', title: 'Amazon Q1 Earnings', est: 0.98 },
  { date: '2026-04-24', type: 'split', ticker: 'CMG', title: 'Chipotle 50:1 Stock Split', ratio: '50:1' },
  { date: '2026-04-25', type: 'economic', title: 'Q1 GDP Advance Estimate' },
];

const MOCK_SUPPLY_EVENTS = [
  { id:1, title:'Red Sea Shipping Attacks', region:'Red Sea', country:'YE', lat:14.5, lon:43.0, severity:'CRITICAL', status:'active', type:'conflict', commodity:'shipping', summary:'Houthi attacks disrupting Bab-el-Mandeb corridor; 40% of Asia-Europe container traffic diverted around Cape of Good Hope.', sectors:['Consumer Disc.','Industrials','Energy'] },
  { id:2, title:'Taiwan Strait Tensions', region:'Taiwan Strait', country:'TW', lat:24.5, lon:121.0, severity:'HIGH', status:'active', type:'conflict', commodity:'semiconductors', summary:'Elevated PLA naval exercises raising insurance premiums; chip inventory buildup observed.', sectors:['Technology'] },
  { id:3, title:'Panama Canal Drought', region:'Panama Canal', country:'PA', lat:9.0, lon:-79.5, severity:'HIGH', status:'active', type:'weather', commodity:'shipping', summary:'Gatun Lake water levels forcing 35% reduction in daily transits through 2026.', sectors:['Consumer Disc.','Energy','Materials'] },
  { id:4, title:'Chile Copper Mine Strike', region:'Atacama', country:'CL', lat:-23.0, lon:-68.5, severity:'MEDIUM', status:'active', type:'labor', commodity:'copper', summary:'Escondida mine workers on strike; 5% of global copper supply offline.', sectors:['Materials','Technology'] },
  { id:5, title:'Suez Canal Congestion', region:'Suez Canal', country:'EG', lat:30.0, lon:32.5, severity:'MEDIUM', status:'monitoring', type:'accident', commodity:'shipping', summary:'Recurrent grounding incidents; carriers pricing in delay risk.', sectors:['Consumer Disc.','Industrials'] },
  { id:6, title:'Russia Sanctions (Nickel)', region:'Norilsk', country:'RU', lat:69.3, lon:88.2, severity:'HIGH', status:'active', type:'sanctions', commodity:'nickel', summary:'Secondary sanctions on Norilsk Nickel reshuffling EV battery supply chain.', sectors:['Materials','Consumer Disc.'] },
  { id:7, title:'Brazil Grain Logistics', region:'Mato Grosso', country:'BR', lat:-12.5, lon:-55.5, severity:'LOW', status:'active', type:'weather', commodity:'grain', summary:'Unseasonal rainfall slowing soy and corn export barges.', sectors:['Consumer Staples'] },
  { id:8, title:'ASML Lithography Delay', region:'Veldhoven', country:'NL', lat:51.4, lon:5.4, severity:'MEDIUM', status:'active', type:'factory_shutdown', commodity:'semiconductors', summary:'EUV tool delivery backlog extending to 18 months; chipmakers rationing capacity.', sectors:['Technology'] },
  { id:9, title:'Philippines Nickel Ban', region:'Surigao', country:'PH', lat:9.7, lon:125.5, severity:'MEDIUM', status:'monitoring', type:'sanctions', commodity:'nickel', summary:'Proposed export ban on raw nickel ore; Indonesia poised to capture share.', sectors:['Materials'] },
];

const MOCK_EVENT_STOCKS = {
  1: [
    { role:'impacted', ticker:'MSC', company:'MSC Industrial', cannot:'European auto parts on-time delivery', redirect:null },
    { role:'impacted', ticker:'HMC', company:'Honda Motor', cannot:'Europe-bound SUV shipments', redirect:null },
    { role:'beneficiary', ticker:'ZIM', company:'ZIM Integrated Shipping', cannot:null, redirect:'Cape route rate premiums' },
    { role:'beneficiary', ticker:'CP',  company:'Canadian Pacific Kansas', cannot:null, redirect:'North American trans-load demand' },
  ],
  2: [
    { role:'impacted', ticker:'TSM', company:'Taiwan Semiconductor', cannot:'Leading-edge node deliveries at scale', redirect:null },
    { role:'beneficiary', ticker:'INTC', company:'Intel Foundry', cannot:null, redirect:'Ohio & Arizona fab contracts' },
    { role:'beneficiary', ticker:'SSNLF', company:'Samsung Electronics', cannot:null, redirect:'Austin & Pyeongtaek capacity' },
  ],
  3: [
    { role:'impacted', ticker:'WMT', company:'Walmart Inc', cannot:'West Coast → East Coast transit', redirect:null },
    { role:'beneficiary', ticker:'UNP', company:'Union Pacific', cannot:null, redirect:'Intermodal rail volume' },
  ],
  4: [
    { role:'impacted', ticker:'BHP', company:'BHP Group', cannot:'Copper concentrate output', redirect:null },
    { role:'beneficiary', ticker:'FCX', company:'Freeport-McMoRan', cannot:null, redirect:'US-based copper supply' },
    { role:'beneficiary', ticker:'SCCO', company:'Southern Copper', cannot:null, redirect:'Peru production ramp' },
  ],
};

const MOCK_STOCK_PICKS = [
  { ticker:'NVDA', company:'NVIDIA Corp', price:795.12, score:94, change:1.27, trend:'up', sources:[
    { name:'Senate Stock Watcher', score:92, reason:'3 senators (both parties) disclosed purchases in last 14 days — combined ~$1.8M notional' },
    { name:'SEC Form 4', score:88, reason:'No insider selling; CFO exercised options and held' },
    { name:'Yahoo Finance', score:90, reason:'31 of 35 analysts at Buy/Strong Buy; target price raised 4× this month' },
    { name:'Options Flow', score:96, reason:'Unusual call sweeps at 820/850 strikes, 2–4 week expiries' },
  ]},
  { ticker:'TSM', company:'Taiwan Semiconductor', price:168.40, score:92, change:1.25, trend:'up', sources:[
    { name:'Senate Stock Watcher', score:85, reason:'2 recent senate disclosures, small positions' },
    { name:'SEC Form 4',           score:82, reason:'Minor insider buys at ADR level via affiliates' },
    { name:'Yahoo Finance',        score:94, reason:'Consensus PT raised to $210 after CapEx guidance' },
    { name:'Options Flow',         score:91, reason:'Sustained call skew, June/July expiries' },
  ]},
  { ticker:'LMT', company:'Lockheed Martin', price:472.10, score:88, change:0.84, trend:'up', sources:[
    { name:'Senate Stock Watcher', score:90, reason:'Armed Services members disclosed buys this quarter' },
    { name:'SEC Form 4',           score:84, reason:'CEO exercise-and-hold; no insider selling since Feb' },
    { name:'Yahoo Finance',        score:86, reason:'Backlog at record; Buy consensus with mid-teens upside' },
    { name:'Options Flow',         score:92, reason:'Call/put ratio 3.2× vs 90d average' },
  ]},
  { ticker:'CAT', company:'Caterpillar Inc', price:342.80, score:86, change:0.30, trend:'up', sources:[
    { name:'Senate Stock Watcher', score:78, reason:'Limited recent activity' },
    { name:'SEC Form 4',           score:88, reason:'Director adding through structured plan + open market' },
    { name:'Yahoo Finance',        score:84, reason:'Infrastructure tailwinds supporting PT revisions' },
    { name:'Options Flow',         score:92, reason:'Deep ITM calls accumulating' },
  ]},
  { ticker:'FCX', company:'Freeport-McMoRan', price:48.22, score:83, change:0.55, trend:'down', sources:[
    { name:'Senate Stock Watcher', score:72, reason:'Minor Senate disclosures' },
    { name:'SEC Form 4',           score:80, reason:'No insider selling; mixed buys' },
    { name:'Yahoo Finance',        score:88, reason:'Copper supply risk driving upgrades' },
    { name:'Options Flow',         score:92, reason:'Weekly call volume spiking on Chile headlines' },
  ]},
];

const MOCK_RESEARCH_REPORTS = [
  { title:'Red Sea Shipping Shock — Gap-Filler Analysis', tag:'supply_chain', date:'Apr 17, 2026', summary:'Container carriers with exposure to Asia-US West Coast trans-Pacific trade stand to benefit from Red Sea rerouting. Rail intermodal volumes at 18-month highs.', author:'StackScreener' },
  { title:'Altman Z-Score Re-ranking: Regional Banks', tag:'fundamentals', date:'Apr 15, 2026', summary:'Quarterly refresh of distance-to-default signals across 47 regional banks. Five new additions to the watchlist, three removals.', author:'StackScreener' },
  { title:'Congressional Buys: Defense Primes Q1', tag:'inst_flow', date:'Apr 14, 2026', summary:'Bipartisan accumulation pattern in LMT, RTX, NOC. Committee overlap analysis included.', author:'StackScreener' },
  { title:'Semiconductor Reshoring Scorecard', tag:'supply_chain', date:'Apr 12, 2026', summary:'CHIPS Act disbursements vs capacity milestones — handicapping which foundries will capture rerouted orders.', author:'StackScreener' },
  { title:'Free Cash Flow Quality: 2026 Cohort', tag:'fundamentals', date:'Apr 10, 2026', summary:'Breaking down reported FCF vs owner earnings for 90 non-financial S&P 500 names. Ten companies flagged for accrual adjustments.', author:'StackScreener' },
  { title:'Form 4 Cluster Buys — March', tag:'inst_flow', date:'Apr 07, 2026', summary:'Ten companies with 3+ insiders buying in the same 30-day window. Historical base rate: 68% outperform over 180 days.', author:'StackScreener' },
];

// ============ STORE (global state) ============
const StackStore = {
  state: JSON.parse(localStorage.getItem('ss_state') || '{}'),
  listeners: new Set(),
  get(key, fallback) {
    return key in this.state ? this.state[key] : fallback;
  },
  set(patch) {
    Object.assign(this.state, patch);
    localStorage.setItem('ss_state', JSON.stringify(this.state));
    this.listeners.forEach(l => l());
  },
  use() {
    const [, force] = React.useReducer(x => x + 1, 0);
    React.useEffect(() => {
      this.listeners.add(force);
      return () => this.listeners.delete(force);
    }, []);
    return this.state;
  }
};

// expose
Object.assign(window, {
  Icon, Logo,
  MOCK_HEATMAP_SECTORS, MOCK_SCREENER_ROWS, MOCK_CALENDAR_EVENTS,
  MOCK_SUPPLY_EVENTS, MOCK_EVENT_STOCKS, MOCK_STOCK_PICKS, MOCK_RESEARCH_REPORTS,
  StackStore,
});

/* Research: Screener, Calendar, Comparison, Picks, Reports */

const formatMC = (b) => b >= 1000 ? `$${(b/1000).toFixed(2)}T` : b >= 1 ? `$${b.toFixed(1)}B` : `$${(b*1000).toFixed(0)}M`;
const formatVol = (v) => v >= 1e9 ? `${(v/1e9).toFixed(1)}B` : v >= 1e6 ? `${(v/1e6).toFixed(1)}M` : `${(v/1e3).toFixed(0)}K`;

const SIGNAL_META = {
  supply_chain: { label:'Supply Chain', color:'accent' },
  congress_buy: { label:'Congress Buy', color:'up' },
  inst_flow:    { label:'Inst. Flow',   color:'warn' },
  dark_pool:    { label:'Dark Pool',    color:'warn' },
};

function ResearchTabs({ sub, go }) {
  const tabs = [
    { k:'screener',   label:'Screener' },
    { k:'calendar',   label:'Calendar' },
    { k:'comparison', label:'Comparison' },
    { k:'picks',      label:'Stock Picks' },
    { k:'reports',    label:'Research Reports' },
  ];
  return (
    <div className="tabs">
      {tabs.map(t => (
        <button key={t.k} className={'tab' + (sub === t.k ? ' active' : '')} onClick={() => go('/research/' + t.k)}>{t.label}</button>
      ))}
    </div>
  );
}

function ScreenerPage() {
  const [sector, setSector] = React.useState('Any');
  const [signal, setSignal] = React.useState('all');
  const [sortBy, setSortBy] = React.useState('score');
  const [sortDir, setSortDir] = React.useState('desc');
  const sectors = ['Any', ...Array.from(new Set(MOCK_SCREENER_ROWS.map(r => r.sector)))];
  let rows = MOCK_SCREENER_ROWS;
  if (sector !== 'Any') rows = rows.filter(r => r.sector === sector);
  if (signal !== 'all') rows = rows.filter(r => r.signal === signal);
  rows = [...rows].sort((a,b) => {
    const av = a[sortBy] ?? 0, bv = b[sortBy] ?? 0;
    return (sortDir === 'asc' ? av - bv : bv - av);
  });

  const Sortable = ({ k, children, align='left' }) => (
    <th style={{ textAlign: align, cursor:'pointer' }} onClick={() => {
      if (sortBy === k) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
      else { setSortBy(k); setSortDir('desc'); }
    }}>
      <span style={{ display:'inline-flex', gap:4, alignItems:'center' }}>
        {children}
        {sortBy === k && <Icon name={sortDir === 'asc' ? 'chevronUp' : 'chevronDown'} size={12}/>}
      </span>
    </th>
  );

  return (
    <>
      <div className="card" style={{ marginBottom:16, padding:14, display:'flex', gap:10, flexWrap:'wrap', alignItems:'center' }}>
        <Icon name="filter" size={16}/>
        <span style={{ fontSize:12, fontWeight:600, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'.05em' }}>Filters</span>
        <select className="select" style={{ width:'auto' }} value={sector} onChange={e => setSector(e.target.value)}>
          {sectors.map(s => <option key={s}>{s}</option>)}
        </select>
        <select className="select" style={{ width:'auto' }} value={signal} onChange={e => setSignal(e.target.value)}>
          <option value="all">All signals</option>
          <option value="supply_chain">Supply Chain</option>
          <option value="congress_buy">Congress Buy</option>
          <option value="inst_flow">Institutional Flow</option>
          <option value="dark_pool">Dark Pool</option>
        </select>
        <select className="select" style={{ width:'auto' }}><option>Market cap: Any</option><option>Mega ({">"}$200B)</option><option>Large $10–200B</option><option>Mid $2–10B</option><option>Small {"<"}$2B</option></select>
        <select className="select" style={{ width:'auto' }}><option>P/E: Any</option><option>{"< 15"}</option><option>15–30</option><option>{"> 30"}</option></select>
        <div style={{ marginLeft:'auto', display:'flex', gap:8 }}>
          <button className="btn sm"><Icon name="download" size={14}/>Export</button>
          <button className="btn primary sm"><Icon name="play" size={12}/>Run scan</button>
        </div>
      </div>

      <div className="card" style={{ padding:0, overflow:'hidden' }}>
        <div style={{ padding:'14px 20px', borderBottom:'1px solid var(--border-soft)', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
          <div>
            <div style={{ fontWeight:600 }}>Results <span style={{ color:'var(--ink-3)', fontWeight:400 }}>· {rows.length} of 6,910 symbols</span></div>
          </div>
          <div style={{ fontSize:12, color:'var(--ink-3)' }}>Refreshed 3 min ago</div>
        </div>
        <div style={{ overflowX:'auto' }}>
          <table className="data-table">
            <thead><tr>
              <Sortable k="rank">#</Sortable>
              <Sortable k="ticker">Ticker</Sortable>
              <th>Company</th>
              <th>Sector</th>
              <Sortable k="mc" align="right">Market Cap</Sortable>
              <Sortable k="pe" align="right">P/E</Sortable>
              <Sortable k="price" align="right">Price</Sortable>
              <Sortable k="change" align="right">Change</Sortable>
              <Sortable k="volume" align="right">Volume</Sortable>
              <th>Signal</th>
              <Sortable k="score" align="right">Score</Sortable>
            </tr></thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.ticker}>
                  <td style={{ color:'var(--ink-3)' }}>{r.rank}</td>
                  <td className="ticker">{r.ticker}</td>
                  <td style={{ maxWidth:220, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{r.company}</td>
                  <td style={{ color:'var(--ink-2)' }}>{r.sector}</td>
                  <td className="num">{formatMC(r.mc)}</td>
                  <td className="num">{r.pe ? r.pe.toFixed(1) : '—'}</td>
                  <td className="num">${r.price.toFixed(2)}</td>
                  <td className="num"><span className={'badge ' + (r.change >= 0 ? 'up' : 'down')} style={{ fontVariantNumeric:'tabular-nums' }}>{r.change >= 0 ? '+' : ''}{r.change.toFixed(2)}%</span></td>
                  <td className="num" style={{ color:'var(--ink-2)' }}>{formatVol(r.volume)}</td>
                  <td>{r.signal ? <span className={'badge ' + SIGNAL_META[r.signal].color}>{SIGNAL_META[r.signal].label}</span> : <span style={{ color:'var(--ink-4)' }}>—</span>}</td>
                  <td>
                    <div style={{ display:'flex', alignItems:'center', gap:8, minWidth:120 }}>
                      <div className="progress" style={{ flex:1 }}><div style={{ width: `${r.score}%` }}/></div>
                      <span className="mono" style={{ fontWeight:700, fontSize:12, minWidth:24, textAlign:'right' }}>{r.score}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function CalendarPage() {
  const [tab, setTab] = React.useState('all');
  const weekStart = new Date('2026-04-19T00:00:00');
  const days = Array.from({length:7}, (_,i) => {
    const d = new Date(weekStart); d.setDate(d.getDate()+i);
    return { date: d.toISOString().slice(0,10), label: d.toLocaleDateString('en-US',{weekday:'short'}), dom: d.getDate(), mon: d.toLocaleDateString('en-US',{month:'short'}) };
  });
  let events = MOCK_CALENDAR_EVENTS;
  if (tab !== 'all') events = events.filter(e => e.type === tab);

  const TYPE_COLOR = { earnings:'up', ipo:'warn', split:'accent', economic:'down' };

  return (
    <>
      <div className="tabs" style={{ marginBottom:20 }}>
        {['all','earnings','split','ipo','economic'].map(t => (
          <button key={t} className={'tab' + (tab === t ? ' active' : '')} onClick={() => setTab(t)}>
            {t==='all'?'All Events':t==='split'?'Splits':t==='ipo'?'IPOs':t[0].toUpperCase()+t.slice(1)}
          </button>
        ))}
      </div>

      <div className="card" style={{ padding:16, marginBottom:16 }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
          <div style={{ fontWeight:600 }}>Week of Apr 19 – Apr 25, 2026</div>
          <div style={{ display:'flex', gap:6 }}>
            <button className="btn sm ghost"><Icon name="chevronLeft" size={14}/></button>
            <button className="btn sm">Today</button>
            <button className="btn sm ghost"><Icon name="chevronRight" size={14}/></button>
          </div>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(7, 1fr)', gap:8 }}>
          {days.map(d => {
            const dayEvs = events.filter(e => e.date === d.date);
            return (
              <div key={d.date} style={{ border:'1px solid var(--border-soft)', borderRadius:10, padding:10, background:'var(--bg-inset)', minHeight:140 }}>
                <div style={{ fontSize:11, color:'var(--ink-3)', fontWeight:600, textTransform:'uppercase', letterSpacing:'.05em' }}>{d.label}</div>
                <div style={{ fontSize:16, fontWeight:700, marginBottom:8 }}>{d.dom}</div>
                <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
                  {dayEvs.map((e,i) => (
                    <span key={i} className={'badge ' + TYPE_COLOR[e.type]} style={{ justifyContent:'flex-start', width:'100%', fontSize:10 }}>
                      {e.ticker && <span className="mono" style={{ fontWeight:700 }}>{e.ticker}</span>}
                      <span style={{ opacity:.85, textOverflow:'ellipsis', overflow:'hidden', whiteSpace:'nowrap' }}>{e.ticker ? e.title.replace(e.ticker,'').trim() : e.title}</span>
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card" style={{ padding:0 }}>
        <div style={{ padding:'14px 20px', borderBottom:'1px solid var(--border-soft)', fontWeight:600 }}>Details</div>
        <table className="data-table">
          <thead><tr><th>Date</th><th>Type</th><th>Ticker</th><th>Event</th><th>Details</th></tr></thead>
          <tbody>
            {events.map((e,i) => (
              <tr key={i}>
                <td className="mono" style={{ color:'var(--ink-2)' }}>{e.date}</td>
                <td><span className={'badge ' + TYPE_COLOR[e.type]}>{e.type}</span></td>
                <td className="ticker">{e.ticker || '—'}</td>
                <td>{e.title}</td>
                <td style={{ color:'var(--ink-3)', fontSize:12 }}>
                  {e.est != null && `EPS estimate: $${e.est}`}
                  {e.lo != null && `Range: $${e.lo}–$${e.hi}`}
                  {e.ratio && `Ratio: ${e.ratio}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function ComparisonPage() {
  const pool = [
    { t:'AAPL', name:'Apple Inc',        mv:3500, ev:3480, pe:30.2, deps:6.80, div:0.55, sec:'Technology',   ind:'Hardware',        ceo:'Tim Cook',     wk:2.1, m3:8.4, ytd:14.2, yr1:28.5, rev:394.3, opex:267.1, opi:114.3, revg:6.2, gp:181.3 },
    { t:'MSFT', name:'Microsoft Corp',    mv:3100, ev:3080, pe:36.7, deps:11.24, div:0.73, sec:'Technology', ind:'Software',        ceo:'Satya Nadella', wk:1.4, m3:6.8, ytd:11.1, yr1:24.1, rev:245.1, opex:94.3, opi:109.4, revg:14.5, gp:171.0 },
    { t:'NVDA', name:'NVIDIA Corp',       mv:2900, ev:2870, pe:38.2, deps:20.80, div:0.04, sec:'Technology', ind:'Semiconductors',  ceo:'Jensen Huang',  wk:4.2, m3:18.3, ytd:42.1, yr1:112.5, rev:60.9, opex:12.4, opi:33.5, revg:265.3, gp:44.3 },
    { t:'GOOGL', name:'Alphabet Inc',     mv:2100, ev:1960, pe:26.8, deps:6.40, div:0.20, sec:'Communication', ind:'Internet',    ceo:'Sundar Pichai', wk:0.8, m3:5.4, ytd:8.9, yr1:19.4, rev:307.4, opex:206.1, opi:84.3, revg:8.7, gp:174.1 },
  ];
  const [selected, setSelected] = React.useState(['AAPL','MSFT','NVDA','GOOGL']);
  const cols = selected.map(t => pool.find(p => p.t === t)).filter(Boolean);
  const [highlight, setHighlight] = React.useState(true);

  const Row = ({ label, key, suffix='', prefix='$', dollars=true, higherBetter=true, pct=false }) => {
    const vals = cols.map(c => c?.[key]);
    const valid = vals.filter(v => v != null);
    const max = Math.max(...valid), min = Math.min(...valid);
    return (
      <tr>
        <td style={{ color:'var(--ink-2)' }}>{label}</td>
        {cols.map((c,i) => {
          const v = c[key];
          if (v == null) return <td key={i} className="num">—</td>;
          const isHigh = v === max, isLow = v === min;
          const good = (higherBetter && isHigh) || (!higherBetter && isLow);
          const bad = (higherBetter && isLow) || (!higherBetter && isHigh);
          return (
            <td key={i} className="num">
              <span style={{ color: highlight ? (good ? 'var(--up)' : bad ? 'var(--down)' : 'var(--ink)') : 'var(--ink)', fontWeight: highlight && (good||bad) ? 600 : 400 }}>
                {highlight && good && '▲ '}{highlight && bad && '▼ '}
                {pct ? (v*100).toFixed(1)+'%' : dollars ? (v >= 100 ? `$${v.toFixed(0)}B` : `$${v.toFixed(2)}`) : v.toFixed(2)}
                {suffix}
              </span>
            </td>
          );
        })}
        {Array.from({length: 4 - cols.length}).map((_,i) => <td key={'e'+i} className="num" style={{ color:'var(--ink-4)' }}>—</td>)}
      </tr>
    );
  };

  const Section = ({ title, children }) => (
    <div className="card" style={{ padding:0, marginBottom:16 }}>
      <div style={{ padding:'12px 20px', borderBottom:'1px solid var(--border-soft)', fontWeight:600, fontSize:13 }}>{title}</div>
      <table className="data-table"><tbody>{children}</tbody></table>
    </div>
  );

  const TextRow = ({ label, key }) => (
    <tr>
      <td style={{ color:'var(--ink-2)' }}>{label}</td>
      {cols.map((c,i) => <td key={i}>{c[key]}</td>)}
      {Array.from({length: 4 - cols.length}).map((_,i) => <td key={'e'+i} style={{ color:'var(--ink-4)' }}>—</td>)}
    </tr>
  );

  return (
    <>
      <div className="card" style={{ padding:16, marginBottom:16 }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:14, flexWrap:'wrap', gap:10 }}>
          <div>
            <div style={{ fontWeight:600 }}>Compare Stocks</div>
            <div style={{ fontSize:12, color:'var(--ink-3)' }}>Compare up to 4 tickers side-by-side.</div>
          </div>
          <label style={{ display:'flex', alignItems:'center', gap:8, fontSize:13 }}>
            <span className="switch"><input type="checkbox" checked={highlight} onChange={e=>setHighlight(e.target.checked)}/><span className="track"/></span>
            Highlight highs / lows
          </label>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:10 }}>
          {[0,1,2,3].map(i => {
            const t = selected[i];
            const c = t ? pool.find(p => p.t === t) : null;
            return (
              <div key={i} style={{ padding:'12px 14px', border:'1px solid var(--border)', borderRadius:10, background:'var(--bg-inset)' }}>
                {c ? (
                  <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                    <div style={{ width:32, height:32, borderRadius:8, background:'var(--accent-soft)', color:'var(--accent)', display:'grid', placeItems:'center', fontFamily:'var(--font-mono)', fontWeight:800, fontSize:11 }}>{c.t.slice(0,2)}</div>
                    <div style={{ flex:1, minWidth:0 }}>
                      <div className="mono" style={{ fontWeight:700 }}>{c.t}</div>
                      <div style={{ fontSize:11, color:'var(--ink-3)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{c.name}</div>
                    </div>
                    <button className="btn ghost sm" onClick={() => setSelected(selected.filter(x => x !== t))}><Icon name="close" size={13}/></button>
                  </div>
                ) : (
                  <button className="btn ghost" style={{ width:'100%', justifyContent:'center', color:'var(--ink-3)' }}
                    onClick={() => {
                      const options = pool.filter(p => !selected.includes(p.t));
                      if (options.length) setSelected([...selected, options[0].t]);
                    }}><Icon name="plus" size={14}/>Add stock</button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <Section title="Valuation">
        <Row label="Market Value" key="mv" />
        <Row label="Enterprise Value" key="ev" />
        <Row label="Price to Earnings" key="pe" dollars={false} higherBetter={false} />
        <Row label="Diluted EPS" key="deps" />
        <Row label="Forward Dividend" key="div" />
        <TextRow label="Sector" key="sec"/>
        <TextRow label="Industry" key="ind"/>
        <TextRow label="CEO" key="ceo"/>
      </Section>
      <Section title="Price Performance">
        <Row label="1 Week" key="wk" dollars={false} suffix="%" />
        <Row label="3 Months" key="m3" dollars={false} suffix="%" />
        <Row label="YTD" key="ytd" dollars={false} suffix="%" />
        <Row label="1 Year" key="yr1" dollars={false} suffix="%" />
      </Section>
      <Section title="Income Statement">
        <Row label="Revenue" key="rev" />
        <Row label="Operating Expenses" key="opex" higherBetter={false} />
        <Row label="Operating Income" key="opi" />
        <Row label="Revenue Growth YoY" key="revg" dollars={false} suffix="%" />
        <Row label="Gross Profit" key="gp" />
      </Section>
    </>
  );
}

function StockPicksPage() {
  const [open, setOpen] = React.useState(new Set(['NVDA']));
  return (
    <>
      <div className="card" style={{ padding:'16px 20px', marginBottom:16, display:'flex', gap:16, alignItems:'center', flexWrap:'wrap' }}>
        <Icon name="spark" size={18}/>
        <div style={{ flex:1, minWidth:240 }}>
          <div style={{ fontWeight:600 }}>20 stocks aggregated from free public sources</div>
          <div style={{ fontSize:12, color:'var(--ink-3)' }}>
            Signals from Senate / House Stock Watcher, SEC Form 4 &amp; 13F, Yahoo Finance, and options flow — weighted into a composite 0–100 score.
          </div>
        </div>
        <button className="btn sm"><Icon name="refresh" size={14}/>Refresh signals</button>
      </div>

      {MOCK_STOCK_PICKS.map(p => {
        const isOpen = open.has(p.ticker);
        return (
          <div key={p.ticker} className="card" style={{ padding:0, marginBottom:10, overflow:'hidden' }}>
            <button onClick={() => {
              const s = new Set(open); s.has(p.ticker) ? s.delete(p.ticker) : s.add(p.ticker); setOpen(s);
            }} style={{ background:'transparent', border:'none', width:'100%', padding:'16px 20px', display:'flex', alignItems:'center', gap:16, cursor:'pointer', color:'var(--ink)' }}>
              <div style={{ width:42, height:42, borderRadius:10, background:'var(--accent-soft)', color:'var(--accent)', display:'grid', placeItems:'center', fontFamily:'var(--font-mono)', fontWeight:800, fontSize:13 }}>{p.ticker.slice(0,2)}</div>
              <div style={{ minWidth:80 }}>
                <div className="mono" style={{ fontWeight:700, fontSize:15 }}>{p.ticker}</div>
                <div style={{ fontSize:11, color:'var(--ink-3)' }}>NASDAQ</div>
              </div>
              <div style={{ flex:1, textAlign:'left', fontSize:14 }}>{p.company}</div>
              <div className="num mono" style={{ minWidth:90, textAlign:'right', fontWeight:600 }}>${p.price.toFixed(2)}</div>
              <span className={'badge ' + (p.change >= 0 ? 'up' : 'down')}>{p.change >= 0 ? '+' : ''}{p.change.toFixed(2)}%</span>
              <div style={{ display:'flex', flexDirection:'column', alignItems:'flex-end', minWidth:80 }}>
                <div style={{ fontSize:10, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'.05em' }}>Score</div>
                <div className="mono" style={{ fontSize:22, fontWeight:800, color:'var(--accent)', lineHeight:1 }}>{p.score}</div>
              </div>
              <Icon name={isOpen?'chevronUp':'chevronDown'} size={18}/>
            </button>
            {isOpen && (
              <div style={{ padding:'4px 20px 20px', borderTop:'1px solid var(--border-soft)' }}>
                <div style={{ fontSize:11, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'.05em', marginBottom:8, fontWeight:600, paddingTop:14 }}>Source breakdown</div>
                <div style={{ display:'grid', gridTemplateColumns:'1fr', gap:10 }}>
                  {p.sources.map(s => (
                    <div key={s.name} style={{ display:'grid', gridTemplateColumns:'180px 1fr 80px', gap:16, alignItems:'center', padding:'10px 12px', background:'var(--bg-inset)', borderRadius:8 }}>
                      <div style={{ fontWeight:600, fontSize:13 }}>{s.name}</div>
                      <div style={{ fontSize:13, color:'var(--ink-2)' }}>{s.reason}</div>
                      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                        <div className="progress" style={{ flex:1 }}><div style={{ width:`${s.score}%` }}/></div>
                        <span className="mono" style={{ fontWeight:700, minWidth:22, textAlign:'right' }}>{s.score}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </>
  );
}

function ReportsPage() {
  const TAG_META = { supply_chain:{label:'Supply Chain', color:'accent'}, fundamentals:{label:'Fundamentals', color:'up'}, inst_flow:{label:'Inst. Flow', color:'warn'} };
  const [tag, setTag] = React.useState('all');
  const reports = tag === 'all' ? MOCK_RESEARCH_REPORTS : MOCK_RESEARCH_REPORTS.filter(r => r.tag === tag);
  return (
    <>
      <div style={{ display:'flex', gap:8, marginBottom:16, flexWrap:'wrap' }}>
        {[['all','All'],['supply_chain','Supply Chain'],['fundamentals','Fundamentals'],['inst_flow','Inst. Flow']].map(([k,l]) => (
          <button key={k} className={'btn sm ' + (tag===k?'primary':'')} onClick={()=>setTag(k)}>{l}</button>
        ))}
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(320px, 1fr))', gap:16 }}>
        {reports.map((r,i) => (
          <article key={i} className="card" style={{ cursor:'pointer', transition:'border-color .15s' }}
            onMouseEnter={e=>e.currentTarget.style.borderColor='var(--border-strong)'}
            onMouseLeave={e=>e.currentTarget.style.borderColor=''}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10 }}>
              <span className={'badge ' + TAG_META[r.tag].color}>{TAG_META[r.tag].label}</span>
              <span style={{ fontSize:11, color:'var(--ink-3)' }}>{r.date}</span>
            </div>
            <h3 style={{ fontSize:15, fontWeight:600, margin:'0 0 8px', letterSpacing:'-0.005em' }}>{r.title}</h3>
            <p style={{ fontSize:13, color:'var(--ink-2)', lineHeight:1.55, margin:'0 0 14px', textWrap:'pretty' }}>{r.summary}</p>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', fontSize:12, color:'var(--ink-3)' }}>
              <span>by {r.author}</span>
              <span style={{ color:'var(--accent)', fontWeight:600 }}>Read →</span>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

function ResearchPage({ sub, go }) {
  return (
    <div className="page">
      <h1>Research</h1>
      <p className="sub">Screener, calendar, comparison, stock picks, and research reports — one hub.</p>
      <ResearchTabs sub={sub} go={go}/>
      {sub === 'screener' && <ScreenerPage/>}
      {sub === 'calendar' && <CalendarPage/>}
      {sub === 'comparison' && <ComparisonPage/>}
      {sub === 'picks' && <StockPicksPage/>}
      {sub === 'reports' && <ReportsPage/>}
    </div>
  );
}

Object.assign(window, { ResearchPage });

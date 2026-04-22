/* Login + Home (heatmap) */

function LoginPage({ go, logo }) {
  const [showPw, setShowPw] = React.useState(false);
  const [u, setU] = React.useState('admin');
  const [p, setP] = React.useState('admin');
  const submit = (e) => { e.preventDefault(); go('/home'); };

  return (
    <div style={{ minHeight:'100vh', display:'grid', gridTemplateColumns:'1fr 1fr', background:'var(--bg)' }} className="login-split">
      <style>{`
        @media (max-width: 820px) { .login-split { grid-template-columns: 1fr !important; } .login-hero { display: none !important; } }
      `}</style>
      <aside className="login-hero" style={{
        padding:'48px 56px',
        background:'linear-gradient(155deg, oklch(from var(--accent) l c h / 0.18), oklch(from var(--accent) l c h / 0.04) 60%, transparent)',
        borderRight:'1px solid var(--border-soft)',
        display:'flex', flexDirection:'column', justifyContent:'space-between',
        position:'relative', overflow:'hidden'
      }}>
        <div style={{ position:'absolute', inset:0, backgroundImage:'radial-gradient(circle at 1px 1px, var(--border) 1px, transparent 0)', backgroundSize:'24px 24px', opacity:0.3, maskImage:'radial-gradient(circle at 30% 40%, black, transparent 70%)' }}/>
        <div style={{ position:'relative' }}>
          <Logo variant={logo} size={26} />
        </div>
        <div style={{ position:'relative', maxWidth:440 }}>
          <div style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'4px 10px', borderRadius:99, background:'var(--accent-soft)', color:'var(--accent)', fontSize:11, fontWeight:700, letterSpacing:'0.05em', textTransform:'uppercase' }}>
            <Icon name="spark" size={12}/> Supply-chain aware
          </div>
          <h1 style={{ fontSize:42, fontWeight:700, lineHeight:1.08, letterSpacing:'-0.02em', margin:'16px 0 16px' }}>
            Spot the gap.<br/>
            Before the market does.
          </h1>
          <p style={{ color:'var(--ink-2)', fontSize:15, lineHeight:1.6, margin:0, maxWidth:400 }}>
            StackScreener ingests supply-chain signals, fundamentals, and institutional flow — then ranks the companies best positioned to fill the gap.
          </p>
          <div style={{ marginTop:28, display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:10, maxWidth:440 }}>
            {[
              { k:'6,924', v:'symbols tracked' },
              { k:'9', v:'active disruptions' },
              { k:'8', v:'score components' },
            ].map(s => (
              <div key={s.v} style={{ padding:'10px 12px', border:'1px solid var(--border-soft)', borderRadius:10, background:'var(--bg-card)' }}>
                <div className="mono" style={{ fontSize:18, fontWeight:700, color:'var(--accent)' }}>{s.k}</div>
                <div style={{ fontSize:11, color:'var(--ink-3)' }}>{s.v}</div>
              </div>
            ))}
          </div>
        </div>
        <div style={{ position:'relative', fontSize:12, color:'var(--ink-3)' }}>
          © 2026 StackScreener · antv311
        </div>
      </aside>

      <main style={{ display:'grid', placeItems:'center', padding:'48px 24px' }}>
        <form onSubmit={submit} style={{ width:'100%', maxWidth:380 }}>
          <h2 style={{ fontSize:24, fontWeight:700, letterSpacing:'-0.01em', margin:'0 0 6px' }}>Welcome back</h2>
          <p style={{ color:'var(--ink-3)', fontSize:14, margin:'0 0 28px' }}>Sign in to your StackScreener workspace.</p>

          <label className="label">Username</label>
          <input className="input" value={u} onChange={e=>setU(e.target.value)} autoComplete="username"/>

          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', marginTop:16 }}>
            <label className="label" style={{ marginBottom:6 }}>Password</label>
            <a href="#/login" onClick={e=>{e.preventDefault(); alert('A reset link would be emailed to the address on file.');}} style={{ fontSize:12, color:'var(--accent)', textDecoration:'none', fontWeight:600 }}>Forgot password?</a>
          </div>
          <div style={{ position:'relative' }}>
            <input className="input" type={showPw?'text':'password'} value={p} onChange={e=>setP(e.target.value)} style={{ paddingRight:38 }} autoComplete="current-password"/>
            <button type="button" onClick={()=>setShowPw(x=>!x)} style={{ position:'absolute', right:8, top:'50%', transform:'translateY(-50%)', background:'transparent', border:'none', color:'var(--ink-3)', padding:6, borderRadius:6, cursor:'pointer' }}>
              <Icon name={showPw?'eyeOff':'eye'} size={16}/>
            </button>
          </div>

          <label className="label" style={{ marginTop:16 }}>2FA code <span style={{ color:'var(--ink-4)', fontWeight:500, fontSize:11, textTransform:'none', letterSpacing:0 }}>(optional — not yet enabled)</span></label>
          <input className="input" placeholder="123 456" inputMode="numeric" pattern="[0-9 ]*" disabled style={{ opacity:0.6 }}/>

          <label style={{ display:'flex', alignItems:'center', gap:8, marginTop:16, fontSize:13, color:'var(--ink-2)' }}>
            <input type="checkbox" defaultChecked style={{ accentColor:'var(--accent)', width:15, height:15 }}/>
            Remember me on this device
          </label>

          <button type="submit" className="btn primary lg" style={{ width:'100%', justifyContent:'center', marginTop:22 }}>
            Sign in <Icon name="chevronRight" size={16}/>
          </button>

          <div style={{ marginTop:20, padding:12, border:'1px dashed var(--border)', borderRadius:10, background:'var(--bg-inset)', fontSize:12, color:'var(--ink-3)' }}>
            <div style={{ fontWeight:600, color:'var(--ink-2)', marginBottom:4 }}>Default credentials</div>
            Use <span className="mono" style={{ color:'var(--ink)' }}>admin / admin</span> — you will be prompted to change on first login.
          </div>
        </form>
      </main>
    </div>
  );
}

// ========== HEATMAP ==========
function HeatmapTile({ s, width, height, onClick }) {
  const pct = s.c;
  const mag = Math.min(Math.abs(pct) / 5, 1);
  const color = pct >= 0
    ? `oklch(${0.30 + mag*0.25} ${0.08 + mag*0.10} 150)`
    : `oklch(${0.34 + mag*0.18} ${0.10 + mag*0.12} 25)`;
  const small = width < 50 || height < 34;
  const tiny = width < 30 || height < 22;
  return (
    <div onClick={() => onClick(s)} style={{
      position:'absolute', left:0, top:0,
      width, height,
      background: color,
      border:'1px solid rgba(0,0,0,.25)',
      display:'flex', flexDirection:'column',
      alignItems:'center', justifyContent:'center',
      cursor:'pointer',
      overflow:'hidden',
      color:'white',
      fontFamily:'var(--font-mono)',
      lineHeight:1.1,
      transition:'filter .12s'
    }} onMouseEnter={e=>e.currentTarget.style.filter='brightness(1.15)'}
       onMouseLeave={e=>e.currentTarget.style.filter='none'}>
      {!tiny && (
        <>
          <div style={{ fontSize: Math.min(width/4, height/3, 20), fontWeight:700 }}>{s.t}</div>
          {!small && <div style={{ fontSize: Math.min(width/7, 11), opacity:0.85 }}>{pct >= 0 ? '+' : ''}{pct.toFixed(2)}%</div>}
        </>
      )}
    </div>
  );
}

// squarify treemap (simplified)
function squarify(items, x, y, w, h) {
  const total = items.reduce((a,b) => a + b.value, 0);
  if (total === 0) return [];
  const out = [];
  let cx = x, cy = y, cw = w, ch = h;
  let remaining = [...items].sort((a,b)=>b.value-a.value);
  const place = (row, rowTotal) => {
    const isHoriz = cw >= ch;
    const rowLen = isHoriz ? (rowTotal/total) * cw : (rowTotal/total) * ch;
    let off = 0;
    for (const r of row) {
      const share = r.value / rowTotal;
      if (isHoriz) {
        const rh = share * ch;
        out.push({ ...r, x: cx, y: cy + off, w: rowLen, h: rh });
        off += rh;
      } else {
        const rw = share * cw;
        out.push({ ...r, x: cx + off, y: cy, w: rw, h: rowLen });
        off += rw;
      }
    }
    if (isHoriz) { cx += rowLen; cw -= rowLen; }
    else         { cy += rowLen; ch -= rowLen; }
  };
  // Greedy group to keep aspect reasonable
  while (remaining.length) {
    let row = [remaining.shift()];
    let rowTotal = row[0].value;
    while (remaining.length) {
      const next = remaining[0];
      const prevAR = aspectScore(row, rowTotal, cw, ch, total);
      const nextAR = aspectScore([...row, next], rowTotal + next.value, cw, ch, total);
      if (nextAR < prevAR) { row.push(remaining.shift()); rowTotal += row[row.length-1].value; }
      else break;
    }
    place(row, rowTotal);
  }
  return out;
}
function aspectScore(row, rowTotal, cw, ch, total) {
  const shortest = Math.min(cw, ch);
  const area = (rowTotal/total) * cw * ch;
  let worst = 0;
  for (const r of row) {
    const a = (r.value/rowTotal) * area;
    const ar = Math.max((shortest*shortest*(r.value))/(area*area) , (area*area)/(shortest*shortest*r.value));
    worst = Math.max(worst, ar);
  }
  return worst;
}

function Heatmap({ filter, onPick }) {
  const ref = React.useRef(null);
  const [dims, setDims] = React.useState({ w: 900, h: 480 });
  React.useEffect(() => {
    const ro = new ResizeObserver(entries => {
      for (const e of entries) setDims({ w: e.contentRect.width, h: e.contentRect.height });
    });
    if (ref.current) ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  // filter universe
  const sectors = MOCK_HEATMAP_SECTORS.map(sec => ({
    ...sec,
    value: sec.weight,
    stocks: sec.stocks.filter(st => {
      if (filter === 'SP') return true;
      if (filter === 'DOW') return ['AAPL','MSFT','JPM','WMT','PG','JNJ','HD','CAT','BA','V','GS','MCD','DIS','CSCO','CVX','NKE','KO','MRK','AXP','IBM','MMM','DOW','HON','TRV','UNH','VZ','WBA','AMGN','CRM'].includes(st.t);
      if (filter === 'RUS') return st.mc < 500 || st.mc > 10;
      if (filter === 'REC') return st.c > 0.5;
      return true;
    })
  })).filter(sec => sec.stocks.length > 0);

  const sectorBoxes = squarify(sectors, 0, 0, dims.w, dims.h);
  return (
    <div ref={ref} style={{ position:'relative', width:'100%', height:'calc(100vh - 340px)', minHeight:380, background:'#0c1410', border:'1px solid var(--border)', borderRadius:'var(--radius-lg)', overflow:'hidden' }}>
      {sectorBoxes.map(sb => {
        const totalMc = sb.stocks.reduce((a,b)=>a+b.mc, 0);
        const stockBoxes = squarify(sb.stocks.map(s => ({ ...s, value: s.mc })), sb.x, sb.y, sb.w, sb.h);
        return (
          <React.Fragment key={sb.name}>
            {stockBoxes.map(st => (
              <div key={st.t} style={{ position:'absolute', left:st.x, top:st.y, width:st.w, height:st.h }}>
                <HeatmapTile s={st} width={st.w} height={st.h} onClick={onPick}/>
              </div>
            ))}
            <div style={{ position:'absolute', left:sb.x+4, top:sb.y+2, fontSize:10, fontWeight:700, color:'rgba(255,255,255,.55)', textTransform:'uppercase', letterSpacing:'.05em', pointerEvents:'none', maxWidth:sb.w-8, textOverflow:'ellipsis', overflow:'hidden', whiteSpace:'nowrap' }}>{sb.name}</div>
          </React.Fragment>
        );
      })}
    </div>
  );
}

function HomePage() {
  const [filter, setFilter] = React.useState('SP');
  const [picked, setPicked] = React.useState(null);

  return (
    <div className="page">
      <div style={{ display:'flex', alignItems:'flex-end', justifyContent:'space-between', flexWrap:'wrap', gap:16, marginBottom:16 }}>
        <div>
          <h1>Market Heatmap</h1>
          <p className="sub">Tiles sized by market cap, colored by intraday change. Double-click to zoom.</p>
        </div>
        <div style={{ display:'flex', gap:8, alignItems:'center' }}>
          <span className="badge dot up">Markets open</span>
          <span style={{ fontSize:12, color:'var(--ink-3)' }}>Refreshed 2 min ago</span>
          <button className="btn sm"><Icon name="refresh" size={14}/>Refresh</button>
        </div>
      </div>

      <Heatmap filter={filter} onPick={setPicked}/>

      <div style={{ display:'grid', gridTemplateColumns:'1fr auto', gap:16, marginTop:16, alignItems:'center', flexWrap:'wrap' }}>
        <div className="card" style={{ padding:'14px 20px' }}>
          <div style={{ display:'flex', flexWrap:'wrap', gap:8, alignItems:'center' }}>
            <span style={{ fontSize:12, color:'var(--ink-3)', fontWeight:600, textTransform:'uppercase', letterSpacing:'.05em', marginRight:8 }}>Index</span>
            {[
              { k:'SP', label:'S&P 500' },
              { k:'DOW', label:'Dow' },
              { k:'RUS', label:'Russell' },
              { k:'REC', label:'Recommended' },
              { k:'ALL', label:'All' },
            ].map(b => (
              <button key={b.k} className={'btn sm ' + (filter === b.k ? 'primary' : '')} onClick={() => setFilter(b.k)}>{b.label}</button>
            ))}
            <div style={{ marginLeft:'auto', display:'flex', gap:12, fontSize:12, color:'var(--ink-3)' }}>
              <span style={{ display:'inline-flex', alignItems:'center', gap:6 }}><span style={{ width:14, height:10, background:'oklch(.30 .08 150)' }}/>-5%</span>
              <span style={{ display:'inline-flex', alignItems:'center', gap:6 }}><span style={{ width:14, height:10, background:'#25383f' }}/>0%</span>
              <span style={{ display:'inline-flex', alignItems:'center', gap:6 }}><span style={{ width:14, height:10, background:'oklch(.55 .18 150)' }}/>+5%</span>
            </div>
          </div>
        </div>
      </div>

      {picked && (
        <div className="modal-backdrop" onClick={()=>setPicked(null)}>
          <div className="modal" onClick={e=>e.stopPropagation()} style={{ maxWidth:420 }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
              <div>
                <div className="mono" style={{ fontSize:24, fontWeight:800 }}>{picked.t}</div>
                <div style={{ color:'var(--ink-3)', fontSize:13 }}>Market cap: ${picked.mc}B</div>
              </div>
              <button className="btn ghost sm" onClick={()=>setPicked(null)}><Icon name="close" size={16}/></button>
            </div>
            <div style={{ marginTop:16, padding:'16px 20px', background:'var(--bg-inset)', borderRadius:10, display:'flex', gap:20, alignItems:'center' }}>
              <div>
                <div style={{ fontSize:11, color:'var(--ink-3)', textTransform:'uppercase', letterSpacing:'.05em' }}>Change</div>
                <div className={'mono ' + (picked.c >= 0 ? '' : '')} style={{ fontSize:22, fontWeight:700, color: picked.c >= 0 ? 'var(--up)' : 'var(--down)' }}>
                  {picked.c >= 0 ? '+' : ''}{picked.c.toFixed(2)}%
                </div>
              </div>
              <div style={{ flex:1, height:40 }}>
                <svg width="100%" height="40" viewBox="0 0 120 40" preserveAspectRatio="none">
                  <polyline fill="none" stroke={picked.c>=0?'var(--up)':'var(--down)'} strokeWidth="1.5"
                    points={Array.from({length:30}).map((_,i) => `${i*4},${20 + Math.sin(i*0.5 + picked.t.length)*8 + (picked.c*i/6)}`).join(' ')}/>
                </svg>
              </div>
            </div>
            <div className="row"><button className="btn">View on Research</button><button className="btn primary">Add to Watchlist</button></div>
          </div>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { LoginPage, HomePage });

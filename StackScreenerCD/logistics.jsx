/* Logistics: real world map with zoom hierarchy (World → Region → Country → Subdivision) */

// ISO-3166 numeric code → iso2 + region (5-region business grouping)
// Large countries (> ~550k km², "larger than France") get 'hasSubdivisions: true'
const COUNTRY_META = {
  // North America
  '840': { iso2:'US', name:'United States', region:'Americas', hasSubdivisions:true },
  '124': { iso2:'CA', name:'Canada',        region:'Americas', hasSubdivisions:true },
  '484': { iso2:'MX', name:'Mexico',        region:'Americas', hasSubdivisions:true },
  // South America (LatAm)
  '076': { iso2:'BR', name:'Brazil',    region:'LatAm', hasSubdivisions:true },
  '032': { iso2:'AR', name:'Argentina', region:'LatAm', hasSubdivisions:true },
  '152': { iso2:'CL', name:'Chile',     region:'LatAm' },
  '604': { iso2:'PE', name:'Peru',      region:'LatAm', hasSubdivisions:true },
  '170': { iso2:'CO', name:'Colombia',  region:'LatAm', hasSubdivisions:true },
  '862': { iso2:'VE', name:'Venezuela', region:'LatAm' },
  '591': { iso2:'PA', name:'Panama',    region:'LatAm' },
  '68':  { iso2:'BO', name:'Bolivia',   region:'LatAm', hasSubdivisions:true },
  '858': { iso2:'UY', name:'Uruguay',   region:'LatAm' },
  '600': { iso2:'PY', name:'Paraguay',  region:'LatAm' },
  '218': { iso2:'EC', name:'Ecuador',   region:'LatAm' },
  // Europe (EMEA)
  '826': { iso2:'GB', name:'United Kingdom', region:'EMEA' },
  '250': { iso2:'FR', name:'France',          region:'EMEA' },
  '276': { iso2:'DE', name:'Germany',         region:'EMEA' },
  '380': { iso2:'IT', name:'Italy',           region:'EMEA' },
  '724': { iso2:'ES', name:'Spain',           region:'EMEA' },
  '528': { iso2:'NL', name:'Netherlands',     region:'EMEA' },
  '056': { iso2:'BE', name:'Belgium',         region:'EMEA' },
  '756': { iso2:'CH', name:'Switzerland',     region:'EMEA' },
  '040': { iso2:'AT', name:'Austria',         region:'EMEA' },
  '752': { iso2:'SE', name:'Sweden',          region:'EMEA' },
  '578': { iso2:'NO', name:'Norway',          region:'EMEA' },
  '246': { iso2:'FI', name:'Finland',         region:'EMEA' },
  '208': { iso2:'DK', name:'Denmark',         region:'EMEA' },
  '616': { iso2:'PL', name:'Poland',          region:'EMEA' },
  '203': { iso2:'CZ', name:'Czechia',         region:'EMEA' },
  '348': { iso2:'HU', name:'Hungary',         region:'EMEA' },
  '642': { iso2:'RO', name:'Romania',         region:'EMEA' },
  '300': { iso2:'GR', name:'Greece',          region:'EMEA' },
  '620': { iso2:'PT', name:'Portugal',        region:'EMEA' },
  '372': { iso2:'IE', name:'Ireland',         region:'EMEA' },
  '792': { iso2:'TR', name:'Turkey',          region:'EMEA', hasSubdivisions:true },
  '804': { iso2:'UA', name:'Ukraine',         region:'EMEA', hasSubdivisions:true },
  '643': { iso2:'RU', name:'Russia',          region:'EMEA', hasSubdivisions:true },
  // Africa (EMEA)
  '818': { iso2:'EG', name:'Egypt',          region:'EMEA', hasSubdivisions:true },
  '710': { iso2:'ZA', name:'South Africa',   region:'EMEA', hasSubdivisions:true },
  '566': { iso2:'NG', name:'Nigeria',        region:'EMEA', hasSubdivisions:true },
  '404': { iso2:'KE', name:'Kenya',          region:'EMEA' },
  '231': { iso2:'ET', name:'Ethiopia',       region:'EMEA', hasSubdivisions:true },
  '012': { iso2:'DZ', name:'Algeria',        region:'EMEA', hasSubdivisions:true },
  '504': { iso2:'MA', name:'Morocco',        region:'EMEA' },
  '788': { iso2:'TN', name:'Tunisia',        region:'EMEA' },
  '729': { iso2:'SD', name:'Sudan',          region:'EMEA', hasSubdivisions:true },
  '728': { iso2:'SS', name:'South Sudan',    region:'EMEA' },
  '120': { iso2:'CM', name:'Cameroon',       region:'EMEA' },
  '180': { iso2:'CD', name:'DR Congo',       region:'EMEA', hasSubdivisions:true },
  '024': { iso2:'AO', name:'Angola',         region:'EMEA', hasSubdivisions:true },
  '834': { iso2:'TZ', name:'Tanzania',       region:'EMEA', hasSubdivisions:true },
  '466': { iso2:'ML', name:'Mali',           region:'EMEA', hasSubdivisions:true },
  '562': { iso2:'NE', name:'Niger',          region:'EMEA', hasSubdivisions:true },
  '148': { iso2:'TD', name:'Chad',           region:'EMEA', hasSubdivisions:true },
  '434': { iso2:'LY', name:'Libya',          region:'EMEA', hasSubdivisions:true },
  '682': { iso2:'SA', name:'Saudi Arabia',   region:'EMEA', hasSubdivisions:true },
  '887': { iso2:'YE', name:'Yemen',          region:'EMEA' },
  '784': { iso2:'AE', name:'UAE',            region:'EMEA' },
  '364': { iso2:'IR', name:'Iran',           region:'EMEA', hasSubdivisions:true },
  '368': { iso2:'IQ', name:'Iraq',           region:'EMEA' },
  '376': { iso2:'IL', name:'Israel',         region:'EMEA' },
  // India / South Asia
  '356': { iso2:'IN', name:'India',       region:'India/SAsia', hasSubdivisions:true },
  '586': { iso2:'PK', name:'Pakistan',    region:'India/SAsia' },
  '050': { iso2:'BD', name:'Bangladesh',  region:'India/SAsia' },
  '144': { iso2:'LK', name:'Sri Lanka',   region:'India/SAsia' },
  '524': { iso2:'NP', name:'Nepal',       region:'India/SAsia' },
  '004': { iso2:'AF', name:'Afghanistan', region:'India/SAsia' },
  // APAC
  '156': { iso2:'CN', name:'China',       region:'APAC', hasSubdivisions:true },
  '158': { iso2:'TW', name:'Taiwan',      region:'APAC' },
  '392': { iso2:'JP', name:'Japan',       region:'APAC' },
  '410': { iso2:'KR', name:'South Korea', region:'APAC' },
  '408': { iso2:'KP', name:'North Korea', region:'APAC' },
  '496': { iso2:'MN', name:'Mongolia',    region:'APAC', hasSubdivisions:true },
  '360': { iso2:'ID', name:'Indonesia',   region:'APAC', hasSubdivisions:true },
  '458': { iso2:'MY', name:'Malaysia',    region:'APAC' },
  '702': { iso2:'SG', name:'Singapore',   region:'APAC' },
  '764': { iso2:'TH', name:'Thailand',    region:'APAC' },
  '704': { iso2:'VN', name:'Vietnam',     region:'APAC' },
  '608': { iso2:'PH', name:'Philippines', region:'APAC' },
  '036': { iso2:'AU', name:'Australia',   region:'APAC', hasSubdivisions:true },
  '554': { iso2:'NZ', name:'New Zealand', region:'APAC' },
  '398': { iso2:'KZ', name:'Kazakhstan',  region:'APAC', hasSubdivisions:true },
};

const REGIONS = {
  'APAC':        { label:'Asia-Pacific', center:[115, 10],  scale:0.9 },
  'EMEA':        { label:'EMEA',         center:[20, 30],   scale:0.8 },
  'Americas':    { label:'Americas',     center:[-100, 40], scale:0.9 },
  'LatAm':       { label:'Latin America',center:[-65, -15], scale:0.9 },
  'India/SAsia': { label:'India / South Asia', center:[80, 20], scale:1.3 },
};

// Major shipping lanes (lng/lat waypoints). Each knows if it's "active" (tied to a disrupted route).
const SHIPPING_LANES = [
  { id:'suez',    name:'Suez Canal route',       points:[[-5,36],[12,36],[28,32],[32.5,30],[34,27],[38,22],[43,14.5],[52,12],[60,16],[72,20],[103,3],[110,22]], disruptedBy:[1,5] },
  { id:'panama',  name:'Panama Canal route',     points:[[-74,40],[-79.5,9],[-85,8],[-95,8],[-110,10],[-135,30],[-160,35],[139,35]], disruptedBy:[3] },
  { id:'malacca', name:'Strait of Malacca',      points:[[72,8],[80,5],[95,5],[103,1.5],[108,3],[114,5],[118,22],[121,24.5],[130,32]], disruptedBy:[2] },
  { id:'hormuz',  name:'Strait of Hormuz',       points:[[48,29],[52,26],[56.5,26.5],[58,25],[60,23],[65,20]], disruptedBy:[] },
  { id:'cape',    name:'Cape of Good Hope',      points:[[-5,36],[-9,38],[-15,28],[-17,14],[-10,0],[0,-15],[12,-25],[20,-35],[32,-31],[40,-20],[45,0],[52,12]], disruptedBy:[1] },
  { id:'northsea',name:'North Sea / Baltic',     points:[[-4,50],[2,51],[4,54],[10,55],[13,55],[18,57],[25,60]], disruptedBy:[] },
  { id:'transpac',name:'Trans-Pacific',          points:[[121,31],[130,32],[140,35],[150,37],[170,40],[-170,45],[-150,45],[-130,42],[-122,37]], disruptedBy:[] },
];

const SEV_COLOR = { CRITICAL:'var(--sev-critical)', HIGH:'var(--sev-high)', MEDIUM:'var(--sev-medium)', LOW:'var(--sev-low)' };
const SEV_HEX   = { CRITICAL:'#ef4444', HIGH:'#f59e0b', MEDIUM:'#3b82f6', LOW:'#64748b' };

// Labels to always show at world level
const ALWAYS_LABELED = new Set(['US','CA','MX','BR','AR','GB','FR','DE','IT','ES','RU','CN','IN','JP','AU','ZA','EG','SA','TR','NG','ID']);

// Fetch TopoJSON once, cache in memory
let _worldCache = null;
async function loadWorld() {
  if (_worldCache) return _worldCache;
  const res = await fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
  _worldCache = await res.json();
  return _worldCache;
}

function useWorld() {
  const [topo, setTopo] = React.useState(null);
  React.useEffect(() => { loadWorld().then(setTopo).catch(e => console.error('[map] load failed', e)); }, []);
  return topo;
}

function useSize(ref) {
  const [size, setSize] = React.useState({ w: 800, h: 400 });
  React.useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(es => {
      for (const e of es) {
        const w = e.contentRect.width;
        setSize({ w, h: Math.max(360, Math.min(w * 0.55, 640)) });
      }
    });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return size;
}

function WorldMap({ events, selected, onSelect, view, onView }) {
  const ref = React.useRef(null);
  const { w, h } = useSize(ref);
  const topo = useWorld();
  const [hoverCountry, setHoverCountry] = React.useState(null);

  const projection = React.useMemo(() => {
    if (!window.d3) return null;
    // Robinson approximation via d3.geoNaturalEarth1 (Robinson isn't in d3-geo core, Natural Earth 1 is similar and looks great)
    let proj;
    if (view.kind === 'country' || view.kind === 'subdivision') {
      proj = window.d3.geoMercator();
    } else {
      proj = window.d3.geoNaturalEarth1();
    }
    proj.translate([w/2, h/2]);

    if (view.kind === 'world') {
      proj.fitExtent([[8, 8], [w - 8, h - 8]], { type:'Sphere' });
    } else if (view.kind === 'region' && REGIONS[view.region]) {
      const r = REGIONS[view.region];
      proj.center(r.center).scale((Math.min(w, h) / 2) * r.scale).translate([w/2, h/2]);
    } else if (view.kind === 'country' && topo) {
      const feats = window.topojson.feature(topo, topo.objects.countries).features;
      const country = feats.find(f => f.id === view.countryId);
      if (country) proj.fitExtent([[20,20],[w-20,h-20]], country);
    }
    return proj;
  }, [view, w, h, topo]);

  const path = React.useMemo(() => projection && window.d3 ? window.d3.geoPath(projection) : null, [projection]);

  const countries = React.useMemo(() => {
    if (!topo) return [];
    return window.topojson.feature(topo, topo.objects.countries).features;
  }, [topo]);

  // Compute severity tint per country from events
  const countrySeverity = React.useMemo(() => {
    const out = {};
    for (const ev of events) {
      const meta = Object.entries(COUNTRY_META).find(([,m]) => m.iso2 === ev.country);
      if (!meta) continue;
      const [numericId] = meta;
      const cur = out[numericId];
      const rank = { CRITICAL:4, HIGH:3, MEDIUM:2, LOW:1 };
      if (!cur || rank[ev.severity] > rank[cur]) out[numericId] = ev.severity;
    }
    return out;
  }, [events]);

  // Active shipping lanes (those hit by current event set)
  const activeEventIds = new Set(events.map(e => e.id));

  if (!topo || !projection) {
    return (
      <div ref={ref} style={{ width:'100%', height:420, background:'var(--bg-inset)', border:'1px solid var(--border-soft)', borderRadius:'var(--radius-lg)', display:'grid', placeItems:'center', color:'var(--ink-3)', fontSize:13 }}>
        <div style={{ display:'flex', gap:10, alignItems:'center' }}>
          <div style={{ width:14, height:14, border:'2px solid var(--accent)', borderTopColor:'transparent', borderRadius:'50%', animation:'spin 0.9s linear infinite' }}/>
          Loading world atlas…
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
        </div>
      </div>
    );
  }

  const drillInto = (featureId) => {
    const meta = COUNTRY_META[featureId];
    if (!meta) return;
    onView({ kind:'country', countryId: featureId, country: meta });
  };

  return (
    <div ref={ref} style={{ position:'relative', width:'100%', background:'#070c10', border:'1px solid var(--border-soft)', borderRadius:'var(--radius-lg)', overflow:'hidden' }}>
      <svg width={w} height={h} style={{ display:'block', width:'100%', height:'auto' }}>
        <defs>
          <pattern id="oceanGrid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.02)" strokeWidth="1"/>
          </pattern>
          <radialGradient id="oceanGlow" cx="50%" cy="50%" r="70%">
            <stop offset="0%" stopColor="rgba(29, 78, 100, 0.15)"/>
            <stop offset="100%" stopColor="rgba(7, 12, 16, 0)"/>
          </radialGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {/* Ocean */}
        <rect width={w} height={h} fill="#070c10"/>
        <rect width={w} height={h} fill="url(#oceanGrid)"/>
        <rect width={w} height={h} fill="url(#oceanGlow)"/>

        {/* Sphere outline (world view only) */}
        {view.kind === 'world' && (
          <path d={path({ type:'Sphere' })} fill="none" stroke="rgba(120,160,180,0.15)" strokeWidth="1"/>
        )}

        {/* Countries */}
        <g>
          {countries.map(f => {
            const id = f.id;
            const meta = COUNTRY_META[id];
            const sev = countrySeverity[id];
            const inRegion = view.kind === 'region' ? meta?.region === view.region : true;
            const isFocus = view.kind === 'country' ? id === view.countryId : true;
            const d = path(f);
            if (!d) return null;
            let fill = sev ? `color-mix(in oklch, ${SEV_HEX[sev]} 32%, #1a2a33)` : '#1a2a33';
            let opacity = 1;
            if (view.kind === 'region' && !inRegion) { fill = '#0f181d'; opacity = 0.55; }
            if (view.kind === 'country' && !isFocus) { fill = '#0f181d'; opacity = 0.4; }
            const isHover = hoverCountry === id;
            if (isHover) fill = sev ? `color-mix(in oklch, ${SEV_HEX[sev]} 55%, #1a2a33)` : '#2a3a44';
            return (
              <path key={id} d={d}
                fill={fill}
                stroke={sev ? `color-mix(in oklch, ${SEV_HEX[sev]} 70%, transparent)` : 'rgba(180, 210, 220, 0.18)'}
                strokeWidth={isHover ? 1.2 : 0.6}
                opacity={opacity}
                style={{ cursor: meta && view.kind !== 'country' ? 'pointer' : 'default', transition:'fill 0.15s' }}
                onMouseEnter={() => setHoverCountry(id)}
                onMouseLeave={() => setHoverCountry(null)}
                onClick={() => {
                  if (!meta) return;
                  if (view.kind === 'world') onView({ kind:'region', region: meta.region });
                  else if (view.kind === 'region') drillInto(id);
                  else if (view.kind === 'country' && meta.hasSubdivisions) onView({ kind:'subdivision', countryId: id, country: meta });
                }}
              />
            );
          })}
        </g>

        {/* Shipping lanes */}
        <g style={{ pointerEvents:'none' }}>
          {SHIPPING_LANES.map(lane => {
            const active = lane.disruptedBy.some(id => activeEventIds.has(id));
            const line = { type:'LineString', coordinates: lane.points };
            const d = path(line);
            if (!d) return null;
            return (
              <g key={lane.id}>
                <path d={d} fill="none" stroke="rgba(100, 140, 160, 0.18)" strokeWidth="1.2"/>
                <path d={d} fill="none"
                  stroke={active ? SEV_HEX.HIGH : 'rgba(160, 200, 220, 0.38)'}
                  strokeWidth={active ? 1.6 : 1}
                  strokeDasharray="5 5"
                  strokeLinecap="round"
                  style={active ? { animation:'laneFlow 1.8s linear infinite' } : undefined}
                />
              </g>
            );
          })}
          <style>{`@keyframes laneFlow { to { stroke-dashoffset: -20; } }`}</style>
        </g>

        {/* Country labels */}
        <g style={{ pointerEvents:'none' }}>
          {view.kind !== 'country' && countries.map(f => {
            const meta = COUNTRY_META[f.id];
            if (!meta) return null;
            const show = view.kind === 'region' ? meta.region === view.region : ALWAYS_LABELED.has(meta.iso2) || countrySeverity[f.id];
            if (!show) return null;
            const c = path.centroid(f);
            if (!Number.isFinite(c[0]) || !Number.isFinite(c[1])) return null;
            return (
              <text key={f.id} x={c[0]} y={c[1]}
                textAnchor="middle"
                fontSize={view.kind === 'region' ? 10 : 9}
                fontWeight={countrySeverity[f.id] ? 700 : 500}
                fill={countrySeverity[f.id] ? '#fff' : 'rgba(200, 220, 230, 0.55)'}
                style={{ letterSpacing:'0.02em', textShadow:'0 0 4px rgba(0,0,0,0.8)' }}
              >
                {meta.iso2}
              </text>
            );
          })}
        </g>

        {/* Event markers */}
        <g>
          {events.map(ev => {
            const p = projection([ev.lon, ev.lat]);
            if (!p) return null;
            const col = SEV_HEX[ev.severity];
            const isSel = selected?.id === ev.id;
            const r = ev.severity === 'CRITICAL' ? 7 : ev.severity === 'HIGH' ? 6 : 5;
            return (
              <g key={ev.id} style={{ cursor:'pointer' }} onClick={() => onSelect(ev)}>
                <circle cx={p[0]} cy={p[1]} r={r+14} fill={col} opacity="0.18">
                  <animate attributeName="r" values={`${r+4};${r+18};${r+4}`} dur="2.4s" repeatCount="indefinite"/>
                  <animate attributeName="opacity" values="0.3;0;0.3" dur="2.4s" repeatCount="indefinite"/>
                </circle>
                <circle cx={p[0]} cy={p[1]} r={r} fill={col} stroke="#fff" strokeWidth={isSel?2:1.2} filter="url(#glow)"/>
                {isSel && (
                  <g>
                    <rect x={p[0]+r+6} y={p[1]-18} width={Math.max(100, ev.title.length * 6.2)} height="22" rx="4" fill="rgba(7,12,16,0.92)" stroke={col} strokeWidth="1"/>
                    <text x={p[0]+r+12} y={p[1]-3} fontSize="11" fontWeight="700" fill="#fff">{ev.title}</text>
                  </g>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* Breadcrumb */}
      <div style={{ position:'absolute', top:10, left:10, display:'flex', alignItems:'center', gap:6, background:'rgba(7,12,16,0.85)', border:'1px solid var(--border-soft)', borderRadius:8, padding:'6px 10px', fontSize:12, fontWeight:500, color:'var(--ink-2)', backdropFilter:'blur(6px)' }}>
        <button className="crumb-btn" onClick={() => onView({ kind:'world' })}>
          <Icon name="globe" size={12}/>World
        </button>
        {view.kind !== 'world' && view.kind !== 'country' && view.kind !== 'subdivision' && view.region && (
          <><span style={{ color:'var(--ink-4)' }}>›</span>
          <span style={{ color:'var(--accent)', fontWeight:600 }}>{REGIONS[view.region]?.label}</span></>
        )}
        {(view.kind === 'country' || view.kind === 'subdivision') && (
          <>
            <span style={{ color:'var(--ink-4)' }}>›</span>
            <button className="crumb-btn" onClick={() => onView({ kind:'region', region: view.country?.region })}>{REGIONS[view.country?.region]?.label}</button>
            <span style={{ color:'var(--ink-4)' }}>›</span>
            <span style={{ color: view.kind === 'subdivision' ? 'var(--ink-2)' : 'var(--accent)', fontWeight:600 }}>{view.country?.name}</span>
            {view.kind === 'subdivision' && (<>
              <span style={{ color:'var(--ink-4)' }}>›</span>
              <span style={{ color:'var(--accent)', fontWeight:600 }}>Subdivisions</span>
            </>)}
          </>
        )}
      </div>

      {/* Zoom controls */}
      <div style={{ position:'absolute', top:10, right:10, display:'flex', flexDirection:'column', gap:4, background:'rgba(7,12,16,0.85)', border:'1px solid var(--border-soft)', borderRadius:8, padding:4, backdropFilter:'blur(6px)' }}>
        {view.kind !== 'world' && (
          <button className="crumb-btn" title="Back out" onClick={() => {
            if (view.kind === 'subdivision') onView({ kind:'country', countryId: view.countryId, country: view.country });
            else if (view.kind === 'country') onView({ kind:'region', region: view.country?.region });
            else onView({ kind:'world' });
          }}><Icon name="chevronLeft" size={14}/></button>
        )}
        <button className="crumb-btn" title="World" onClick={() => onView({ kind:'world' })}>
          <Icon name="globe" size={14}/>
        </button>
      </div>

      {/* Hover country tooltip */}
      {hoverCountry && COUNTRY_META[hoverCountry] && (
        <div style={{ position:'absolute', bottom:56, left:12, background:'rgba(7,12,16,0.92)', border:'1px solid var(--border)', borderRadius:8, padding:'8px 12px', fontSize:12, color:'var(--ink)' }}>
          <div style={{ fontWeight:600 }}>{COUNTRY_META[hoverCountry].name}</div>
          <div style={{ fontSize:10, color:'var(--ink-3)', marginTop:2 }}>
            {REGIONS[COUNTRY_META[hoverCountry].region]?.label} · {COUNTRY_META[hoverCountry].hasSubdivisions ? 'Drill for subdivisions' : 'Click to zoom'}
          </div>
        </div>
      )}

      {/* Legend */}
      <div style={{ position:'absolute', bottom:12, right:12, display:'flex', gap:10, flexWrap:'wrap', background:'rgba(7,12,16,0.85)', border:'1px solid var(--border-soft)', borderRadius:8, padding:'6px 10px', fontSize:11, backdropFilter:'blur(6px)' }}>
        {['CRITICAL','HIGH','MEDIUM','LOW'].map(k => (
          <span key={k} style={{ display:'inline-flex', alignItems:'center', gap:6, color:'var(--ink-2)', fontWeight:600 }}>
            <span style={{ width:9, height:9, borderRadius:'50%', background:SEV_HEX[k], boxShadow:`0 0 6px ${SEV_HEX[k]}` }}/>{k}
          </span>
        ))}
        <span style={{ display:'inline-flex', alignItems:'center', gap:6, color:'var(--ink-2)', marginLeft:6, borderLeft:'1px solid var(--border)', paddingLeft:10 }}>
          <span style={{ width:14, height:2, background:SEV_HEX.HIGH, borderRadius:1 }}/>Disrupted lane
        </span>
      </div>

      <style>{`
        .crumb-btn { display:inline-flex; align-items:center; gap:4px; padding:4px 8px; background:transparent; border:none; color:var(--ink-2); font-size:12px; font-weight:500; border-radius:4px; cursor:pointer; font-family:inherit; }
        .crumb-btn:hover { background:var(--bg-hover); color:var(--ink); }
      `}</style>
    </div>
  );
}

function LogisticsPage() {
  const [selected, setSelected] = React.useState(MOCK_SUPPLY_EVENTS[0]);
  const [filter, setFilter] = React.useState('all');
  const [view, setView] = React.useState({ kind:'world' });
  const events = filter === 'all' ? MOCK_SUPPLY_EVENTS : MOCK_SUPPLY_EVENTS.filter(e => e.severity === filter);
  const impactRows = selected ? (MOCK_EVENT_STOCKS[selected.id] || []) : [];
  return (
    <div className="page">
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-end', flexWrap:'wrap', gap:16, marginBottom:16 }}>
        <div>
          <h1>Supply Chain Logistics</h1>
          <p className="sub">Active disruptions, the companies they hit, and who picks up the gap.</p>
        </div>
        <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
          {['all','CRITICAL','HIGH','MEDIUM','LOW'].map(f => (
            <button key={f} className={'btn sm ' + (filter===f?'primary':'')} onClick={() => setFilter(f)}>{f === 'all' ? 'All' : f}</button>
          ))}
          <div style={{ borderLeft:'1px solid var(--border)', margin:'0 4px' }}/>
          {Object.entries(REGIONS).map(([k, r]) => (
            <button key={k} className={'btn sm ' + (view.kind === 'region' && view.region === k ? 'primary' : '')}
              onClick={() => setView({ kind:'region', region:k })}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'1.7fr 1fr', gap:16, alignItems:'start' }} className="logistics-grid">
        <style>{`@media (max-width: 900px) { .logistics-grid { grid-template-columns: 1fr !important; } }`}</style>

        <WorldMap events={events} selected={selected} onSelect={setSelected} view={view} onView={setView}/>

        <div className="card" style={{ padding:0, maxHeight:'calc(100vh - 300px)', overflowY:'auto' }}>
          <div style={{ padding:'14px 20px', borderBottom:'1px solid var(--border-soft)', fontWeight:600, fontSize:13 }}>
            Active events <span style={{ color:'var(--ink-3)', fontWeight:400 }}>· {events.length}</span>
          </div>
          {events.map(ev => (
            <button key={ev.id} onClick={()=>{
              setSelected(ev);
              const meta = Object.values(COUNTRY_META).find(m => m.iso2 === ev.country);
              const numericId = Object.keys(COUNTRY_META).find(k => COUNTRY_META[k].iso2 === ev.country);
              if (meta && numericId) setView({ kind:'country', countryId:numericId, country:meta });
            }} style={{
              width:'100%', background: selected?.id===ev.id ? 'var(--bg-hover)' : 'transparent',
              border:'none', borderBottom:'1px solid var(--border-soft)',
              padding:'14px 20px', textAlign:'left', cursor:'pointer',
              display:'flex', gap:12, alignItems:'flex-start', color:'var(--ink)'
            }}>
              <span style={{ width:10, height:10, marginTop:5, borderRadius:'50%', background:SEV_HEX[ev.severity], flexShrink:0, boxShadow:`0 0 0 3px ${SEV_HEX[ev.severity]}25` }}/>
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ fontWeight:600, fontSize:13 }}>{ev.title}</div>
                <div style={{ fontSize:11, color:'var(--ink-3)', marginTop:2 }}>{ev.region} · {ev.commodity}</div>
              </div>
              <span className="badge" style={{ color:SEV_HEX[ev.severity], borderColor:'transparent', background:`${SEV_HEX[ev.severity]}25` }}>{ev.severity}</span>
            </button>
          ))}
        </div>
      </div>

      {selected && (
        <div className="card" style={{ padding:0, marginTop:16 }}>
          <div style={{ padding:'16px 20px', borderBottom:'1px solid var(--border-soft)' }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', flexWrap:'wrap', gap:12 }}>
              <div>
                <div style={{ display:'flex', gap:8, alignItems:'center', marginBottom:4 }}>
                  <h3 style={{ margin:0, fontSize:16 }}>{selected.title}</h3>
                  <span className="badge" style={{ color:SEV_HEX[selected.severity], background:`${SEV_HEX[selected.severity]}25`, borderColor:'transparent' }}>{selected.severity}</span>
                  <span className="badge">{selected.status}</span>
                </div>
                <div style={{ fontSize:13, color:'var(--ink-2)', maxWidth:720, textWrap:'pretty' }}>{selected.summary}</div>
              </div>
              <div style={{ display:'flex', gap:6 }}>
                {selected.sectors.map(s => <span key={s} className="badge accent">{s}</span>)}
              </div>
            </div>
          </div>
          <div style={{ overflowX:'auto' }}>
            <table className="data-table">
              <thead><tr>
                <th>Role</th><th>Ticker</th><th>Company</th>
                <th>Cannot provide</th><th>Will redirect to</th>
              </tr></thead>
              <tbody>
                {impactRows.map((r,i) => (
                  <tr key={i}>
                    <td><span className={'badge ' + (r.role==='impacted'?'down':'up')}>{r.role}</span></td>
                    <td className="ticker">{r.ticker}</td>
                    <td>{r.company}</td>
                    <td style={{ color:'var(--ink-2)' }}>{r.cannot || <span style={{ color:'var(--ink-4)' }}>—</span>}</td>
                    <td style={{ color:'var(--ink-2)' }}>{r.redirect || <span style={{ color:'var(--ink-4)' }}>—</span>}</td>
                  </tr>
                ))}
                {impactRows.length === 0 && (
                  <tr><td colSpan="5" style={{ textAlign:'center', color:'var(--ink-3)', padding:'24px' }}>No company links yet — this event is still being ingested.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { LogisticsPage });

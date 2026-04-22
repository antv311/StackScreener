/* Settings page (workspace admin): Users, API Keys
   Preferences page (personal): Profile, Appearance, Notifications, Security */

function SettingsPage({ sub, go }) {
  const tabs = [
    { k:'users',      label:'Users',      icon:'users' },
    { k:'api',        label:'API Keys',   icon:'key' },
    { k:'alerts',     label:'Alerts',     icon:'bell' },
  ];
  // Legacy redirect: /settings/profile → /preferences/profile
  React.useEffect(() => {
    if (sub === 'profile')     { go('/preferences/profile'); }
    if (sub === 'appearance')  { go('/preferences/appearance'); }
    if (sub === 'security')    { go('/preferences/security'); }
  }, [sub]);

  return (
    <div className="page" style={{ display:'grid', gridTemplateColumns:'220px 1fr', gap:24 }}>
      <style>{`@media (max-width: 820px){ .page > nav.settings-nav{ display:flex !important; overflow-x:auto; } .page[style*="grid-template-columns"]{ grid-template-columns:1fr !important; } }`}</style>
      <nav className="settings-nav" style={{ display:'flex', flexDirection:'column', gap:2, position:'sticky', top:76, alignSelf:'start' }}>
        <div style={{ fontSize:11, fontWeight:700, color:'var(--ink-4)', textTransform:'uppercase', letterSpacing:'.08em', padding:'6px 10px 10px' }}>Workspace</div>
        {tabs.map(t => (
          <button key={t.k} onClick={() => go('/settings/'+t.k)} className="nav-btn" style={{
            display:'flex', alignItems:'center', gap:10, padding:'9px 12px',
            borderRadius:8, border:'none', textAlign:'left',
            background: sub === t.k ? 'var(--accent-soft)' : 'transparent',
            color: sub === t.k ? 'var(--accent)' : 'var(--ink-2)',
            fontSize:13, fontWeight:500, cursor:'pointer'
          }}>
            <Icon name={t.icon} size={15}/>{t.label}
          </button>
        ))}
        <div style={{ fontSize:11, fontWeight:700, color:'var(--ink-4)', textTransform:'uppercase', letterSpacing:'.08em', padding:'18px 10px 10px' }}>Personal</div>
        <button className="nav-btn" onClick={() => go('/preferences/profile')} style={{
          display:'flex', alignItems:'center', gap:10, padding:'9px 12px',
          borderRadius:8, border:'none', textAlign:'left', background:'transparent',
          color:'var(--ink-3)', fontSize:13, fontWeight:500, cursor:'pointer'
        }}>
          <Icon name="user" size={15}/>Preferences
          <Icon name="arrowUpRight" size={12} style={{ marginLeft:'auto', opacity:0.5 }}/>
        </button>
      </nav>
      <div style={{ minWidth:0 }}>
        {sub === 'users'  && <UsersSettings/>}
        {sub === 'api'    && <ApiKeysSettings/>}
        {sub === 'alerts' && <AlertsSettings/>}
        {!['users','api','alerts'].includes(sub) && <UsersSettings/>}
      </div>
    </div>
  );
}

function PreferencesPage({ sub, go }) {
  const tabs = [
    { k:'profile',       label:'Profile',       icon:'user' },
    { k:'appearance',    label:'Appearance',    icon:'sun' },
    { k:'notifications', label:'Notifications', icon:'bell' },
    { k:'security',      label:'Security',      icon:'shield' },
  ];
  return (
    <div className="page" style={{ display:'grid', gridTemplateColumns:'220px 1fr', gap:24 }}>
      <nav className="settings-nav" style={{ display:'flex', flexDirection:'column', gap:2, position:'sticky', top:76, alignSelf:'start' }}>
        <div style={{ display:'flex', gap:12, alignItems:'center', padding:'4px 10px 14px' }}>
          <div className="avatar lg" style={{ width:40, height:40, borderRadius:'50%', background:'var(--accent-soft)', color:'var(--accent)', display:'grid', placeItems:'center', fontWeight:800, fontSize:15, border:'1px solid var(--accent-border)' }}>T</div>
          <div style={{ minWidth:0 }}>
            <div style={{ fontWeight:600, fontSize:13 }}>Tony</div>
            <div style={{ fontSize:11, color:'var(--ink-3)' }}>Preferences</div>
          </div>
        </div>
        {tabs.map(t => (
          <button key={t.k} onClick={() => go('/preferences/'+t.k)} className="nav-btn" style={{
            display:'flex', alignItems:'center', gap:10, padding:'9px 12px',
            borderRadius:8, border:'none', textAlign:'left',
            background: sub === t.k ? 'var(--accent-soft)' : 'transparent',
            color: sub === t.k ? 'var(--accent)' : 'var(--ink-2)',
            fontSize:13, fontWeight:500, cursor:'pointer'
          }}>
            <Icon name={t.icon} size={15}/>{t.label}
          </button>
        ))}
      </nav>
      <div style={{ minWidth:0 }}>
        {sub === 'profile'       && <ProfileSettings/>}
        {sub === 'appearance'    && <AppearanceSettings/>}
        {sub === 'notifications' && <AlertsSettings personal/>}
        {sub === 'security'      && <SecuritySettings/>}
        {!['profile','appearance','notifications','security'].includes(sub) && <ProfileSettings/>}
      </div>
    </div>
  );
}

function SectionHeader({ title, sub }) {
  return (
    <div style={{ marginBottom:20 }}>
      <h1 style={{ margin:'0 0 4px', fontSize:22 }}>{title}</h1>
      <p className="sub" style={{ margin:0 }}>{sub}</p>
    </div>
  );
}

function ProfileSettings() {
  return (
    <>
      <SectionHeader title="Profile" sub="Your personal workspace details."/>
      <div className="card">
        <div style={{ display:'flex', gap:20, alignItems:'center', marginBottom:20 }}>
          <div style={{ width:64, height:64, borderRadius:'50%', background:'var(--accent-soft)', color:'var(--accent)', display:'grid', placeItems:'center', fontWeight:800, fontSize:22, border:'1px solid var(--accent-border)' }}>T</div>
          <div>
            <div style={{ fontWeight:600 }}>Tony</div>
            <div style={{ fontSize:12, color:'var(--ink-3)' }}>Admin · created April 2026</div>
          </div>
          <button className="btn sm" style={{ marginLeft:'auto' }}>Upload photo</button>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
          <div><label className="label">Display name</label><input className="input" defaultValue="Tony"/></div>
          <div><label className="label">Username</label><input className="input" defaultValue="admin" disabled/></div>
          <div><label className="label">Email</label><input className="input" defaultValue="tony@example.com"/></div>
          <div><label className="label">Timezone</label>
            <select className="select" defaultValue="America/New_York">
              <option>America/New_York</option><option>America/Chicago</option><option>America/Los_Angeles</option><option>UTC</option>
            </select>
          </div>
        </div>
        <div style={{ display:'flex', justifyContent:'flex-end', gap:8, marginTop:20 }}>
          <button className="btn ghost">Cancel</button><button className="btn primary">Save changes</button>
        </div>
      </div>
    </>
  );
}

function UsersSettings() {
  const [users, setUsers] = React.useState(() => StackStore.get('users', [
    { id:1, username:'admin',  display:'Tony',      email:'tony@example.com',  admin:true,  forcePwd:false, created:'2026-04-01' },
    { id:2, username:'analyst', display:'Sam Chen', email:'sam@example.com',   admin:false, forcePwd:false, created:'2026-04-05' },
    { id:3, username:'guest',   display:'Guest',    email:'guest@example.com', admin:false, forcePwd:true,  created:'2026-04-12' },
  ]));
  const [adding, setAdding] = React.useState(false);
  const [form, setForm] = React.useState({ username:'', display:'', email:'', admin:false });
  const save = () => {
    const next = [...users, { ...form, id: Date.now(), forcePwd:true, created:new Date().toISOString().slice(0,10) }];
    setUsers(next); StackStore.set({ users: next }); setAdding(false); setForm({ username:'', display:'', email:'', admin:false });
  };
  const remove = (id) => { const next = users.filter(u => u.id !== id); setUsers(next); StackStore.set({ users: next }); };
  return (
    <>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:20 }}>
        <SectionHeader title="Users" sub="Admins can add, edit, and remove workspace users."/>
        <button className="btn primary" onClick={()=>setAdding(true)}><Icon name="plus" size={14}/>Add user</button>
      </div>
      <div className="card" style={{ padding:0 }}>
        <table className="data-table">
          <thead><tr><th>User</th><th>Email</th><th>Role</th><th>Status</th><th>Created</th><th></th></tr></thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td>
                  <div style={{ display:'flex', gap:10, alignItems:'center' }}>
                    <div style={{ width:30, height:30, borderRadius:'50%', background:'var(--accent-soft)', color:'var(--accent)', display:'grid', placeItems:'center', fontWeight:700, fontSize:12 }}>{u.display[0]}</div>
                    <div><div style={{ fontWeight:600 }}>{u.display}</div><div className="mono" style={{ fontSize:11, color:'var(--ink-3)' }}>{u.username}</div></div>
                  </div>
                </td>
                <td style={{ color:'var(--ink-2)' }}>{u.email}</td>
                <td>{u.admin ? <span className="badge accent">Admin</span> : <span className="badge">Member</span>}</td>
                <td>{u.forcePwd ? <span className="badge warn">Pwd change required</span> : <span className="badge up dot">Active</span>}</td>
                <td className="mono" style={{ fontSize:12, color:'var(--ink-3)' }}>{u.created}</td>
                <td style={{ textAlign:'right' }}>
                  <button className="btn ghost sm" title="Edit"><Icon name="edit" size={14}/></button>
                  <button className="btn ghost sm" title="Delete" onClick={()=>remove(u.id)} disabled={u.username === 'admin'} style={{ color: u.username === 'admin' ? undefined : 'var(--down)' }}><Icon name="trash" size={14}/></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {adding && (
        <div className="modal-backdrop" onClick={()=>setAdding(false)}>
          <div className="modal" onClick={e=>e.stopPropagation()}>
            <h2>Add user</h2>
            <p className="sub">They'll be prompted to set a password on first login.</p>
            <div style={{ display:'grid', gap:14 }}>
              <div><label className="label">Username</label><input className="input" value={form.username} onChange={e=>setForm({...form, username:e.target.value})}/></div>
              <div><label className="label">Display name</label><input className="input" value={form.display} onChange={e=>setForm({...form, display:e.target.value})}/></div>
              <div><label className="label">Email</label><input className="input" type="email" value={form.email} onChange={e=>setForm({...form, email:e.target.value})}/></div>
              <label style={{ display:'flex', alignItems:'center', gap:10, fontSize:13 }}>
                <span className="switch"><input type="checkbox" checked={form.admin} onChange={e=>setForm({...form, admin:e.target.checked})}/><span className="track"/></span>
                Grant admin access
              </label>
            </div>
            <div className="row"><button className="btn" onClick={()=>setAdding(false)}>Cancel</button><button className="btn primary" onClick={save} disabled={!form.username||!form.email}>Create user</button></div>
          </div>
        </div>
      )}
    </>
  );
}

function ApiKeysSettings() {
  const [keys, setKeys] = React.useState(() => StackStore.get('api_keys', [
    { id:1, name:'Yahoo Finance',     url:'https://query1.finance.yahoo.com', key:'xxxx-xxxx-a4f2', connected:true,  tested:'2026-04-18' },
    { id:2, name:'SEC EDGAR',         url:'https://data.sec.gov',              key:'xxxx-xxxx-0b91', connected:true,  tested:'2026-04-17' },
    { id:3, name:'Senate Stock Watcher', url:'https://senatestockwatcher.com/api', key:'',             connected:false, tested:null },
  ]));
  const [adding, setAdding] = React.useState(false);
  const [showKey, setShowKey] = React.useState({});
  const [testing, setTesting] = React.useState(null);
  const [form, setForm] = React.useState({ name:'', url:'', key:'' });

  const persist = (next) => { setKeys(next); StackStore.set({ api_keys: next }); };
  const save = () => {
    const next = [...keys, { ...form, id: Date.now(), connected:false, tested:null }];
    persist(next); setAdding(false); setForm({ name:'', url:'', key:'' });
  };
  const remove = (id) => persist(keys.filter(k => k.id !== id));
  const test = async (id) => {
    setTesting(id);
    setTimeout(() => {
      const next = keys.map(k => k.id === id ? { ...k, connected: !!k.key, tested: new Date().toISOString().slice(0,10) } : k);
      persist(next); setTesting(null);
    }, 1100);
  };

  return (
    <>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:20 }}>
        <SectionHeader title="API Keys" sub="Keys are encrypted at rest (Fernet) and only decrypted in memory when needed."/>
        <button className="btn primary" onClick={()=>setAdding(true)}><Icon name="plus" size={14}/>Add provider</button>
      </div>

      <div style={{ display:'grid', gap:12 }}>
        {keys.map(k => (
          <div key={k.id} className="card" style={{ padding:16 }}>
            <div style={{ display:'flex', gap:16, alignItems:'flex-start' }}>
              <div style={{ width:40, height:40, borderRadius:10, background:'var(--accent-soft)', color:'var(--accent)', display:'grid', placeItems:'center', flexShrink:0 }}>
                <Icon name="key" size={18}/>
              </div>
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ display:'flex', gap:10, alignItems:'center', marginBottom:2 }}>
                  <span style={{ fontWeight:600, fontSize:14 }}>{k.name}</span>
                  {k.connected ? <span className="badge up dot">Connected</span> : <span className="badge warn dot">Not tested</span>}
                </div>
                <div style={{ fontSize:12, color:'var(--ink-3)', marginBottom:10 }}>
                  <Icon name="link" size={11}/> <span className="mono">{k.url || '(no URL)'}</span>
                  {k.tested && <> · last tested {k.tested}</>}
                </div>
                <div style={{ display:'grid', gridTemplateColumns:'1fr auto auto', gap:8, alignItems:'center' }}>
                  <div style={{ position:'relative' }}>
                    <input className="input mono" readOnly type={showKey[k.id] ? 'text' : 'password'} value={k.key || '(not set)'} style={{ paddingRight:34, fontSize:12 }}/>
                    <button className="btn ghost sm" onClick={()=>setShowKey({ ...showKey, [k.id]: !showKey[k.id] })} style={{ position:'absolute', right:4, top:'50%', transform:'translateY(-50%)' }}><Icon name={showKey[k.id]?'eyeOff':'eye'} size={14}/></button>
                  </div>
                  <button className="btn sm" onClick={()=>test(k.id)} disabled={testing === k.id || !k.key}>
                    {testing === k.id ? <><Icon name="refresh" size={12}/>Testing…</> : <><Icon name="zap" size={12}/>Test</>}
                  </button>
                  <button className="btn sm" title="Edit"><Icon name="edit" size={13}/></button>
                  <button className="btn ghost sm" onClick={()=>remove(k.id)} title="Delete" style={{ color:'var(--down)' }}><Icon name="trash" size={13}/></button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop:16, padding:14, display:'flex', gap:12, alignItems:'flex-start', background:'var(--bg-inset)' }}>
        <Icon name="shield" size={16} /><div style={{ fontSize:12, color:'var(--ink-3)', lineHeight:1.6 }}>
          Keys stored in <span className="mono">api_keys</span> table — encrypted with Fernet (cryptography library); master key lives in the OS keyring. Plaintext only exists in process memory during active requests.
        </div>
      </div>

      {adding && (
        <div className="modal-backdrop" onClick={()=>setAdding(false)}>
          <div className="modal" onClick={e=>e.stopPropagation()}>
            <h2>Add API provider</h2>
            <p className="sub">Store any REST endpoint by name. Hit Test after saving to verify connectivity.</p>
            <div style={{ display:'grid', gap:14 }}>
              <div><label className="label">Provider name</label><input className="input" placeholder="e.g. Quiver Quant" value={form.name} onChange={e=>setForm({...form, name:e.target.value})}/></div>
              <div><label className="label">Base URL</label><input className="input mono" placeholder="https://api.provider.com/v1" value={form.url} onChange={e=>setForm({...form, url:e.target.value})}/></div>
              <div><label className="label">API Key</label><input className="input mono" type="password" placeholder="sk-xxxxxxxxxxxx" value={form.key} onChange={e=>setForm({...form, key:e.target.value})}/>
                <div className="helper">Encrypted before saving — never written to disk in plaintext.</div>
              </div>
            </div>
            <div className="row"><button className="btn" onClick={()=>setAdding(false)}>Cancel</button><button className="btn primary" onClick={save} disabled={!form.name}>Save provider</button></div>
          </div>
        </div>
      )}
    </>
  );
}

function AlertsSettings() {
  const opts = [
    { k:'scan_daily',      label:'Run daily scan',          desc:'Pre-market scan of your watchlist + top 500 symbols', def:true },
    { k:'new_event',       label:'New supply chain event',  desc:'Email me when a CRITICAL or HIGH severity disruption is detected', def:true },
    { k:'score_threshold', label:'Composite score > 85',    desc:'Alert when any holding crosses the threshold', def:false },
    { k:'congress_buy',    label:'Congressional trade',     desc:'Any new filing by a member tied to one of my watchlist stocks', def:true },
    { k:'earnings_day',    label:'Earnings day digest',     desc:'Summary the morning of any watchlist earnings', def:false },
  ];
  return (
    <>
      <SectionHeader title="Alerts &amp; automation" sub="Let StackScreener run unattended and email you what matters."/>
      <div className="card" style={{ padding:0 }}>
        {opts.map((o,i) => (
          <div key={o.k} style={{ display:'flex', gap:16, alignItems:'center', padding:'16px 20px', borderBottom: i < opts.length - 1 ? '1px solid var(--border-soft)' : 'none' }}>
            <div style={{ flex:1 }}>
              <div style={{ fontWeight:600, fontSize:13 }}>{o.label}</div>
              <div style={{ fontSize:12, color:'var(--ink-3)', marginTop:3 }}>{o.desc}</div>
            </div>
            <label className="switch"><input type="checkbox" defaultChecked={o.def}/><span className="track"/></label>
          </div>
        ))}
      </div>
      <div className="card" style={{ marginTop:16 }}>
        <h3 style={{ margin:'0 0 4px', fontSize:14 }}>Delivery</h3>
        <p className="card-sub">Where alerts are sent.</p>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
          <div><label className="label">Email</label><input className="input" defaultValue="tony@example.com"/></div>
          <div><label className="label">Webhook (optional)</label><input className="input mono" placeholder="https://..." /></div>
        </div>
      </div>
    </>
  );
}

function AppearanceSettings() {
  const s = StackStore.use();
  const accents = [
    { k:155, label:'Emerald' }, { k:180, label:'Teal' }, { k:220, label:'Azure' },
    { k:280, label:'Violet' }, { k:330, label:'Rose' }, { k:70,  label:'Amber' },
  ];
  return (
    <>
      <SectionHeader title="Appearance" sub="Theme, density, and accent color."/>
      <div className="card">
        <h3 style={{ margin:'0 0 12px', fontSize:14 }}>Theme</h3>
        <div style={{ display:'flex', gap:10 }}>
          {['dark','light','auto'].map(t => (
            <button key={t} className={'btn ' + (s.theme === t || (!s.theme && t === 'dark') ? 'primary' : '')} onClick={() => { StackStore.set({ theme: t }); document.documentElement.dataset.theme = t === 'auto' ? (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light') : t; }}>
              <Icon name={t==='dark'?'moon':t==='light'?'sun':'sliders'} size={14}/>
              {t[0].toUpperCase()+t.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <div className="card" style={{ marginTop:16 }}>
        <h3 style={{ margin:'0 0 12px', fontSize:14 }}>Accent color</h3>
        <div style={{ display:'flex', gap:10, flexWrap:'wrap' }}>
          {accents.map(a => (
            <button key={a.k} onClick={()=>{ StackStore.set({ accent: a.k }); document.documentElement.style.setProperty('--accent-h', a.k); }}
              style={{ display:'flex', gap:10, padding:'8px 14px 8px 10px', border:'1px solid var(--border)', borderRadius:10, alignItems:'center', background:(s.accent||155)==a.k?'var(--bg-hover)':'var(--bg-card)', cursor:'pointer', color:'var(--ink)' }}>
              <span style={{ width:22, height:22, borderRadius:6, background:`oklch(0.72 0.15 ${a.k})` }}/>
              <span style={{ fontSize:13, fontWeight:500 }}>{a.label}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}

function SecuritySettings() {
  return (
    <>
      <SectionHeader title="Security" sub="Password and two-factor authentication."/>
      <div className="card">
        <h3 style={{ margin:'0 0 4px', fontSize:14 }}>Change password</h3>
        <p className="card-sub">PBKDF2-HMAC-SHA256, 260,000 iterations.</p>
        <div style={{ display:'grid', gap:12, maxWidth:440 }}>
          <div><label className="label">Current password</label><input className="input" type="password"/></div>
          <div><label className="label">New password</label><input className="input" type="password"/></div>
          <div><label className="label">Confirm new password</label><input className="input" type="password"/></div>
        </div>
        <div style={{ display:'flex', justifyContent:'flex-end', marginTop:16 }}><button className="btn primary">Update password</button></div>
      </div>

      <div className="card" style={{ marginTop:16 }}>
        <div style={{ display:'flex', gap:16, alignItems:'flex-start' }}>
          <div style={{ width:40, height:40, borderRadius:10, background:'var(--accent-soft)', color:'var(--accent)', display:'grid', placeItems:'center' }}><Icon name="lock" size={18}/></div>
          <div style={{ flex:1 }}>
            <h3 style={{ margin:'0 0 4px', fontSize:14 }}>Two-factor authentication <span className="badge warn" style={{ marginLeft:6 }}>Coming soon</span></h3>
            <p className="card-sub">The <span className="mono">totp_secret</span> column is reserved on the users table. 2FA enrollment will be available in a future release.</p>
            <button className="btn" disabled>Set up authenticator</button>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop:16 }}>
        <h3 style={{ margin:'0 0 4px', fontSize:14 }}>Sessions</h3>
        <p className="card-sub">Active devices on your account.</p>
        <div style={{ display:'flex', gap:12, padding:'12px 14px', background:'var(--bg-inset)', borderRadius:10, alignItems:'center' }}>
          <span className="badge up dot">Current</span>
          <div style={{ flex:1, fontSize:13 }}>Chrome · macOS · NYC, US</div>
          <span style={{ fontSize:12, color:'var(--ink-3)' }}>Signed in just now</span>
        </div>
      </div>
    </>
  );
}

Object.assign(window, { SettingsPage, PreferencesPage });

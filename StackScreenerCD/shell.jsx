/* Shell: sidebar, topbar, router */

const NAV_ITEMS = [
  { key:'home',      label:'Home',      icon:'home',       path:'/home' },
  { key:'research',  label:'Research',  icon:'research',   path:'/research' },
  { key:'logistics', label:'Logistics', icon:'logistics',  path:'/logistics' },
];
const FOOTER_ITEMS = [
  { key:'settings',  label:'Settings',  icon:'settings',   path:'/settings' },
];

function SidebarPill({ current, go, logo }) {
  return (
    <nav className="sidebar-pill-nav">
      <div className="brand">
        <Logo variant={logo} size={22} />
      </div>
      {NAV_ITEMS.map(it => (
        <button key={it.key} className={'nav-btn' + (current.startsWith(it.path) ? ' active' : '')} onClick={() => go(it.path)}>
          <Icon name={it.icon} size={16}/>{it.label}
        </button>
      ))}
      <div className="footer">
        {FOOTER_ITEMS.map(it => (
          <button key={it.key} className={'nav-btn' + (current.startsWith(it.path) ? ' active' : '')} onClick={() => go(it.path)}>
            <Icon name={it.icon} size={16}/>{it.label}
          </button>
        ))}
        <button className="nav-btn" onClick={() => go('/login')}>
          <Icon name="logout" size={16}/>Sign out
        </button>
      </div>
    </nav>
  );
}

function SidebarFlat({ current, go, logo }) {
  return (
    <nav className="sidebar-flat-nav">
      <div className="brand">
        <Logo variant={logo} size={20} />
      </div>
      <div className="section-label">Workspace</div>
      {NAV_ITEMS.map(it => (
        <button key={it.key} className={'nav-btn' + (current.startsWith(it.path) ? ' active' : '')} onClick={() => go(it.path)}>
          <Icon name={it.icon} size={16}/>{it.label}
        </button>
      ))}
      <div className="footer">
        {FOOTER_ITEMS.map(it => (
          <button key={it.key} className={'nav-btn' + (current.startsWith(it.path) ? ' active' : '')} onClick={() => go(it.path)}>
            <Icon name={it.icon} size={16}/>{it.label}
          </button>
        ))}
        <button className="nav-btn" onClick={() => go('/login')}>
          <Icon name="logout" size={16}/>Sign out
        </button>
      </div>
    </nav>
  );
}

function SidebarRail({ current, go, logo }) {
  return (
    <nav className="sidebar-rail-nav">
      <div className="brand-mark">
        <Logo variant={logo} size={28} showWord={false} />
      </div>
      {NAV_ITEMS.map(it => (
        <button key={it.key} className={'nav-btn' + (current.startsWith(it.path) ? ' active' : '')} onClick={() => go(it.path)}>
          <Icon name={it.icon} size={20}/>
          <span className="tip">{it.label}</span>
        </button>
      ))}
      <div className="footer">
        {FOOTER_ITEMS.map(it => (
          <button key={it.key} className={'nav-btn' + (current.startsWith(it.path) ? ' active' : '')} onClick={() => go(it.path)}>
            <Icon name={it.icon} size={20}/>
            <span className="tip">{it.label}</span>
          </button>
        ))}
        <button className="nav-btn" onClick={() => go('/login')}>
          <Icon name="logout" size={20}/>
          <span className="tip">Sign out</span>
        </button>
      </div>
    </nav>
  );
}

function Topbar({ current }) {
  const crumb = (() => {
    if (current.startsWith('/home')) return ['Home'];
    if (current.startsWith('/research')) {
      const sub = current.split('/')[2] || 'screener';
      const map = { screener:'Screener', calendar:'Calendar', comparison:'Comparison', picks:'Stock Picks', reports:'Research Reports' };
      return ['Research', map[sub] || 'Screener'];
    }
    if (current.startsWith('/logistics')) return ['Logistics'];
    if (current.startsWith('/settings')) {
      const sub = current.split('/')[2] || 'users';
      const map = { users:'Users', api:'API Keys', alerts:'Alerts', appearance:'Appearance', security:'Security' };
      return ['Settings', map[sub] || 'Users'];
    }
    if (current.startsWith('/preferences')) {
      const sub = current.split('/')[2] || 'profile';
      const map = { profile:'Profile', appearance:'Appearance', notifications:'Notifications', security:'Security' };
      return ['Preferences', map[sub] || 'Profile'];
    }
    return ['StackScreener'];
  })();

  return <TopbarInner crumb={crumb}/>;
}

function TopbarInner({ crumb }) {
  const [, go] = useRoute();
  const [open, setOpen] = React.useState(false);
  const menuRef = React.useRef(null);
  React.useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (menuRef.current && !menuRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const goTo = (p) => { setOpen(false); go(p); };

  return (
    <header className="topbar">
      <div className="crumbs">
        {crumb.map((c, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span className="sep">/</span>}
            <span className={i === crumb.length - 1 ? 'current' : ''}>{c}</span>
          </React.Fragment>
        ))}
      </div>
      <div className="search">
        <span className="icon"><Icon name="search" size={15}/></span>
        <input placeholder="Search ticker, company, sector…"/>
      </div>
      <button className="btn ghost sm" title="Notifications"><Icon name="bell" size={16}/></button>
      <div ref={menuRef} style={{ position:'relative' }}>
        <button className="user-chip" title="Account menu" onClick={() => setOpen(o => !o)} aria-expanded={open} style={{ cursor:'pointer' }}>
          <div className="avatar">T</div>
          <span style={{ fontSize: 12, color:'var(--ink-2)', fontWeight: 500 }}>Tony</span>
          <Icon name="chevronDown" size={13}/>
        </button>
        {open && (
          <div className="user-menu">
            <div className="user-menu-head">
              <div className="avatar lg">T</div>
              <div style={{ minWidth:0 }}>
                <div style={{ fontWeight:600, fontSize:13 }}>Tony</div>
                <div style={{ fontSize:11, color:'var(--ink-3)' }}>tony@example.com</div>
                <div style={{ marginTop:4 }}><span className="badge accent">Admin</span></div>
              </div>
            </div>
            <div className="user-menu-group">
              <button className="user-menu-item" onClick={() => goTo('/preferences/profile')}><Icon name="user" size={14}/>Profile</button>
              <button className="user-menu-item" onClick={() => goTo('/preferences/appearance')}><Icon name="sun" size={14}/>Appearance</button>
              <button className="user-menu-item" onClick={() => goTo('/preferences/notifications')}><Icon name="bell" size={14}/>Notifications</button>
              <button className="user-menu-item" onClick={() => goTo('/preferences/security')}><Icon name="shield" size={14}/>Security</button>
            </div>
            <div className="user-menu-group">
              <button className="user-menu-item" onClick={() => goTo('/settings/users')}><Icon name="settings" size={14}/>Workspace settings</button>
            </div>
            <div className="user-menu-group">
              <button className="user-menu-item danger" onClick={() => goTo('/login')}><Icon name="logout" size={14}/>Sign out</button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}

// Hash-based router
function useRoute() {
  const [hash, setHash] = React.useState(window.location.hash || '#/home');
  React.useEffect(() => {
    const onHash = () => setHash(window.location.hash || '#/home');
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  const path = hash.replace(/^#/, '') || '/home';
  const go = (p) => { window.location.hash = p; };
  return [path, go];
}

Object.assign(window, { SidebarPill, SidebarFlat, SidebarRail, Topbar, useRoute });

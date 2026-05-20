import { useState, useEffect, useRef } from "react";

const API = "http://localhost:8000";

const MOCK = {
  stats: {
    total_gstins: 5000, critical_count: 56, high_count: 485,
    medium_count: 471, low_count: 3988, total_alerts: 541,
    alert_rate: 10.82, avg_risk_score: 18.4,
    fraud_type_breakdown: {
      fake_itc: 316, circular_trading: 212,
      shell_company: 213, missing_returns: 164, sudden_spike: 95
    },
  },
  topRisks: [
    { rank:1, gstin:"27VVZYP7446E1ZH", ensemble_score:97.0, risk_level:"CRITICAL", fraud_type:"shell_company",    xgb_score:99.5, anomaly_score:70.4, graph_risk_score:89.7, in_circular_ring:true,  models_agreeing:4 },
    { rank:2, gstin:"17WTALS7186N2ZN", ensemble_score:95.7, risk_level:"CRITICAL", fraud_type:"sudden_spike",     xgb_score:98.8, anomaly_score:100,  graph_risk_score:82.3, in_circular_ring:false, models_agreeing:4 },
    { rank:3, gstin:"12XUUHW6959P3Z3", ensemble_score:95.4, risk_level:"CRITICAL", fraud_type:"fake_itc",         xgb_score:99.9, anomaly_score:67.2, graph_risk_score:85.9, in_circular_ring:true,  models_agreeing:4 },
    { rank:4, gstin:"09ZKRQH3507F9ZW", ensemble_score:94.7, risk_level:"CRITICAL", fraud_type:"missing_returns",  xgb_score:98.7, anomaly_score:76.8, graph_risk_score:75.7, in_circular_ring:true,  models_agreeing:3 },
    { rank:5, gstin:"20JRFBA7800W2ZY", ensemble_score:93.6, risk_level:"CRITICAL", fraud_type:"sudden_spike",     xgb_score:98.4, anomaly_score:61.8, graph_risk_score:82.8, in_circular_ring:false, models_agreeing:3 },
    { rank:6, gstin:"32ZAVWR7364E2Z9", ensemble_score:93.3, risk_level:"CRITICAL", fraud_type:"shell_company",    xgb_score:98.1, anomaly_score:76.2, graph_risk_score:75.8, in_circular_ring:true,  models_agreeing:3 },
    { rank:7, gstin:"33CFEQA4862C2ZP", ensemble_score:92.5, risk_level:"CRITICAL", fraud_type:"shell_company",    xgb_score:99.6, anomaly_score:66.1, graph_risk_score:75.8, in_circular_ring:false, models_agreeing:3 },
    { rank:8, gstin:"36FCOMK2625P8Z2", ensemble_score:91.4, risk_level:"CRITICAL", fraud_type:"fake_itc",         xgb_score:99.8, anomaly_score:71.2, graph_risk_score:66.0, in_circular_ring:false, models_agreeing:3 },
    { rank:9, gstin:"08RZTZL1694W5ZG", ensemble_score:89.3, risk_level:"HIGH",     fraud_type:"fake_itc",         xgb_score:99.9, anomaly_score:74.6, graph_risk_score:83.1, in_circular_ring:false, models_agreeing:3 },
    { rank:10,gstin:"05BDITF0160Z2ZT", ensemble_score:87.7, risk_level:"HIGH",     fraud_type:"shell_company",    xgb_score:98.9, anomaly_score:83.6, graph_risk_score:52.6, in_circular_ring:false, models_agreeing:3 },
  ]
};

const riskColor = l => ({ CRITICAL:"#FF3B5C", HIGH:"#FF8C00", MEDIUM:"#FFD60A", LOW:"#30D158" }[l] || "#8E8E93");
const riskBg    = l => ({ CRITICAL:"rgba(255,59,92,0.12)", HIGH:"rgba(255,140,0,0.12)", MEDIUM:"rgba(255,214,10,0.12)", LOW:"rgba(48,209,88,0.12)" }[l] || "rgba(142,142,147,0.12)");
const fraudIcon = t => ({ fake_itc:"⚡", circular_trading:"🔄", shell_company:"👻", missing_returns:"📭", sudden_spike:"📈" }[t] || "⚠️");

function AnimatedNumber({ value, suffix = "", decimals = 0 }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    let start = 0, end = parseFloat(value), dur = 1400, step = 16;
    const inc = end / (dur / step);
    clearInterval(ref.current);
    ref.current = setInterval(() => {
      start += inc;
      if (start >= end) { setDisplay(end); clearInterval(ref.current); }
      else setDisplay(start);
    }, step);
    return () => clearInterval(ref.current);
  }, [value]);
  return <span>{display.toFixed(decimals)}{suffix}</span>;
}

function MiniBar({ value, max, color }) {
  const [w, setW] = useState(0);
  useEffect(() => { const t = setTimeout(() => setW((value/max)*100), 100); return () => clearTimeout(t); }, [value, max]);
  return (
    <div style={{ display:"flex", alignItems:"center", gap:8 }}>
      <div style={{ flex:1, height:5, background:"rgba(255,255,255,0.06)", borderRadius:3, overflow:"hidden" }}>
        <div style={{ height:"100%", borderRadius:3, background:color, width:`${w}%`, transition:"width 1.2s cubic-bezier(.4,0,.2,1)", boxShadow:`0 0 8px ${color}80` }} />
      </div>
      <span style={{ fontSize:11, color:"#8E8E93", minWidth:36, textAlign:"right", fontFamily:"'DM Mono',monospace" }}>{value.toLocaleString()}</span>
    </div>
  );
}

function ScoreGauge({ score, size = 52 }) {
  const r = (size - 10) / 2;
  const circ = 2 * Math.PI * r;
  const [dash, setDash] = useState(0);
  const color = score >= 81 ? "#FF3B5C" : score >= 61 ? "#FF8C00" : score >= 31 ? "#FFD60A" : "#30D158";
  useEffect(() => { const t = setTimeout(() => setDash((score/100)*circ), 200); return () => clearTimeout(t); }, [score, circ]);
  return (
    <div style={{ position:"relative", width:size, height:size }}>
      <svg width={size} height={size} style={{ transform:"rotate(-90deg)", position:"absolute" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={5} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={5}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
          style={{ transition:"stroke-dasharray 1s cubic-bezier(.4,0,.2,1)", filter:`drop-shadow(0 0 5px ${color})` }} />
      </svg>
      <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", fontSize:10, fontWeight:700, color, fontFamily:"'DM Mono',monospace" }}>
        {score?.toFixed(0)}
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, color, icon, delay = 0 }) {
  const [vis, setVis] = useState(false);
  useEffect(() => { const t = setTimeout(() => setVis(true), delay); return () => clearTimeout(t); }, [delay]);
  return (
    <div style={{
      background:"rgba(255,255,255,0.03)", border:"1px solid rgba(255,255,255,0.07)",
      borderRadius:20, padding:"22px 24px", position:"relative", overflow:"hidden",
      opacity:vis?1:0, transform:vis?"translateY(0)":"translateY(20px)",
      transition:"opacity 0.5s ease, transform 0.5s ease",
    }}>
      <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:`linear-gradient(90deg,transparent,${color},transparent)` }} />
      <div style={{ position:"absolute", top:-40, right:-40, width:100, height:100, borderRadius:"50%", background:color, opacity:0.05, filter:"blur(25px)" }} />
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
        <div>
          <div style={{ fontSize:12, color:"#8E8E93", marginBottom:8, letterSpacing:"0.03em" }}>{label}</div>
          <div style={{ fontSize:34, fontWeight:800, color:"#F5F5F7", fontFamily:"'DM Mono',monospace", lineHeight:1 }}>
            <AnimatedNumber value={value} />
          </div>
          {sub && <div style={{ fontSize:12, color, marginTop:6, fontWeight:500 }}>{sub}</div>}
        </div>
        <div style={{ fontSize:30 }}>{icon}</div>
      </div>
    </div>
  );
}

function GSTINModal({ gstin, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetch(`${API}/api/gstin/${gstin}`).then(r=>r.json()).then(d=>{setData(d);setLoading(false);}).catch(()=>setLoading(false));
  }, [gstin]);
  const level = data?.risk_summary?.risk_level || "LOW";
  const color = riskColor(level);
  return (
    <div onClick={onClose} style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.85)", backdropFilter:"blur(16px)", zIndex:1000, display:"flex", alignItems:"center", justifyContent:"center", animation:"fadeIn 0.2s ease" }}>
      <div onClick={e=>e.stopPropagation()} style={{ background:"#141416", border:"1px solid rgba(255,255,255,0.1)", borderRadius:24, padding:32, width:"min(560px,92vw)", maxHeight:"85vh", overflowY:"auto", animation:"slideUp 0.3s ease" }}>
        {loading ? (
          <div style={{ textAlign:"center", padding:48, color:"#8E8E93" }}>
            <div style={{ fontSize:36, animation:"spin 0.8s linear infinite", display:"inline-block" }}>⟳</div>
            <div style={{ marginTop:12, fontSize:14 }}>Loading investigation report...</div>
          </div>
        ) : data ? (
          <>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:24 }}>
              <div>
                <div style={{ fontSize:11, color:"#8E8E93", letterSpacing:"0.08em", marginBottom:6 }}>INVESTIGATION REPORT</div>
                <div style={{ fontSize:17, fontWeight:700, color:"#F5F5F7", fontFamily:"'DM Mono',monospace" }}>{gstin}</div>
                <div style={{ fontSize:13, color:"#8E8E93", marginTop:4 }}>{data.company_info?.company_name}</div>
                <div style={{ fontSize:12, color:"#8E8E93", marginTop:2 }}>📍 {data.company_info?.state} • {data.company_info?.industry}</div>
              </div>
              <div style={{ textAlign:"right" }}>
                <div style={{ padding:"4px 14px", borderRadius:20, background:riskBg(level), color, fontSize:12, fontWeight:700, border:`1px solid ${color}40`, marginBottom:8, display:"inline-block" }}>{level} RISK</div>
                <div style={{ fontSize:42, fontWeight:900, color, fontFamily:"'DM Mono',monospace", lineHeight:1 }}>
                  {data.risk_summary?.ensemble_score?.toFixed(1)}%
                </div>
                {data.risk_summary?.in_circular_ring && <div style={{ fontSize:11, color:"#FF8C00", marginTop:4 }}>🔄 In circular trading ring</div>}
              </div>
            </div>

            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:20 }}>
              {[
                { label:"XGBoost", val:data.score_breakdown?.xgb_score,        color:"#0A84FF", icon:"🤖" },
                { label:"Anomaly", val:data.score_breakdown?.anomaly_score,     color:"#BF5AF2", icon:"🎯" },
                { label:"Graph",   val:data.score_breakdown?.graph_risk_score,  color:"#FF9F0A", icon:"🕸️" },
                { label:"Rules",   val:data.score_breakdown?.rule_score,        color:"#30D158", icon:"📋" },
              ].map(({label,val,color:c,icon}) => (
                <div key={label} style={{ background:"rgba(255,255,255,0.04)", borderRadius:14, padding:"14px 16px" }}>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
                    <span style={{ fontSize:12, color:"#8E8E93" }}>{icon} {label}</span>
                    <span style={{ fontSize:20, fontWeight:800, color:c, fontFamily:"'DM Mono',monospace" }}>{val?.toFixed(1)}%</span>
                  </div>
                  <div style={{ height:4, background:"rgba(255,255,255,0.06)", borderRadius:2, overflow:"hidden" }}>
                    <div style={{ height:"100%", width:`${val}%`, background:c, borderRadius:2, boxShadow:`0 0 6px ${c}` }} />
                  </div>
                </div>
              ))}
            </div>

            {data.rule_flags?.length > 0 && (
              <div style={{ background:"rgba(255,59,92,0.06)", border:"1px solid rgba(255,59,92,0.2)", borderRadius:14, padding:16, marginBottom:14 }}>
                <div style={{ fontSize:11, color:"#FF3B5C", fontWeight:700, marginBottom:10, letterSpacing:"0.06em" }}>⚠️ FRAUD INDICATORS DETECTED</div>
                {data.rule_flags.map((f,i)=>(
                  <div key={i} style={{ fontSize:13, color:"#F5F5F7", padding:"5px 0", borderBottom:i<data.rule_flags.length-1?"1px solid rgba(255,255,255,0.05)":"none" }}>
                    • {f}
                  </div>
                ))}
              </div>
            )}

            <div style={{ background:"rgba(255,255,255,0.03)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:14, padding:16, marginBottom:16 }}>
              <div style={{ fontSize:11, color:"#8E8E93", fontWeight:700, marginBottom:8, letterSpacing:"0.06em" }}>📋 RECOMMENDATION</div>
              <div style={{ fontSize:13, color:"#F5F5F7", lineHeight:1.7 }}>{data.recommendation}</div>
            </div>

            <button onClick={onClose} style={{ width:"100%", padding:14, borderRadius:12, background:"rgba(255,255,255,0.06)", border:"1px solid rgba(255,255,255,0.1)", color:"#F5F5F7", fontSize:14, cursor:"pointer", fontFamily:"inherit", fontWeight:500 }}>
              Close Report
            </button>
          </>
        ) : (
          <div style={{ textAlign:"center", padding:40, color:"#8E8E93" }}>
            <div style={{ fontSize:40, marginBottom:12 }}>⚠️</div>
            <div>Could not load report — API may be offline</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [stats, setStats] = useState(null);
  const [topRisks, setTopRisks] = useState([]);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedGstin, setSelectedGstin] = useState(null);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [alerts, setAlerts] = useState([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/dashboard/stats`).then(r=>r.json()),
      fetch(`${API}/api/top-risks?n=10`).then(r=>r.json()),
    ]).then(([s,t]) => {
      setStats(s); setTopRisks(t.top_risks||[]); setApiOnline(true);
    }).catch(() => {
      setStats(MOCK.stats); setTopRisks(MOCK.topRisks);
    }).finally(() => setLoaded(true));
  }, []);

  useEffect(() => {
    if (activeTab !== "alerts") return;
    setAlertsLoading(true);
    fetch(`${API}/api/alerts?page_size=50`)
      .then(r=>r.json()).then(d=>setAlerts(d.alerts||[]))
      .catch(()=>setAlerts(MOCK.topRisks))
      .finally(()=>setAlertsLoading(false));
  }, [activeTab]);

  useEffect(() => {
    if (!search.trim() || search.length < 3) { setSearchResults([]); return; }
    const t = setTimeout(() => {
      setSearching(true);
      fetch(`${API}/api/search?q=${search}&limit=8`)
        .then(r=>r.json()).then(d=>setSearchResults(d.results||[]))
        .catch(()=>setSearchResults([]))
        .finally(()=>setSearching(false));
    }, 350);
    return () => clearTimeout(t);
  }, [search]);

  const fraudTypes = stats?.fraud_type_breakdown || {};
  const maxFraud = Math.max(...Object.values(fraudTypes), 1);

  if (!loaded) return (
    <div style={{ minHeight:"100vh", background:"#0A0A0B", display:"flex", alignItems:"center", justifyContent:"center", flexDirection:"column", gap:16 }}>
      <div style={{ width:52, height:52, border:"3px solid rgba(255,255,255,0.08)", borderTop:"3px solid #FF3B5C", borderRadius:"50%", animation:"spin 0.8s linear infinite" }} />
      <div style={{ color:"#8E8E93", fontSize:13, fontFamily:"'DM Mono',monospace", letterSpacing:"0.05em" }}>LOADING FRAUD INTELLIGENCE...</div>
    </div>
  );

  return (
    <div style={{ minHeight:"100vh", background:"#0A0A0B", color:"#F5F5F7", fontFamily:"'Sora',sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=DM+Mono:ital,wght@0,400;0,500;1,400&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes fadeIn{from{opacity:0}to{opacity:1}}
        @keyframes slideUp{from{transform:translateY(28px);opacity:0}to{transform:translateY(0);opacity:1}}
        @keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
        @keyframes glow{0%,100%{box-shadow:0 0 20px rgba(255,59,92,0.3)}50%{box-shadow:0 0 40px rgba(255,59,92,0.6)}}
        @keyframes scan{0%{transform:translateY(-100%)}100%{transform:translateY(400%)}}
        .nav-btn{background:none;border:none;cursor:pointer;padding:8px 20px;border-radius:10px;font-family:inherit;font-size:13px;font-weight:500;transition:all 0.2s;letter-spacing:0.02em}
        .nav-btn:hover{background:rgba(255,255,255,0.06)}
        .nav-btn.active{background:rgba(255,59,92,0.12);color:#FF3B5C}
        .row-hover{transition:background 0.15s}
        .row-hover:hover{background:rgba(255,255,255,0.04)!important;cursor:pointer}
        .search-input:focus{outline:none;border-color:rgba(255,59,92,0.6)!important;box-shadow:0 0 0 3px rgba(255,59,92,0.1)}
        .tab-content{animation:fadeIn 0.3s ease}
        .hint-btn:hover{background:rgba(255,255,255,0.08)!important;color:#F5F5F7!important}
      `}</style>

      {/* Header */}
      <header style={{ padding:"14px 32px", display:"flex", alignItems:"center", justifyContent:"space-between", borderBottom:"1px solid rgba(255,255,255,0.06)", position:"sticky", top:0, zIndex:100, background:"rgba(10,10,11,0.92)", backdropFilter:"blur(24px)" }}>
        <div style={{ display:"flex", alignItems:"center", gap:14 }}>
          <div style={{ width:40, height:40, borderRadius:13, background:"linear-gradient(135deg,#FF3B5C,#FF6B00)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:20, animation:"float 4s ease-in-out infinite", boxShadow:"0 4px 24px rgba(255,59,92,0.35)" }}>🛡️</div>
          <div>
            <div style={{ fontSize:15, fontWeight:700, letterSpacing:"-0.02em" }}>GST FraudShield</div>
            <div style={{ fontSize:11, color:"#8E8E93", letterSpacing:"0.04em" }}>AI-POWERED TAX INTELLIGENCE</div>
          </div>
        </div>

        <nav style={{ display:"flex", gap:2 }}>
          {[["dashboard","📊","Dashboard"],["alerts","🚨","Alerts"],["search","🔍","Search"]].map(([id,icon,label])=>(
            <button key={id} className={`nav-btn ${activeTab===id?"active":""}`} onClick={()=>setActiveTab(id)}
              style={{ color:activeTab===id?"#FF3B5C":"#8E8E93" }}>
              {icon} {label}
            </button>
          ))}
        </nav>

        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <div style={{ width:8, height:8, borderRadius:"50%", background:apiOnline?"#30D158":"#FF3B5C", boxShadow:`0 0 8px ${apiOnline?"#30D158":"#FF3B5C"}`, animation:"glow 2s ease-in-out infinite" }} />
          <span style={{ fontSize:12, color:"#8E8E93" }}>{apiOnline?"API Connected":"Demo Mode"}</span>
        </div>
      </header>

      <main style={{ maxWidth:1300, margin:"0 auto", padding:"28px 24px" }}>

        {/* DASHBOARD */}
        {activeTab==="dashboard" && (
          <div className="tab-content">
            <div style={{ marginBottom:24, display:"flex", justifyContent:"space-between", alignItems:"flex-end" }}>
              <div>
                <h1 style={{ fontSize:26, fontWeight:800, letterSpacing:"-0.02em" }}>Fraud Intelligence Dashboard</h1>
                <p style={{ fontSize:13, color:"#8E8E93", marginTop:4 }}>Real-time GST fraud detection across {(stats?.total_gstins||5000).toLocaleString()} registered taxpayers</p>
              </div>
              <div style={{ fontSize:12, color:"#8E8E93", fontFamily:"'DM Mono',monospace" }}>{new Date().toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}</div>
            </div>

            <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:14, marginBottom:24 }}>
              <StatCard label="Total GSTINs Analyzed" value={stats?.total_gstins||0} icon="🏢" color="#0A84FF" delay={0}   sub={`Avg risk: ${stats?.avg_risk_score?.toFixed(1)||0}%`} />
              <StatCard label="Critical Alerts" value={stats?.critical_count||0} icon="🔴" color="#FF3B5C" delay={80}  sub="Immediate action required" />
              <StatCard label="High Risk" value={stats?.high_count||0} icon="🟠" color="#FF8C00" delay={160} sub="Review within 48 hours" />
              <StatCard label="Total Alerts" value={stats?.total_alerts||0} icon="⚡" color="#BF5AF2" delay={240} sub={`${stats?.alert_rate?.toFixed(1)||0}% of all GSTINs`} />
            </div>

            <div style={{ display:"grid", gridTemplateColumns:"1.5fr 1fr", gap:18, marginBottom:18 }}>

              {/* Top risks */}
              <div style={{ background:"rgba(255,255,255,0.025)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:22, overflow:"hidden" }}>
                <div style={{ padding:"18px 22px 14px", borderBottom:"1px solid rgba(255,255,255,0.06)", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <div>
                    <div style={{ fontSize:14, fontWeight:700 }}>🎯 Top Risk GSTINs</div>
                    <div style={{ fontSize:11, color:"#8E8E93", marginTop:2 }}>Click any row for full investigation report</div>
                  </div>
                  <button onClick={()=>setActiveTab("alerts")} style={{ fontSize:11, color:"#FF3B5C", background:"rgba(255,59,92,0.1)", border:"1px solid rgba(255,59,92,0.2)", borderRadius:8, padding:"4px 12px", cursor:"pointer", fontFamily:"inherit" }}>
                    View All {stats?.total_alerts} →
                  </button>
                </div>

                <div style={{ padding:"4px 0" }}>
                  {topRisks.slice(0,8).map((r,i)=>{
                    const color = riskColor(r.risk_level);
                    return (
                      <div key={r.gstin} className="row-hover" onClick={()=>setSelectedGstin(r.gstin)}
                        style={{ display:"grid", gridTemplateColumns:"28px 1fr 56px 90px", gap:12, padding:"11px 22px", alignItems:"center", borderBottom:"1px solid rgba(255,255,255,0.04)", animation:`slideUp 0.4s ease ${i*55}ms both` }}>
                        <div style={{ fontSize:11, color:"#8E8E93", fontFamily:"'DM Mono',monospace", textAlign:"center" }}>#{r.rank}</div>
                        <div>
                          <div style={{ fontSize:12, fontFamily:"'DM Mono',monospace", fontWeight:600, color:"#F5F5F7", letterSpacing:"0.01em" }}>{r.gstin}</div>
                          <div style={{ fontSize:11, color:"#8E8E93", marginTop:3, display:"flex", gap:8 }}>
                            <span>{fraudIcon(r.fraud_type)} {r.fraud_type?.replace(/_/g," ")}</span>
                            {r.in_circular_ring && <span style={{ color:"#FF8C00" }}>🔄 ring</span>}
                            {r.models_agreeing>=3 && <span style={{ color:"#BF5AF2" }}>•{r.models_agreeing} agree</span>}
                          </div>
                        </div>
                        <ScoreGauge score={r.ensemble_score} size={48} />
                        <div style={{ display:"flex", justifyContent:"flex-end" }}>
                          <span style={{ padding:"3px 10px", borderRadius:20, fontSize:10, fontWeight:700, background:riskBg(r.risk_level), color, border:`1px solid ${color}35`, letterSpacing:"0.04em" }}>
                            {r.risk_level}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Right panels */}
              <div style={{ display:"flex", flexDirection:"column", gap:14 }}>

                {/* Risk distribution */}
                <div style={{ background:"rgba(255,255,255,0.025)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:22, padding:"18px 22px" }}>
                  <div style={{ fontSize:14, fontWeight:700, marginBottom:2 }}>📊 Risk Distribution</div>
                  <div style={{ fontSize:11, color:"#8E8E93", marginBottom:18 }}>Across all {(stats?.total_gstins||5000).toLocaleString()} GSTINs</div>
                  {[
                    {level:"CRITICAL",count:stats?.critical_count||56,  color:"#FF3B5C"},
                    {level:"HIGH",    count:stats?.high_count||485,      color:"#FF8C00"},
                    {level:"MEDIUM",  count:stats?.medium_count||471,    color:"#FFD60A"},
                    {level:"LOW",     count:stats?.low_count||3988,      color:"#30D158"},
                  ].map(({level,count,color})=>(
                    <div key={level} style={{ marginBottom:13 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
                        <span style={{ fontSize:11, color, fontWeight:700, letterSpacing:"0.04em" }}>{level}</span>
                        <span style={{ fontSize:11, color:"#8E8E93", fontFamily:"'DM Mono',monospace" }}>{count.toLocaleString()} · {((count/(stats?.total_gstins||5000))*100).toFixed(1)}%</span>
                      </div>
                      <MiniBar value={count} max={stats?.total_gstins||5000} color={color} />
                    </div>
                  ))}
                </div>

                {/* Fraud patterns */}
                <div style={{ background:"rgba(255,255,255,0.025)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:22, padding:"18px 22px", flex:1 }}>
                  <div style={{ fontSize:14, fontWeight:700, marginBottom:2 }}>🎭 Fraud Patterns</div>
                  <div style={{ fontSize:11, color:"#8E8E93", marginBottom:18 }}>Detected fraud categories</div>
                  {Object.entries(fraudTypes).map(([type,count],i)=>{
                    const colors = ["#FF3B5C","#FF8C00","#BF5AF2","#0A84FF","#30D158"];
                    return (
                      <div key={type} style={{ display:"flex", alignItems:"center", gap:10, marginBottom:13 }}>
                        <span style={{ fontSize:16, flexShrink:0 }}>{fraudIcon(type)}</span>
                        <div style={{ flex:1, minWidth:0 }}>
                          <div style={{ fontSize:11, color:"#F5F5F7", marginBottom:4, textTransform:"capitalize", fontWeight:500 }}>{type.replace(/_/g," ")}</div>
                          <MiniBar value={count} max={maxFraud} color={colors[i%colors.length]} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Model performance */}
            <div style={{ background:"rgba(255,255,255,0.025)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:22, padding:"18px 22px" }}>
              <div style={{ fontSize:14, fontWeight:700, marginBottom:2 }}>🤖 Ensemble Model Performance</div>
              <div style={{ fontSize:11, color:"#8E8E93", marginBottom:20 }}>XGBoost + Isolation Forest + Graph Neural Network combined</div>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:14 }}>
                {[
                  {label:"Accuracy",  val:95.76, color:"#30D158", icon:"✅", desc:"Overall correct predictions"},
                  {label:"Precision", val:99.50, color:"#0A84FF", icon:"🎯", desc:"True fraud among flagged"},
                  {label:"Recall",    val:79.20, color:"#BF5AF2", icon:"🔍", desc:"Real fraud cases caught"},
                  {label:"AUC-ROC",   val:98.28, color:"#FF8C00", icon:"📈", desc:"Model discrimination power"},
                ].map(({label,val,color,icon,desc})=>(
                  <div key={label} style={{ background:"rgba(255,255,255,0.04)", borderRadius:16, padding:"18px", textAlign:"center", border:"1px solid rgba(255,255,255,0.06)" }}>
                    <div style={{ fontSize:22, marginBottom:8 }}>{icon}</div>
                    <div style={{ fontSize:28, fontWeight:900, color, fontFamily:"'DM Mono',monospace", lineHeight:1 }}>
                      <AnimatedNumber value={val} decimals={1} suffix="%" />
                    </div>
                    <div style={{ fontSize:12, fontWeight:600, color:"#F5F5F7", margin:"6px 0 4px" }}>{label}</div>
                    <div style={{ fontSize:10, color:"#8E8E93", lineHeight:1.4 }}>{desc}</div>
                    <div style={{ height:3, background:"rgba(255,255,255,0.06)", borderRadius:2, marginTop:12, overflow:"hidden" }}>
                      <div style={{ height:"100%", width:`${val}%`, background:color, borderRadius:2, boxShadow:`0 0 8px ${color}`, transition:"width 1.4s ease" }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ALERTS */}
        {activeTab==="alerts" && (
          <div className="tab-content">
            <div style={{ marginBottom:22, display:"flex", justifyContent:"space-between", alignItems:"flex-end" }}>
              <div>
                <h2 style={{ fontSize:22, fontWeight:800 }}>🚨 Fraud Alerts</h2>
                <p style={{ fontSize:13, color:"#8E8E93", marginTop:4 }}>GSTINs requiring immediate investigation • Click row for full report</p>
              </div>
              <div style={{ display:"flex", gap:8 }}>
                {[{l:"CRITICAL",c:stats?.critical_count},{l:"HIGH",c:stats?.high_count}].map(({l,c})=>(
                  <div key={l} style={{ padding:"5px 14px", borderRadius:20, fontSize:12, fontWeight:700, background:riskBg(l), color:riskColor(l), border:`1px solid ${riskColor(l)}35` }}>
                    {l}: {c}
                  </div>
                ))}
              </div>
            </div>

            {alertsLoading ? (
              <div style={{ textAlign:"center", padding:64, color:"#8E8E93" }}>
                <div style={{ fontSize:36, animation:"spin 0.8s linear infinite", display:"inline-block", marginBottom:14 }}>⟳</div>
                <div style={{ fontSize:14 }}>Loading alerts from API...</div>
              </div>
            ) : (
              <div style={{ background:"rgba(255,255,255,0.025)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:22, overflow:"hidden" }}>
                <div style={{ display:"grid", gridTemplateColumns:"1fr 110px 90px 90px 90px 90px", padding:"12px 22px", borderBottom:"1px solid rgba(255,255,255,0.07)", fontSize:10, color:"#8E8E93", fontWeight:700, letterSpacing:"0.07em" }}>
                  <span>GSTIN / FRAUD TYPE</span>
                  <span style={{textAlign:"center"}}>FINAL SCORE</span>
                  <span style={{textAlign:"center"}}>XGBOOST</span>
                  <span style={{textAlign:"center"}}>ANOMALY</span>
                  <span style={{textAlign:"center"}}>GRAPH</span>
                  <span style={{textAlign:"center"}}>RISK LEVEL</span>
                </div>
                {(alerts.length ? alerts : MOCK.topRisks).map((a,i)=>{
                  const color = riskColor(a.risk_level);
                  return (
                    <div key={a.gstin} className="row-hover" onClick={()=>setSelectedGstin(a.gstin)}
                      style={{ display:"grid", gridTemplateColumns:"1fr 110px 90px 90px 90px 90px", padding:"13px 22px", alignItems:"center", borderBottom:"1px solid rgba(255,255,255,0.04)", animation:`slideUp 0.3s ease ${i*35}ms both` }}>
                      <div>
                        <div style={{ fontSize:12, fontFamily:"'DM Mono',monospace", fontWeight:600, letterSpacing:"0.01em" }}>{a.gstin}</div>
                        <div style={{ fontSize:11, color:"#8E8E93", marginTop:3, display:"flex", gap:8, flexWrap:"wrap" }}>
                          <span>{fraudIcon(a.fraud_type)} {a.fraud_type?.replace(/_/g," ")}</span>
                          {a.in_circular_ring && <span style={{color:"#FF8C00"}}>🔄 circular ring</span>}
                          {a.models_agreeing>=3 && <span style={{color:"#BF5AF2"}}>• {a.models_agreeing} models agree</span>}
                        </div>
                      </div>
                      <div style={{ textAlign:"center", fontSize:16, fontWeight:800, color, fontFamily:"'DM Mono',monospace" }}>{a.ensemble_score?.toFixed(1)}%</div>
                      <div style={{ textAlign:"center", fontSize:12, color:"#0A84FF", fontFamily:"'DM Mono',monospace" }}>{a.xgb_score?.toFixed(0)}%</div>
                      <div style={{ textAlign:"center", fontSize:12, color:"#BF5AF2", fontFamily:"'DM Mono',monospace" }}>{a.anomaly_score?.toFixed(0)}%</div>
                      <div style={{ textAlign:"center", fontSize:12, color:"#FF9F0A", fontFamily:"'DM Mono',monospace" }}>{a.graph_risk_score?.toFixed(0)}%</div>
                      <div style={{ textAlign:"center" }}>
                        <span style={{ padding:"3px 10px", borderRadius:20, fontSize:10, fontWeight:700, background:riskBg(a.risk_level), color, border:`1px solid ${color}35`, letterSpacing:"0.04em" }}>
                          {a.risk_level}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* SEARCH */}
        {activeTab==="search" && (
          <div className="tab-content">
            <div style={{ maxWidth:620, margin:"0 auto" }}>
              <div style={{ textAlign:"center", marginBottom:36 }}>
                <div style={{ fontSize:52, marginBottom:16, animation:"float 3s ease-in-out infinite", display:"inline-block" }}>🔍</div>
                <h2 style={{ fontSize:26, fontWeight:800, letterSpacing:"-0.02em" }}>GSTIN Lookup</h2>
                <p style={{ fontSize:13, color:"#8E8E93", marginTop:6 }}>Search any GSTIN for instant AI-powered fraud analysis</p>
              </div>

              <div style={{ position:"relative", marginBottom:28 }}>
                <input className="search-input" value={search} onChange={e=>setSearch(e.target.value)}
                  placeholder="Enter GSTIN (e.g. 27VVZYP7446E1ZH)..."
                  style={{ width:"100%", padding:"18px 56px 18px 24px", fontSize:14, background:"rgba(255,255,255,0.05)", border:"1px solid rgba(255,255,255,0.12)", borderRadius:16, color:"#F5F5F7", fontFamily:"'DM Mono',monospace", transition:"all 0.2s", letterSpacing:"0.03em" }} />
                <div style={{ position:"absolute", right:16, top:"50%", transform:"translateY(-50%)", fontSize:16 }}>
                  {searching ? <span style={{ animation:"spin 0.8s linear infinite", display:"inline-block" }}>⟳</span> : "🔍"}
                </div>
              </div>

              {searchResults.length > 0 && (
                <div style={{ background:"rgba(255,255,255,0.025)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:20, overflow:"hidden" }}>
                  {searchResults.map((r,i)=>{
                    const color = riskColor(r.risk_level);
                    return (
                      <div key={r.gstin} className="row-hover" onClick={()=>setSelectedGstin(r.gstin)}
                        style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"16px 22px", borderBottom:"1px solid rgba(255,255,255,0.05)", animation:`slideUp 0.3s ease ${i*50}ms both` }}>
                        <div>
                          <div style={{ fontSize:14, fontFamily:"'DM Mono',monospace", fontWeight:600 }}>{r.gstin}</div>
                          <div style={{ fontSize:11, color:"#8E8E93", marginTop:4 }}>{fraudIcon(r.fraud_type)} {r.fraud_type?.replace(/_/g," ")}</div>
                        </div>
                        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                          <span style={{ fontSize:20, fontWeight:800, color, fontFamily:"'DM Mono',monospace" }}>{r.ensemble_score?.toFixed(1)}%</span>
                          <span style={{ padding:"4px 12px", borderRadius:20, fontSize:11, fontWeight:700, background:riskBg(r.risk_level), color, border:`1px solid ${color}35` }}>{r.risk_level}</span>
                          <span style={{ color:"#8E8E93" }}>→</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {search.length >= 3 && searchResults.length === 0 && !searching && (
                <div style={{ textAlign:"center", padding:48, color:"#8E8E93" }}>
                  <div style={{ fontSize:42, marginBottom:12 }}>🔎</div>
                  <div style={{ fontSize:14 }}>No GSTINs found for "{search}"</div>
                  <div style={{ fontSize:12, marginTop:6 }}>Try a partial GSTIN like "27VVZ" or "12XUU"</div>
                </div>
              )}

              {!search && (
                <div style={{ textAlign:"center", paddingTop:16 }}>
                  <div style={{ fontSize:12, color:"#8E8E93", marginBottom:16 }}>Try these high-risk GSTINs:</div>
                  <div style={{ display:"flex", gap:8, justifyContent:"center", flexWrap:"wrap" }}>
                    {["27VVZYP","12XUUHW","17WTALS","09ZKRQH"].map(hint=>(
                      <button key={hint} className="hint-btn" onClick={()=>setSearch(hint)}
                        style={{ padding:"8px 16px", borderRadius:20, fontSize:12, background:"rgba(255,255,255,0.05)", border:"1px solid rgba(255,255,255,0.1)", color:"#8E8E93", cursor:"pointer", fontFamily:"'DM Mono',monospace", transition:"all 0.2s" }}>
                        {hint}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {selectedGstin && <GSTINModal gstin={selectedGstin} onClose={()=>setSelectedGstin(null)} />}
    </div>
  );
}
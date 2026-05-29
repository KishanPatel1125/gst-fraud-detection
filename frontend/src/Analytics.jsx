// Analytics.jsx
// Advanced Analytics Dashboard
// Month-over-month trends, industry analysis, state rankings

import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, Legend,
  PieChart, Pie, Cell, AreaChart, Area,
} from "recharts";

const API = "https://gst-fraud-detection-production.up.railway.app";

const CHART_COLORS = [
  "#FF3B5C","#FF8C00","#BF5AF2","#0A84FF",
  "#30D158","#FFD60A","#FF6B00","#00C7BE",
  "#5E5CE6","#AC8E68",
];

function ChartTooltip({ active, payload, label, isDark }) {
  if (!active || !payload?.length) return null;
  const bg  = isDark ? "#1C1C1E" : "#fff";
  const brd = isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.12)";
  const txt = isDark ? "#F5F5F7" : "#111";
  const mut = isDark ? "#8E8E93" : "#666";
  return (
    <div style={{ background:bg, border:`1px solid ${brd}`, borderRadius:10, padding:"10px 14px", boxShadow:"0 8px 24px rgba(0,0,0,0.15)" }}>
      <div style={{ fontSize:12, color:mut, marginBottom:6 }}>{label}</div>
      {payload.map((p,i) => (
        <div key={i} style={{ fontSize:13, fontWeight:700, color:p.color||txt, fontFamily:"'DM Mono',monospace" }}>
          {p.name}: {typeof p.value === "number" ? p.value.toLocaleString() : p.value}
        </div>
      ))}
    </div>
  );
}

export default function Analytics({ token, isDark = true }) {
  const [trends,     setTrends]     = useState([]);
  const [industries, setIndustries] = useState([]);
  const [states,     setStates]     = useState([]);
  const [summary,    setSummary]    = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [activeView, setActiveView] = useState("overview");

  const txt    = isDark ? "#F5F5F7" : "#111";
  const muted  = isDark ? "#8E8E93" : "#666";
  const cardBg = isDark ? "rgba(255,255,255,0.025)" : "rgba(255,255,255,0.9)";
  const cardBd = isDark ? "rgba(255,255,255,0.07)"  : "rgba(0,0,0,0.08)";
  const surfBg = isDark ? "rgba(255,255,255,0.04)"  : "rgba(0,0,0,0.04)";
  const gridC  = isDark ? "rgba(255,255,255,0.05)"  : "rgba(0,0,0,0.06)";

  const authHeaders = token ? { Authorization:`Bearer ${token}` } : {};
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`${API}/api/analytics/trends`,    { headers:authHeaders }).then(r=>r.json()),
      fetch(`${API}/api/analytics/industries`,{ headers:authHeaders }).then(r=>r.json()),
      fetch(`${API}/api/analytics/states`,    { headers:authHeaders }).then(r=>r.json()),
      fetch(`${API}/api/analytics/summary`,   { headers:authHeaders }).then(r=>r.json()),
    ]).then(([t,i,s,sum]) => {
      setTrends(t.trends       || []);
      setIndustries(i.industries || []);
      setStates(s.states       || []);
      setSummary(sum);
    }).catch(() => {
      // Mock data fallback
      setTrends(generateMockTrends());
      setIndustries(generateMockIndustries());
      setStates(generateMockStates());
      setSummary(generateMockSummary());
    }).finally(() => setLoading(false));
  }, []);

  function generateMockTrends() {
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return months.map((m,i) => ({
      month:    `${m} 2025`,
      critical: 45 + Math.round(Math.random()*20),
      high:     420 + Math.round(Math.random()*80),
      total:    480 + Math.round(Math.random()*100),
      amount:   80  + Math.round(Math.random()*60),
    }));
  }

  function generateMockIndustries() {
    return [
      {industry:"Trading",     total:1200,fraud:180,rate:15.0,amount:45.2},
      {industry:"Manufacturing",total:850,fraud:102,rate:12.0,amount:32.1},
      {industry:"Services",    total:980,fraud:88, rate:9.0, amount:28.5},
      {industry:"Construction",total:420,fraud:63, rate:15.0,amount:19.8},
      {industry:"Real Estate", total:310,fraud:56, rate:18.1,amount:22.4},
      {industry:"Hospitality", total:280,fraud:34, rate:12.1,amount:11.2},
      {industry:"Technology",  total:360,fraud:29, rate:8.1, amount:9.8},
      {industry:"Healthcare",  total:240,fraud:18, rate:7.5, amount:7.2},
    ];
  }

  function generateMockStates() {
    return [
      {state:"Delhi",         code:"07",total:280,fraud:89,rate:31.8,amount:42.1},
      {state:"Maharashtra",   code:"27",total:620,fraud:165,rate:26.6,amount:78.4},
      {state:"Karnataka",     code:"29",total:310,fraud:72,rate:23.2,amount:34.2},
      {state:"Gujarat",       code:"24",total:390,fraud:82,rate:21.0,amount:38.9},
      {state:"Tamil Nadu",    code:"33",total:350,fraud:68,rate:19.4,amount:32.3},
      {state:"Telangana",     code:"36",total:220,fraud:38,rate:17.3,amount:18.1},
      {state:"Uttar Pradesh", code:"09",total:480,fraud:76,rate:15.8,amount:36.2},
      {state:"West Bengal",   code:"19",total:290,fraud:43,rate:14.8,amount:20.4},
    ];
  }

  function generateMockSummary() {
    return {
      total_gstins:         5000,
      total_fraud_cases:    541,
      estimated_evasion:    "₹1,247.3Cr",
      avg_fraud_score:      18.4,
      highest_risk_state:   "Delhi (31.8%)",
      highest_risk_industry:"Real Estate (18.1%)",
      yoy_change:           "+12.4%",
      models_accuracy:      "95.76%",
    };
  }

  if (loading) return (
    <div style={{ textAlign:"center", padding:60, color:muted }}>
      <div style={{ fontSize:36, animation:"spin 0.8s linear infinite", display:"inline-block", marginBottom:12 }}>⟳</div>
      <div>Loading analytics...</div>
    </div>
  );

  return (
    <div style={{ fontFamily:"'Sora',sans-serif" }}>

      {/* Header */}
      <div style={{ marginBottom:24, display:"flex", justifyContent:"space-between", alignItems:"flex-end", flexWrap:"wrap", gap:8 }}>
        <div>
          <h2 style={{ fontSize:22, fontWeight:800, color:txt }}>📊 Advanced Analytics</h2>
          <p style={{ fontSize:13, color:muted, marginTop:4 }}>Deep insights into GST fraud patterns and trends</p>
        </div>
        <div style={{ fontSize:11, color:muted, fontFamily:"'DM Mono',monospace" }}>
          {new Date().toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}
        </div>
      </div>

      {/* View tabs */}
      <div style={{ display:"flex", gap:8, marginBottom:20, flexWrap:"wrap" }}>
        {[
          ["overview","📈 Overview"],
          ["trends",  "📅 Trends"],
          ["industry","🏭 Industry"],
          ["states",  "🗺️ States"],
        ].map(([id,label]) => (
          <button key={id} onClick={() => setActiveView(id)} style={{
            padding:"8px 16px", borderRadius:10, border:`1px solid ${cardBd}`,
            background: activeView===id ? "rgba(255,59,92,0.12)" : surfBg,
            color: activeView===id ? "#FF3B5C" : muted,
            fontSize:13, fontWeight:500, cursor:"pointer",
            fontFamily:"inherit", transition:"all 0.2s",
          }}>{label}</button>
        ))}
      </div>

      {/* ── OVERVIEW ── */}
      {activeView==="overview" && summary && (
        <div>
          {/* KPI cards */}
          <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12, marginBottom:20 }}>
            {[
              { label:"Total GSTINs",          value:summary.total_gstins?.toLocaleString(),  color:"#0A84FF", icon:"🏢" },
              { label:"Fraud Cases",            value:summary.total_fraud_cases?.toLocaleString(), color:"#FF3B5C", icon:"🚨" },
              { label:"Estimated Tax Evasion",  value:summary.estimated_evasion,               color:"#FF8C00", icon:"💰" },
              { label:"YoY Change",             value:summary.yoy_change,                      color:"#FF3B5C", icon:"📈" },
            ].map(({ label, value, color, icon }) => (
              <div key={label} style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, padding:"18px 20px", position:"relative", overflow:"hidden" }}>
                <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:`linear-gradient(90deg,transparent,${color},transparent)` }}/>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
                  <div>
                    <div style={{ fontSize:11, color:muted, marginBottom:6 }}>{label}</div>
                    <div style={{ fontSize:22, fontWeight:800, color, fontFamily:"'DM Mono',monospace", lineHeight:1 }}>{value}</div>
                  </div>
                  <div style={{ fontSize:24 }}>{icon}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Quick insights */}
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:16 }}>
            {/* Fraud trend area chart */}
            <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, padding:"18px 20px" }}>
              <div style={{ fontSize:14, fontWeight:700, color:txt, marginBottom:4 }}>📈 Fraud Cases Trend</div>
              <div style={{ fontSize:11, color:muted, marginBottom:16 }}>Last 12 months</div>
              <ResponsiveContainer width="100%" height={180}>
                <AreaChart data={trends} margin={{top:0,right:0,left:-30,bottom:0}}>
                  <defs>
                    <linearGradient id="criticalGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#FF3B5C" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#FF3B5C" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="highGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#FF8C00" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#FF8C00" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridC}/>
                  <XAxis dataKey="month" tick={{fill:muted,fontSize:9}} axisLine={false} tickLine={false} interval={2}/>
                  <YAxis tick={{fill:muted,fontSize:9}} axisLine={false} tickLine={false}/>
                  <Tooltip content={<ChartTooltip isDark={isDark}/>}/>
                  <Area type="monotone" dataKey="critical" stroke="#FF3B5C" fill="url(#criticalGrad)" strokeWidth={2} name="Critical"/>
                  <Area type="monotone" dataKey="high"     stroke="#FF8C00" fill="url(#highGrad)"     strokeWidth={2} name="High"/>
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Tax evasion amount trend */}
            <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, padding:"18px 20px" }}>
              <div style={{ fontSize:14, fontWeight:700, color:txt, marginBottom:4 }}>💰 Estimated Evasion (₹Cr)</div>
              <div style={{ fontSize:11, color:muted, marginBottom:16 }}>Monthly tax evasion estimate</div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={trends} margin={{top:0,right:0,left:-30,bottom:0}}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridC}/>
                  <XAxis dataKey="month" tick={{fill:muted,fontSize:9}} axisLine={false} tickLine={false} interval={2}/>
                  <YAxis tick={{fill:muted,fontSize:9}} axisLine={false} tickLine={false}/>
                  <Tooltip content={<ChartTooltip isDark={isDark}/>} formatter={v=>`₹${v}Cr`}/>
                  <Bar dataKey="amount" fill="#FF3B5C" radius={[4,4,0,0]} name="Evasion (₹Cr)"/>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Key insights */}
          <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, padding:"18px 20px" }}>
            <div style={{ fontSize:14, fontWeight:700, color:txt, marginBottom:16 }}>💡 Key Insights</div>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:12 }}>
              {[
                { icon:"🏆", title:"Highest Risk State",    value:summary.highest_risk_state,    color:"#FF3B5C" },
                { icon:"🏭", title:"Highest Risk Industry", value:summary.highest_risk_industry,  color:"#FF8C00" },
                { icon:"🤖", title:"Model Accuracy",        value:summary.models_accuracy,        color:"#30D158" },
                { icon:"📊", title:"Avg Risk Score",        value:`${summary.avg_fraud_score}%`,  color:"#0A84FF" },
              ].map(({ icon, title, value, color }) => (
                <div key={title} style={{ background:surfBg, borderRadius:14, padding:"14px 16px", display:"flex", alignItems:"center", gap:12 }}>
                  <div style={{ fontSize:28 }}>{icon}</div>
                  <div>
                    <div style={{ fontSize:11, color:muted, marginBottom:4 }}>{title}</div>
                    <div style={{ fontSize:14, fontWeight:700, color }}>{value}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── TRENDS ── */}
      {activeView==="trends" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

          {/* Monthly fraud count line chart */}
          <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, padding:"18px 20px" }}>
            <div style={{ fontSize:14, fontWeight:700, color:txt, marginBottom:4 }}>📅 Monthly Fraud Detection Trend</div>
            <div style={{ fontSize:11, color:muted, marginBottom:16 }}>Critical vs High risk cases over 12 months</div>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trends} margin={{top:0,right:0,left:-20,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridC}/>
                <XAxis dataKey="month" tick={{fill:muted,fontSize:10}} axisLine={false} tickLine={false}/>
                <YAxis tick={{fill:muted,fontSize:10}} axisLine={false} tickLine={false}/>
                <Tooltip content={<ChartTooltip isDark={isDark}/>}/>
                <Legend iconType="circle" iconSize={8} wrapperStyle={{fontSize:11,color:muted}}/>
                <Line type="monotone" dataKey="critical" stroke="#FF3B5C" strokeWidth={2.5} dot={{fill:"#FF3B5C",r:3}} name="Critical"/>
                <Line type="monotone" dataKey="high"     stroke="#FF8C00" strokeWidth={2.5} dot={{fill:"#FF8C00",r:3}} name="High"/>
                <Line type="monotone" dataKey="total"    stroke="#0A84FF" strokeWidth={2}   dot={false}               name="Total" strokeDasharray="5 5"/>
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Monthly evasion bar chart */}
          <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, padding:"18px 20px" }}>
            <div style={{ fontSize:14, fontWeight:700, color:txt, marginBottom:4 }}>💰 Monthly Tax Evasion Estimate (₹ Crore)</div>
            <div style={{ fontSize:11, color:muted, marginBottom:16 }}>Estimated revenue loss from detected fraud</div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={trends} margin={{top:0,right:0,left:-20,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridC}/>
                <XAxis dataKey="month" tick={{fill:muted,fontSize:10}} axisLine={false} tickLine={false}/>
                <YAxis tick={{fill:muted,fontSize:10}} axisLine={false} tickLine={false}/>
                <Tooltip content={<ChartTooltip isDark={isDark}/>} formatter={v=>`₹${v}Cr`}/>
                <Bar dataKey="amount" radius={[6,6,0,0]} name="Evasion (₹Cr)">
                  {trends.map((_,i) => (
                    <Cell key={i} fill={CHART_COLORS[i%CHART_COLORS.length]}/>
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Trend table */}
          <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, overflow:"hidden" }}>
            <div style={{ padding:"16px 20px", borderBottom:`1px solid ${cardBd}`, fontSize:14, fontWeight:700, color:txt }}>
              📋 Monthly Breakdown Table
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 100px 100px 100px 120px", padding:"11px 20px", borderBottom:`1px solid ${cardBd}`, fontSize:10, color:muted, fontWeight:700, letterSpacing:"0.06em" }}>
              <span>MONTH</span>
              <span style={{textAlign:"center"}}>CRITICAL</span>
              <span style={{textAlign:"center"}}>HIGH</span>
              <span style={{textAlign:"center"}}>TOTAL</span>
              <span style={{textAlign:"center"}}>EVASION</span>
            </div>
            {trends.map((t,i) => (
              <div key={i} style={{ display:"grid", gridTemplateColumns:"1fr 100px 100px 100px 120px", padding:"11px 20px", alignItems:"center", borderBottom:`1px solid ${isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.05)"}` }}>
                <span style={{ fontSize:13, color:txt, fontWeight:500 }}>{t.month}</span>
                <span style={{ textAlign:"center", fontSize:13, fontWeight:700, color:"#FF3B5C", fontFamily:"'DM Mono',monospace" }}>{t.critical}</span>
                <span style={{ textAlign:"center", fontSize:13, fontWeight:700, color:"#FF8C00", fontFamily:"'DM Mono',monospace" }}>{t.high}</span>
                <span style={{ textAlign:"center", fontSize:13, color:txt,     fontFamily:"'DM Mono',monospace" }}>{t.total}</span>
                <span style={{ textAlign:"center", fontSize:13, fontWeight:700, color:"#30D158", fontFamily:"'DM Mono',monospace" }}>₹{t.amount}Cr</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── INDUSTRY ── */}
      {activeView==="industry" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

          {/* Industry bar chart */}
          <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, padding:"18px 20px" }}>
            <div style={{ fontSize:14, fontWeight:700, color:txt, marginBottom:4 }}>🏭 Fraud Rate by Industry</div>
            <div style={{ fontSize:11, color:muted, marginBottom:16 }}>% of GSTINs flagged as fraudulent</div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={industries} layout="vertical" margin={{top:0,right:20,left:20,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridC} horizontal={false}/>
                <XAxis type="number" tick={{fill:muted,fontSize:10}} axisLine={false} tickLine={false} tickFormatter={v=>`${v}%`}/>
                <YAxis type="category" dataKey="industry" tick={{fill:txt,fontSize:11}} axisLine={false} tickLine={false} width={90}/>
                <Tooltip content={<ChartTooltip isDark={isDark}/>} formatter={v=>`${v}%`}/>
                <Bar dataKey="rate" radius={[0,6,6,0]} name="Fraud Rate %">
                  {industries.map((_,i) => (
                    <Cell key={i} fill={_.rate>=15?"#FF3B5C":_.rate>=10?"#FF8C00":"#FFD60A"}/>
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Industry comparison */}
          <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, padding:"18px 20px" }}>
            <div style={{ fontSize:14, fontWeight:700, color:txt, marginBottom:4 }}>💰 Tax Evasion by Industry (₹Cr)</div>
            <div style={{ fontSize:11, color:muted, marginBottom:16 }}>Estimated revenue loss per sector</div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={industries} margin={{top:0,right:0,left:-20,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridC}/>
                <XAxis dataKey="industry" tick={{fill:muted,fontSize:9}} axisLine={false} tickLine={false}/>
                <YAxis tick={{fill:muted,fontSize:10}} axisLine={false} tickLine={false}/>
                <Tooltip content={<ChartTooltip isDark={isDark}/>} formatter={v=>`₹${v}Cr`}/>
                <Bar dataKey="amount" radius={[6,6,0,0]} name="Evasion (₹Cr)">
                  {industries.map((_,i) => <Cell key={i} fill={CHART_COLORS[i%CHART_COLORS.length]}/>)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Industry table */}
          <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, overflow:"hidden" }}>
            <div style={{ padding:"16px 20px", borderBottom:`1px solid ${cardBd}`, fontSize:14, fontWeight:700, color:txt }}>
              📋 Industry Detail Table
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 100px 100px 100px 120px", padding:"11px 20px", borderBottom:`1px solid ${cardBd}`, fontSize:10, color:muted, fontWeight:700, letterSpacing:"0.06em" }}>
              <span>INDUSTRY</span>
              <span style={{textAlign:"center"}}>TOTAL</span>
              <span style={{textAlign:"center"}}>FRAUD</span>
              <span style={{textAlign:"center"}}>RATE</span>
              <span style={{textAlign:"center"}}>EVASION</span>
            </div>
            {industries.sort((a,b)=>b.rate-a.rate).map((ind,i) => (
              <div key={i} style={{ display:"grid", gridTemplateColumns:"1fr 100px 100px 100px 120px", padding:"12px 20px", alignItems:"center", borderBottom:`1px solid ${isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.05)"}` }}>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <div style={{ width:8, height:8, borderRadius:"50%", background:ind.rate>=15?"#FF3B5C":ind.rate>=10?"#FF8C00":"#FFD60A", flexShrink:0 }}/>
                  <span style={{ fontSize:13, color:txt, fontWeight:500 }}>{ind.industry}</span>
                </div>
                <span style={{ textAlign:"center", fontSize:12, color:muted, fontFamily:"'DM Mono',monospace" }}>{ind.total}</span>
                <span style={{ textAlign:"center", fontSize:12, color:"#FF3B5C", fontFamily:"'DM Mono',monospace", fontWeight:600 }}>{ind.fraud}</span>
                <span style={{ textAlign:"center", fontSize:13, fontWeight:800, color:ind.rate>=15?"#FF3B5C":ind.rate>=10?"#FF8C00":"#FFD60A", fontFamily:"'DM Mono',monospace" }}>{ind.rate}%</span>
                <span style={{ textAlign:"center", fontSize:12, color:"#30D158", fontFamily:"'DM Mono',monospace", fontWeight:600 }}>₹{ind.amount}Cr</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── STATES ── */}
      {activeView==="states" && (
        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

          {/* States bar chart */}
          <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, padding:"18px 20px" }}>
            <div style={{ fontSize:14, fontWeight:700, color:txt, marginBottom:4 }}>🗺️ Fraud Rate by State</div>
            <div style={{ fontSize:11, color:muted, marginBottom:16 }}>Top 8 states by fraud percentage</div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={states} margin={{top:0,right:0,left:-20,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridC}/>
                <XAxis dataKey="state" tick={{fill:muted,fontSize:9}} axisLine={false} tickLine={false}/>
                <YAxis tick={{fill:muted,fontSize:10}} axisLine={false} tickLine={false} tickFormatter={v=>`${v}%`}/>
                <Tooltip content={<ChartTooltip isDark={isDark}/>} formatter={v=>`${v}%`}/>
                <Bar dataKey="rate" radius={[6,6,0,0]} name="Fraud Rate %">
                  {states.map((_,i) => (
                    <Cell key={i} fill={_.rate>=25?"#FF3B5C":_.rate>=20?"#FF8C00":_.rate>=15?"#FFD60A":"#30D158"}/>
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* States evasion */}
          <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, padding:"18px 20px" }}>
            <div style={{ fontSize:14, fontWeight:700, color:txt, marginBottom:4 }}>💰 Tax Evasion by State (₹Cr)</div>
            <div style={{ fontSize:11, color:muted, marginBottom:16 }}>Estimated revenue loss per state</div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={states} margin={{top:0,right:0,left:-20,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridC}/>
                <XAxis dataKey="state" tick={{fill:muted,fontSize:9}} axisLine={false} tickLine={false}/>
                <YAxis tick={{fill:muted,fontSize:10}} axisLine={false} tickLine={false}/>
                <Tooltip content={<ChartTooltip isDark={isDark}/>} formatter={v=>`₹${v}Cr`}/>
                <Bar dataKey="amount" radius={[6,6,0,0]} name="Evasion (₹Cr)">
                  {states.map((_,i) => <Cell key={i} fill={CHART_COLORS[i%CHART_COLORS.length]}/>)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* States table */}
          <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, overflow:"hidden" }}>
            <div style={{ padding:"16px 20px", borderBottom:`1px solid ${cardBd}`, fontSize:14, fontWeight:700, color:txt }}>
              📋 State Detail Table
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"40px 1fr 80px 100px 100px 120px", padding:"11px 20px", borderBottom:`1px solid ${cardBd}`, fontSize:10, color:muted, fontWeight:700, letterSpacing:"0.06em" }}>
              <span>#</span>
              <span>STATE</span>
              <span style={{textAlign:"center"}}>CODE</span>
              <span style={{textAlign:"center"}}>FRAUD</span>
              <span style={{textAlign:"center"}}>RATE</span>
              <span style={{textAlign:"center"}}>EVASION</span>
            </div>
            {states.sort((a,b)=>b.rate-a.rate).map((s,i) => (
              <div key={i} style={{ display:"grid", gridTemplateColumns:"40px 1fr 80px 100px 100px 120px", padding:"12px 20px", alignItems:"center", borderBottom:`1px solid ${isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.05)"}` }}>
                <div style={{ width:24, height:24, borderRadius:"50%", background:i<3?"linear-gradient(135deg,#FF3B5C,#FF6B00)":"rgba(255,255,255,0.1)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:11, fontWeight:700, color:"white" }}>
                  {i+1}
                </div>
                <span style={{ fontSize:13, color:txt, fontWeight:500 }}>{s.state}</span>
                <span style={{ textAlign:"center", fontSize:11, color:muted, fontFamily:"'DM Mono',monospace" }}>{s.code}</span>
                <span style={{ textAlign:"center", fontSize:12, color:"#FF3B5C", fontFamily:"'DM Mono',monospace", fontWeight:600 }}>{s.fraud}</span>
                <span style={{ textAlign:"center", fontSize:13, fontWeight:800, color:s.rate>=25?"#FF3B5C":s.rate>=20?"#FF8C00":"#FFD60A", fontFamily:"'DM Mono',monospace" }}>{s.rate}%</span>
                <span style={{ textAlign:"center", fontSize:12, color:"#30D158", fontFamily:"'DM Mono',monospace", fontWeight:600 }}>₹{s.amount}Cr</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
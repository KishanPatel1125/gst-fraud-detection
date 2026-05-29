import { useState, useEffect, useRef, useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
  CartesianGrid, Legend, RadialBarChart, RadialBar,
  LineChart, Line, AreaChart, Area
} from "recharts";
import BulkUpload from "./BulkUpload";
import IndiaHeatmap from "./IndiaHeatmap";
import UserManagement from "./UserManagement";
import Analytics from "./Analytics";

const API = "https://gst-fraud-detection-production.up.railway.app";

const MOCK = {
  stats: {
    total_gstins:5000,critical_count:56,high_count:485,medium_count:471,low_count:3988,
    total_alerts:541,alert_rate:10.82,avg_risk_score:18.4,
    fraud_type_breakdown:{fake_itc:316,circular_trading:212,shell_company:213,missing_returns:164,sudden_spike:95},
  },
  topRisks:[
    {rank:1,gstin:"27VVZYP7446E1ZH",ensemble_score:97.0,risk_level:"CRITICAL",fraud_type:"shell_company",xgb_score:99.5,anomaly_score:70.4,graph_risk_score:89.7,in_circular_ring:true,models_agreeing:4},
    {rank:2,gstin:"17WTALS7186N2ZN",ensemble_score:95.7,risk_level:"CRITICAL",fraud_type:"sudden_spike",xgb_score:98.8,anomaly_score:100,graph_risk_score:82.3,in_circular_ring:false,models_agreeing:4},
    {rank:3,gstin:"12XUUHW6959P3Z3",ensemble_score:95.4,risk_level:"CRITICAL",fraud_type:"fake_itc",xgb_score:99.9,anomaly_score:67.2,graph_risk_score:85.9,in_circular_ring:true,models_agreeing:4},
    {rank:4,gstin:"09ZKRQH3507F9ZW",ensemble_score:94.7,risk_level:"CRITICAL",fraud_type:"missing_returns",xgb_score:98.7,anomaly_score:76.8,graph_risk_score:75.7,in_circular_ring:true,models_agreeing:3},
    {rank:5,gstin:"20JRFBA7800W2ZY",ensemble_score:93.6,risk_level:"CRITICAL",fraud_type:"sudden_spike",xgb_score:98.4,anomaly_score:61.8,graph_risk_score:82.8,in_circular_ring:false,models_agreeing:3},
    {rank:6,gstin:"32ZAVWR7364E2Z9",ensemble_score:93.3,risk_level:"CRITICAL",fraud_type:"shell_company",xgb_score:98.1,anomaly_score:76.2,graph_risk_score:75.8,in_circular_ring:true,models_agreeing:3},
    {rank:7,gstin:"33CFEQA4862C2ZP",ensemble_score:92.5,risk_level:"CRITICAL",fraud_type:"shell_company",xgb_score:99.6,anomaly_score:66.1,graph_risk_score:75.8,in_circular_ring:false,models_agreeing:3},
    {rank:8,gstin:"36FCOMK2625P8Z2",ensemble_score:91.4,risk_level:"CRITICAL",fraud_type:"fake_itc",xgb_score:99.8,anomaly_score:71.2,graph_risk_score:66.0,in_circular_ring:false,models_agreeing:3},
    {rank:9,gstin:"08RZTZL1694W5ZG",ensemble_score:89.3,risk_level:"HIGH",fraud_type:"fake_itc",xgb_score:99.9,anomaly_score:74.6,graph_risk_score:83.1,in_circular_ring:false,models_agreeing:3},
    {rank:10,gstin:"05BDITF0160Z2ZT",ensemble_score:87.7,risk_level:"HIGH",fraud_type:"shell_company",xgb_score:98.9,anomaly_score:83.6,graph_risk_score:52.6,in_circular_ring:false,models_agreeing:3},
  ]
};

/* ─── theme-aware colour helpers ─────────────────────────────────────── */
const riskColor  = (l,isDark=true) => ({
  CRITICAL: isDark?"#FF3B5C":"#D0003A",
  HIGH:     isDark?"#FF8C00":"#C46A00",
  MEDIUM:   isDark?"#FFD60A":"#B09500",
  LOW:      isDark?"#30D158":"#1A8A35"
}[l]||"#8E8E93");

const riskBg = (l,isDark=true) => ({
  CRITICAL: isDark?"rgba(255,59,92,0.12)" :"rgba(208,0,58,0.08)",
  HIGH:     isDark?"rgba(255,140,0,0.12)" :"rgba(196,106,0,0.08)",
  MEDIUM:   isDark?"rgba(255,214,10,0.12)":"rgba(176,149,0,0.08)",
  LOW:      isDark?"rgba(48,209,88,0.12)" :"rgba(26,138,53,0.08)"
}[l]||"rgba(142,142,147,0.12)");

const fraudIcon = t => ({fake_itc:"⚡",circular_trading:"🔄",shell_company:"👻",missing_returns:"📭",sudden_spike:"📈"}[t]||"⚠️");
const roleIcon  = r => ({admin:"👑",officer:"🏛️",ca:"📊"}[r]||"👤");
const CHART_COLORS = ["#FF3B5C","#FF8C00","#BF5AF2","#0A84FF","#30D158","#FFD60A"];

/* ─── Ripple helper ───────────────────────────────────────────────────── */
function useRipple(){
  const ref=useRef(null);
  const trigger=(e)=>{
    const el=ref.current; if(!el)return;
    const r=el.getBoundingClientRect();
    const rip=document.createElement("span");
    const size=Math.max(el.offsetWidth,el.offsetHeight)*2;
    rip.style.cssText=`position:absolute;border-radius:50%;width:${size}px;height:${size}px;
      top:${e.clientY-r.top-size/2}px;left:${e.clientX-r.left-size/2}px;
      background:rgba(255,59,92,0.18);transform:scale(0);pointer-events:none;
      animation:ripple 0.55s ease-out forwards;`;
    el.style.position="relative"; el.style.overflow="hidden";
    el.appendChild(rip);
    setTimeout(()=>rip.remove(),600);
  };
  return [ref,trigger];
}

/* ─── Animated number ────────────────────────────────────────────────── */
function AnimatedNumber({value,suffix="",decimals=0}){
  const[display,setDisplay]=useState(0);
  const ref=useRef(null);
  useEffect(()=>{
    let start=0,end=parseFloat(value),step=16;
    const inc=end/(1400/step);
    clearInterval(ref.current);
    ref.current=setInterval(()=>{
      start+=inc;
      if(start>=end){setDisplay(end);clearInterval(ref.current);}
      else setDisplay(start);
    },step);
    return()=>clearInterval(ref.current);
  },[value]);
  return<span>{display.toFixed(decimals)}{suffix}</span>;
}

/* ─── Stat card (enhanced with hover lift + shimmer) ─────────────────── */
function StatCard({label,value,sub,color,icon,delay=0,isDark}){
  const[vis,setVis]=useState(false);
  const[hov,setHov]=useState(false);
  useEffect(()=>{const t=setTimeout(()=>setVis(true),delay);return()=>clearTimeout(t);},[delay]);
  const bg = isDark?"rgba(255,255,255,0.025)":"rgba(0,0,0,0.03)";
  const border = isDark?"rgba(255,255,255,0.07)":"rgba(0,0,0,0.08)";
  return(
    <div
      onMouseEnter={()=>setHov(true)}
      onMouseLeave={()=>setHov(false)}
      style={{
        background:hov?(isDark?"rgba(255,255,255,0.045)":"rgba(0,0,0,0.06)"):bg,
        border:`1px solid ${hov?color+"55":border}`,
        borderRadius:20,padding:"18px 20px",position:"relative",overflow:"hidden",
        opacity:vis?1:0,
        transform:vis?(hov?"translateY(-4px) scale(1.01)":"translateY(0)"):"translateY(24px)",
        transition:"opacity 0.5s ease,transform 0.4s cubic-bezier(0.34,1.56,0.64,1),border-color 0.3s,background 0.3s",
        cursor:"default",
        boxShadow:hov?`0 12px 32px ${color}22`:"none"
      }}>
      {/* top shimmer bar */}
      <div style={{position:"absolute",top:0,left:0,right:0,height:2,background:`linear-gradient(90deg,transparent,${color},transparent)`,opacity:hov?1:0.5,transition:"opacity 0.3s"}}/>
      {/* glow blob */}
      <div style={{position:"absolute",top:-30,right:-30,width:80,height:80,borderRadius:"50%",background:color,opacity:hov?0.12:0.06,filter:"blur(20px)",transition:"opacity 0.3s"}}/>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
        <div>
          <div style={{fontSize:11,color:isDark?"#8E8E93":"#666",marginBottom:6,letterSpacing:"0.03em"}}>{label}</div>
          <div style={{fontSize:28,fontWeight:800,color:isDark?"#F5F5F7":"#111",fontFamily:"'DM Mono',monospace",lineHeight:1}}>
            <AnimatedNumber value={value}/>
          </div>
          {sub&&<div style={{fontSize:11,color,marginTop:5,fontWeight:500}}>{sub}</div>}
        </div>
        <div style={{fontSize:26,transform:hov?"scale(1.15) rotate(-5deg)":"scale(1)",transition:"transform 0.3s cubic-bezier(0.34,1.56,0.64,1)"}}>{icon}</div>
      </div>
    </div>
  );
}

/* ─── Score gauge ────────────────────────────────────────────────────── */
function ScoreGauge({score,size=52,isDark=true}){
  const r=(size-10)/2,circ=2*Math.PI*r;
  const[dash,setDash]=useState(0);
  const color=score>=81?"#FF3B5C":score>=61?"#FF8C00":score>=31?"#FFD60A":"#30D158";
  useEffect(()=>{const t=setTimeout(()=>setDash((score/100)*circ),200);return()=>clearTimeout(t);},[score,circ]);
  return(
    <div style={{position:"relative",width:size,height:size}}>
      <svg width={size} height={size} style={{transform:"rotate(-90deg)",position:"absolute"}}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={isDark?"rgba(255,255,255,0.06)":"rgba(0,0,0,0.08)"} strokeWidth={5}/>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={5}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
          style={{transition:"stroke-dasharray 1.1s cubic-bezier(0.34,1.56,0.64,1)"}}/>
      </svg>
      <div style={{position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,fontWeight:700,color,fontFamily:"'DM Mono',monospace"}}>{score?.toFixed(0)}</div>
    </div>
  );
}

/* ─── Custom chart tooltip ───────────────────────────────────────────── */
function ChartTooltip({active,payload,label,isDark}){
  if(!active||!payload?.length) return null;
  return(
    <div style={{background:isDark?"#1C1C1E":"#fff",border:`1px solid ${isDark?"rgba(255,255,255,0.1)":"rgba(0,0,0,0.12)"}`,borderRadius:10,padding:"10px 14px",boxShadow:"0 8px 24px rgba(0,0,0,0.15)"}}>
      <div style={{fontSize:12,color:isDark?"#8E8E93":"#777",marginBottom:6}}>{label}</div>
      {payload.map((p,i)=>(
        <div key={i} style={{fontSize:13,fontWeight:700,color:p.color||(isDark?"#F5F5F7":"#111"),fontFamily:"'DM Mono',monospace"}}>
          {p.name}: {p.value?.toLocaleString()}
        </div>
      ))}
    </div>
  );
}

/* ─── Theme toggle button ────────────────────────────────────────────── */
function ThemeToggle({isDark,onToggle}){
  const[hov,setHov]=useState(false);
  return(
    <button
      onClick={onToggle}
      onMouseEnter={()=>setHov(true)}
      onMouseLeave={()=>setHov(false)}
      title={isDark?"Switch to Light Mode":"Switch to Dark Mode"}
      style={{
        padding:"5px 10px",borderRadius:20,border:`1px solid ${isDark?"rgba(255,255,255,0.15)":"rgba(0,0,0,0.15)"}`,
        background:hov?(isDark?"rgba(255,255,255,0.1)":"rgba(0,0,0,0.08)"):(isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.04)"),
        color:isDark?"#F5F5F7":"#111",fontSize:16,cursor:"pointer",
        display:"flex",alignItems:"center",gap:6,transition:"all 0.25s",
        transform:hov?"scale(1.05)":"scale(1)"
      }}>
      <span style={{display:"inline-block",transition:"transform 0.4s cubic-bezier(0.34,1.56,0.64,1)",transform:isDark?"rotate(0deg)":"rotate(180deg)"}}>
        {isDark?"🌙":"☀️"}
      </span>
    </button>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   LOGIN PAGE
═══════════════════════════════════════════════════════════════════════ */
function Login({onLogin,isDark,onToggleTheme}){
  const[username,setUsername]=useState("");
  const[password,setPassword]=useState("");
  const[loading,setLoading]=useState(false);
  const[error,setError]=useState("");
  const[showPass,setShowPass]=useState(false);

  const handleLogin=async(e)=>{
    e.preventDefault();setLoading(true);setError("");
    try{
      const form=new FormData();
      form.append("username",username);form.append("password",password);
      const res=await fetch(`${API}/api/auth/login`,{method:"POST",body:form});
      const data=await res.json();
      if(!res.ok){setError(data.detail||"Invalid credentials");return;}
      localStorage.setItem("gst_token",data.access_token);
      localStorage.setItem("gst_user",JSON.stringify(data.user));
      onLogin(data.user,data.access_token);
    }catch{setError("Cannot connect to server");}
    finally{setLoading(false);}
  };

  const quickLogin=(u,p)=>{setUsername(u);setPassword(p);};

  const bg   = isDark?"#0A0A0B":"#F2F2F7";
  const card  = isDark?"rgba(255,255,255,0.03)":"rgba(255,255,255,0.85)";
  const bord  = isDark?"rgba(255,255,255,0.08)":"rgba(0,0,0,0.1)";
  const txt   = isDark?"#F5F5F7":"#111";
  const muted = isDark?"#8E8E93":"#666";

  return(
    <div style={{minHeight:"100vh",background:bg,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"'Sora',sans-serif",padding:"20px",transition:"background 0.4s"}}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        @keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
        @keyframes fadeIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes ripple{to{transform:scale(1);opacity:0}}
        @keyframes particleFloat{0%{transform:translateY(0) translateX(0);opacity:0.4}50%{opacity:0.8}100%{transform:translateY(-60px) translateX(20px);opacity:0}}
        @keyframes pulseRing{0%{transform:scale(1);opacity:0.6}100%{transform:scale(1.8);opacity:0}}
        @keyframes shimmerBar{0%{background-position:-200% 0}100%{background-position:200% 0}}
        .inp{width:100%;padding:14px 16px;background:${isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.04)"};border:1px solid ${bord};border-radius:12px;color:${txt};font-family:inherit;font-size:14px;transition:all 0.2s;outline:none}
        .inp:focus{border-color:rgba(255,59,92,0.6);box-shadow:0 0 0 3px rgba(255,59,92,0.1);background:${isDark?"rgba(255,255,255,0.07)":"rgba(0,0,0,0.06)"}}
        .inp::placeholder{color:${muted}}
        .btn-login{width:100%;padding:15px;background:linear-gradient(135deg,#FF3B5C,#FF6B00);border:none;border-radius:12px;color:white;font-family:inherit;font-size:15px;font-weight:700;cursor:pointer;transition:all 0.2s}
        .btn-login:hover{transform:translateY(-2px);box-shadow:0 10px 36px rgba(255,59,92,0.45)}
        .btn-login:active{transform:translateY(0)}
        .btn-login:disabled{opacity:0.6;cursor:not-allowed;transform:none}
        .quick-btn{padding:8px 14px;border-radius:10px;border:1px solid ${bord};background:${isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.04)"};color:${muted};font-family:inherit;font-size:12px;cursor:pointer;transition:all 0.2s;flex:1}
        .quick-btn:hover{background:${isDark?"rgba(255,255,255,0.09)":"rgba(0,0,0,0.09)"};color:${txt};transform:translateY(-1px)}
      `}</style>

      {/* Animated background blobs */}
      <div style={{position:"fixed",top:"15%",left:"25%",width:500,height:500,borderRadius:"50%",background:"rgba(255,59,92,0.05)",filter:"blur(100px)",pointerEvents:"none",animation:"float 8s ease-in-out infinite"}}/>
      <div style={{position:"fixed",bottom:"15%",right:"20%",width:400,height:400,borderRadius:"50%",background:"rgba(255,140,0,0.04)",filter:"blur(80px)",pointerEvents:"none",animation:"float 10s ease-in-out infinite reverse"}}/>

      {/* Theme toggle top-right */}
      <div style={{position:"fixed",top:20,right:20,zIndex:10}}>
        <ThemeToggle isDark={isDark} onToggle={onToggleTheme}/>
      </div>

      <div style={{width:"min(440px,100%)",animation:"fadeIn 0.55s ease"}}>
        <div style={{textAlign:"center",marginBottom:32}}>
          <div style={{position:"relative",display:"inline-block",marginBottom:16}}>
            <div style={{width:64,height:64,borderRadius:20,background:"linear-gradient(135deg,#FF3B5C,#FF6B00)",display:"inline-flex",alignItems:"center",justifyContent:"center",fontSize:30,animation:"float 3s ease-in-out infinite",boxShadow:"0 8px 32px rgba(255,59,92,0.4)"}}>🛡️</div>
            {/* Pulse rings */}
            <div style={{position:"absolute",inset:-8,borderRadius:28,border:"2px solid rgba(255,59,92,0.4)",animation:"pulseRing 1.8s ease-out infinite"}}/>
            <div style={{position:"absolute",inset:-8,borderRadius:28,border:"2px solid rgba(255,59,92,0.25)",animation:"pulseRing 1.8s ease-out 0.6s infinite"}}/>
          </div>
          <h1 style={{fontSize:24,fontWeight:800,color:txt}}>GST FraudShield</h1>
          <p style={{fontSize:13,color:muted,marginTop:6,letterSpacing:"0.04em"}}>AI-POWERED TAX INTELLIGENCE</p>
        </div>

        <div style={{background:card,border:`1px solid ${bord}`,borderRadius:24,padding:32,backdropFilter:"blur(20px)",transition:"background 0.4s"}}>
          <h2 style={{fontSize:18,fontWeight:700,color:txt,marginBottom:6}}>Sign In</h2>
          <p style={{fontSize:13,color:muted,marginBottom:24}}>Access the fraud detection dashboard</p>
          {error&&(
            <div style={{background:"rgba(255,59,92,0.1)",border:"1px solid rgba(255,59,92,0.3)",borderRadius:10,padding:"10px 14px",marginBottom:16,fontSize:13,color:"#FF3B5C",animation:"fadeIn 0.3s ease"}}>
              ⚠️ {error}
            </div>
          )}
          <form onSubmit={handleLogin}>
            <div style={{marginBottom:14}}>
              <label style={{fontSize:12,color:muted,display:"block",marginBottom:6,fontWeight:500,letterSpacing:"0.04em"}}>USERNAME</label>
              <input className="inp" type="text" placeholder="Enter username" value={username} onChange={e=>setUsername(e.target.value)} required autoComplete="username"/>
            </div>
            <div style={{marginBottom:24,position:"relative"}}>
              <label style={{fontSize:12,color:muted,display:"block",marginBottom:6,fontWeight:500,letterSpacing:"0.04em"}}>PASSWORD</label>
              <div style={{position:"relative"}}>
                <input className="inp" type={showPass?"text":"password"} placeholder="Enter password" value={password} onChange={e=>setPassword(e.target.value)} required style={{paddingRight:44}} autoComplete="current-password"/>
                <button type="button" onClick={()=>setShowPass(!showPass)} style={{position:"absolute",right:14,top:"50%",transform:"translateY(-50%)",background:"none",border:"none",color:muted,cursor:"pointer",fontSize:16,transition:"transform 0.2s"}}>
                  {showPass?"🙈":"👁️"}
                </button>
              </div>
            </div>
            <button type="submit" className="btn-login" disabled={loading}>
              {loading
                ?<span style={{display:"flex",alignItems:"center",justifyContent:"center",gap:10}}>
                   <span style={{width:16,height:16,border:"2px solid rgba(255,255,255,0.3)",borderTop:"2px solid white",borderRadius:"50%",animation:"spin 0.8s linear infinite",display:"inline-block"}}/>
                   Signing in...
                 </span>
                :"Sign In →"}
            </button>
          </form>

          <div style={{marginTop:24}}>
            <div style={{fontSize:11,color:muted,textAlign:"center",marginBottom:10,letterSpacing:"0.04em"}}>QUICK DEMO LOGIN</div>
            <div style={{display:"flex",gap:8}}>
              <button className="quick-btn" onClick={()=>quickLogin("admin","secret")}>👑 Admin</button>
              <button className="quick-btn" onClick={()=>quickLogin("officer","secret")}>🏛️ Officer</button>
              <button className="quick-btn" onClick={()=>quickLogin("ca","secret")}>📊 CA</button>
            </div>
            <div style={{fontSize:11,color:muted,textAlign:"center",marginTop:8}}>Password: <span style={{fontFamily:"'DM Mono',monospace",color:txt}}>secret</span></div>
          </div>
        </div>

        <div style={{marginTop:16,display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:8}}>
          {[{role:"Admin",icon:"👑",desc:"Full access",color:"#FF3B5C"},{role:"Officer",icon:"🏛️",desc:"View + investigate",color:"#FF8C00"},{role:"CA",icon:"📊",desc:"Reports only",color:"#30D158"}].map(({role,icon,desc,color})=>(
            <div key={role} style={{background:isDark?"rgba(255,255,255,0.02)":"rgba(0,0,0,0.03)",border:`1px solid ${bord}`,borderRadius:12,padding:"10px 12px",textAlign:"center",transition:"transform 0.2s,box-shadow 0.2s"}}
              onMouseEnter={e=>{e.currentTarget.style.transform="translateY(-2px)";e.currentTarget.style.boxShadow=`0 8px 20px ${color}22`;}}
              onMouseLeave={e=>{e.currentTarget.style.transform="";e.currentTarget.style.boxShadow="";}}>
              <div style={{fontSize:18,marginBottom:4}}>{icon}</div>
              <div style={{fontSize:11,fontWeight:700,color,marginBottom:2}}>{role}</div>
              <div style={{fontSize:10,color:muted}}>{desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   GSTIN MODAL
═══════════════════════════════════════════════════════════════════════ */
function GSTINModal({gstin,onClose,token,isDark}){
  const[data,      setData]      = useState(null);
  const[timeline,  setTimeline]  = useState([]);
  const[loading,   setLoading]   = useState(true);
  const[pdfLoading,setPdfLoading]= useState(false);
  const[activeTab, setActiveTab] = useState("overview");

  useEffect(()=>{
    const headers = token?{Authorization:`Bearer ${token}`}:{};

    // Load GSTIN details
    fetch(`${API}/api/gstin/${gstin}`,{headers})
      .then(r=>r.json())
      .then(d=>{ setData(d); setLoading(false); })
      .catch(()=>setLoading(false));

    // Load timeline
    fetch(`${API}/api/gstin/${gstin}/timeline`,{headers})
      .then(r=>r.json())
      .then(d=>setTimeline(d.timeline||[]))
      .catch(()=>{});
  },[gstin,token]);

  const downloadPDF=async()=>{
    setPdfLoading(true);
    try{
      const res=await fetch(`${API}/api/report/${gstin}`,{
        headers:token?{Authorization:`Bearer ${token}`}:{}
      });
      if(!res.ok){alert("PDF failed");return;}
      const blob=await res.blob();
      const url=URL.createObjectURL(blob);
      const a=document.createElement("a");
      a.href=url; a.download=`GST_Report_${gstin}.pdf`;
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(url);
    }catch{alert("PDF download failed");}
    finally{setPdfLoading(false);}
  };

  const level     = data?.risk_summary?.risk_level||"LOW";
  const color     = riskColor(level,isDark);
  const modalBg   = isDark?"#141416":"#ffffff";
  const modalBord = isDark?"rgba(255,255,255,0.1)":"rgba(0,0,0,0.1)";
  const txt       = isDark?"#F5F5F7":"#111";
  const muted     = isDark?"#8E8E93":"#666";
  const surfaceBg = isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.03)";
  const tabBd     = isDark?"rgba(255,255,255,0.06)":"rgba(0,0,0,0.07)";

  // ── Filed months count ──
  const filedCount   = timeline.filter(t=>t.filed).length;
  const missingCount = timeline.filter(t=>!t.filed).length;
  const maxSales     = Math.max(...timeline.map(t=>t.sales),1);

  return(
    <div onClick={onClose} style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.85)",backdropFilter:"blur(16px)",zIndex:1000,display:"flex",alignItems:"center",justifyContent:"center",padding:20,animation:"fadeIn 0.2s ease"}}>
      <div onClick={e=>e.stopPropagation()} style={{background:modalBg,border:`1px solid ${modalBord}`,borderRadius:24,padding:"24px",width:"min(620px,100%)",maxHeight:"90vh",overflowY:"auto",animation:"slideUp 0.35s ease",transition:"background 0.3s"}}>

        {loading?(
          <div style={{textAlign:"center",padding:48,color:muted}}>
            <div style={{fontSize:36,animation:"spin 0.8s linear infinite",display:"inline-block"}}>⟳</div>
            <div style={{marginTop:12}}>Loading report...</div>
          </div>
        ):data?(
          <>
            {/* ── Header ── */}
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:16,flexWrap:"wrap",gap:12}}>
              <div>
                <div style={{fontSize:11,color:muted,letterSpacing:"0.08em",marginBottom:6}}>INVESTIGATION REPORT</div>
                <div style={{fontSize:16,fontWeight:700,color:txt,fontFamily:"'DM Mono',monospace"}}>{gstin}</div>
                <div style={{fontSize:13,color:muted,marginTop:4}}>{data.company_info?.company_name}</div>
                <div style={{fontSize:12,color:muted,marginTop:2}}>📍 {data.company_info?.state} • {data.company_info?.industry}</div>
              </div>
              <div style={{textAlign:"right"}}>
                <div style={{padding:"4px 14px",borderRadius:20,background:riskBg(level,isDark),color,fontSize:12,fontWeight:700,border:`1px solid ${color}40`,marginBottom:8,display:"inline-block"}}>{level} RISK</div>
                <div style={{fontSize:38,fontWeight:900,color,fontFamily:"'DM Mono',monospace",lineHeight:1}}>{data.risk_summary?.ensemble_score?.toFixed(1)}%</div>
                {data.risk_summary?.in_circular_ring&&<div style={{fontSize:11,color:"#FF8C00",marginTop:4}}>🔄 Circular ring</div>}
                {data.risk_summary?.models_agreeing&&<div style={{fontSize:11,color:"#BF5AF2",marginTop:2}}>{data.risk_summary.models_agreeing} models agree</div>}
              </div>
            </div>

            {/* ── Tab navigation ── */}
            <div style={{display:"flex",gap:6,marginBottom:16,borderBottom:`1px solid ${tabBd}`,paddingBottom:12}}>
              {[["overview","📊 Overview"],["timeline","📅 Timeline"],["indicators","🎯 Indicators"]].map(([id,label])=>(
                <button key={id} onClick={()=>setActiveTab(id)} style={{
                  padding:"6px 14px",borderRadius:10,border:`1px solid ${tabBd}`,
                  background:activeTab===id?"rgba(255,59,92,0.12)":surfaceBg,
                  color:activeTab===id?"#FF3B5C":muted,
                  fontSize:12,fontWeight:500,cursor:"pointer",
                  fontFamily:"inherit",transition:"all 0.2s",
                }}>{label}</button>
              ))}
            </div>

            {/* ── OVERVIEW TAB ── */}
            {activeTab==="overview"&&(
              <>
                {/* Score breakdown */}
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:14}}>
                  {[
                    {label:"XGBoost",val:data.score_breakdown?.xgb_score,      color:"#0A84FF",icon:"🤖"},
                    {label:"Anomaly",val:data.score_breakdown?.anomaly_score,   color:"#BF5AF2",icon:"🎯"},
                    {label:"Graph",  val:data.score_breakdown?.graph_risk_score,color:"#FF9F0A",icon:"🕸️"},
                    {label:"Rules",  val:data.score_breakdown?.rule_score,      color:"#30D158",icon:"📋"},
                  ].map(({label,val,color:c,icon})=>(
                    <div key={label} style={{background:surfaceBg,borderRadius:14,padding:"12px 14px"}}>
                      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
                        <span style={{fontSize:12,color:muted}}>{icon} {label}</span>
                        <span style={{fontSize:18,fontWeight:800,color:c,fontFamily:"'DM Mono',monospace"}}>{val?.toFixed(1)}%</span>
                      </div>
                      <div style={{height:4,background:isDark?"rgba(255,255,255,0.06)":"rgba(0,0,0,0.07)",borderRadius:2,overflow:"hidden"}}>
                        <div style={{height:"100%",width:`${val}%`,background:c,borderRadius:2}}/>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Rule flags */}
                {data.rule_flags?.length>0&&(
                  <div style={{background:"rgba(255,59,92,0.06)",border:"1px solid rgba(255,59,92,0.2)",borderRadius:14,padding:14,marginBottom:14}}>
                    <div style={{fontSize:11,color:"#FF3B5C",fontWeight:700,marginBottom:8,letterSpacing:"0.06em"}}>⚠️ FRAUD INDICATORS</div>
                    {data.rule_flags.map((f,i)=>(
                      <div key={i} style={{fontSize:12,color:txt,padding:"4px 0",borderBottom:i<data.rule_flags.length-1?`1px solid ${isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.05)"}`:""  }}>• {f}</div>
                    ))}
                  </div>
                )}

                {/* Recommendation */}
                <div style={{background:surfaceBg,border:`1px solid ${tabBd}`,borderRadius:14,padding:14,marginBottom:14}}>
                  <div style={{fontSize:11,color:muted,fontWeight:700,marginBottom:8,letterSpacing:"0.06em"}}>📋 RECOMMENDATION</div>
                  <div style={{fontSize:13,color:txt,lineHeight:1.7}}>{data.recommendation}</div>
                </div>
              </>
            )}

            {/* ── TIMELINE TAB ── */}
            {activeTab==="timeline"&&(
              <div>
                {/* Filing stats */}
                <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:10,marginBottom:16}}>
                  {[
                    {label:"Filed",   value:filedCount,   color:"#30D158"},
                    {label:"Missing", value:missingCount,  color:"#FF3B5C"},
                    {label:"Rate",    value:`${((filedCount/Math.max(timeline.length,1))*100).toFixed(0)}%`, color:"#0A84FF"},
                  ].map(({label,value,color:c})=>(
                    <div key={label} style={{background:surfaceBg,borderRadius:12,padding:"12px 14px",textAlign:"center"}}>
                      <div style={{fontSize:22,fontWeight:800,color:c,fontFamily:"'DM Mono',monospace"}}>{value}</div>
                      <div style={{fontSize:11,color:muted,marginTop:4}}>{label} months</div>
                    </div>
                  ))}
                </div>

                {/* Sales line chart */}
                {timeline.length>0&&(
                  <>
                    <div style={{fontSize:11,color:muted,fontWeight:700,marginBottom:10,letterSpacing:"0.06em"}}>📈 MONTHLY SALES & ITC TREND</div>
                    <ResponsiveContainer width="100%" height={150}>
                      <LineChart data={timeline} margin={{top:0,right:0,left:-30,bottom:0}}>
                        <CartesianGrid strokeDasharray="3 3" stroke={isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.06)"}/>
                        <XAxis dataKey="month" tick={{fill:muted,fontSize:9}} axisLine={false} tickLine={false} interval={2}/>
                        <YAxis tick={{fill:muted,fontSize:9}} axisLine={false} tickLine={false}/>
                        <Tooltip content={<ChartTooltip isDark={isDark}/>} formatter={v=>`₹${(v/100000).toFixed(1)}L`}/>
                        <Line type="monotone" dataKey="sales" stroke="#0A84FF" strokeWidth={2} dot={false} name="Sales"/>
                        <Line type="monotone" dataKey="itc"   stroke="#FF3B5C" strokeWidth={2} dot={false} name="ITC"/>
                      </LineChart>
                    </ResponsiveContainer>
                  </>
                )}

                {/* Monthly filing status grid */}
                <div style={{marginTop:16}}>
                  <div style={{fontSize:11,color:muted,fontWeight:700,marginBottom:10,letterSpacing:"0.06em"}}>📅 MONTH-BY-MONTH STATUS</div>
                  <div style={{display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:4}}>
                    {timeline.map((m,i)=>(
                      <div key={i} title={`${m.month}: ${m.filed?"Filed":"MISSING"} ${m.delay>0?`(${m.delay}d delay)`:""}`}
                        style={{
                          borderRadius:8, padding:"8px 4px",
                          background:m.filed
                            ?(m.delay>30?"rgba(255,214,10,0.15)":"rgba(48,209,88,0.12)")
                            :"rgba(255,59,92,0.15)",
                          border:`1px solid ${m.filed?(m.delay>30?"rgba(255,214,10,0.3)":"rgba(48,209,88,0.25)"):"rgba(255,59,92,0.3)"}`,
                          textAlign:"center",cursor:"default",
                          boxShadow:!m.filed?"0 0 6px rgba(255,59,92,0.2)":"none",
                        }}>
                        <div style={{fontSize:9,color:muted,marginBottom:2}}>{m.month}</div>
                        <div style={{fontSize:14}}>
                          {m.filed?(m.delay>30?"⚠️":"✅"):"❌"}
                        </div>
                        {m.delay>0&&m.filed&&(
                          <div style={{fontSize:8,color:"#FFD60A",marginTop:1}}>{m.delay}d</div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Legend */}
                  <div style={{display:"flex",gap:16,marginTop:10,flexWrap:"wrap"}}>
                    {[
                      {icon:"✅",label:"Filed on time",  color:"#30D158"},
                      {icon:"⚠️",label:"Filed late (>30d)",color:"#FFD60A"},
                      {icon:"❌",label:"Missing return", color:"#FF3B5C"},
                    ].map(({icon,label,color:c})=>(
                      <div key={label} style={{display:"flex",alignItems:"center",gap:5}}>
                        <span style={{fontSize:12}}>{icon}</span>
                        <span style={{fontSize:11,color:muted}}>{label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Delay chart */}
                {timeline.some(t=>t.delay>0)&&(
                  <div style={{marginTop:16}}>
                    <div style={{fontSize:11,color:muted,fontWeight:700,marginBottom:10,letterSpacing:"0.06em"}}>⏱️ FILING DELAY (DAYS)</div>
                    <div style={{display:"flex",gap:3,alignItems:"flex-end",height:60}}>
                      {timeline.map((m,i)=>{
                        const h=m.filed?(m.delay/90)*100:100;
                        return(
                          <div key={i} title={`${m.month}: ${m.filed?`${m.delay}d delay`:"Not filed"}`}
                            style={{
                              flex:1,height:`${Math.max(h,4)}%`,
                              background:m.filed
                                ?(m.delay>30?"#FFD60A":m.delay>0?"#FF8C00":"#30D158")
                                :"#FF3B5C",
                              borderRadius:"2px 2px 0 0",
                              transition:"height 0.5s ease",
                              opacity:0.8,
                            }}/>
                        );
                      })}
                    </div>
                    <div style={{display:"flex",justifyContent:"space-between",marginTop:4}}>
                      <span style={{fontSize:9,color:muted}}>{timeline[0]?.month}</span>
                      <span style={{fontSize:9,color:muted}}>{timeline[timeline.length-1]?.month}</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── INDICATORS TAB ── */}
            {activeTab==="indicators"&&(
              <div>
                <div style={{background:surfaceBg,border:`1px solid ${tabBd}`,borderRadius:14,padding:16,marginBottom:14}}>
                  <div style={{fontSize:11,color:muted,fontWeight:700,marginBottom:12,letterSpacing:"0.06em"}}>📊 KEY FRAUD INDICATORS</div>
                  <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
                    {[
                      {label:"ITC Ratio",        val:`${data.fraud_indicators?.avg_itc_ratio?.toFixed(3)||0}x`,      warn:data.fraud_indicators?.avg_itc_ratio>1.5},
                      {label:"Filing Rate",       val:`${(data.fraud_indicators?.filing_rate*100||0).toFixed(1)}%`,   warn:data.fraud_indicators?.filing_rate<0.8},
                      {label:"Missing Returns",   val:`${data.fraud_indicators?.missing_returns||0} months`,           warn:data.fraud_indicators?.missing_returns>2},
                      {label:"Sales Spike",       val:`${data.fraud_indicators?.spike_ratio?.toFixed(2)||0}x`,        warn:data.fraud_indicators?.spike_ratio>3},
                      {label:"Invoice Match",     val:`${(data.fraud_indicators?.invoice_match_rate*100||0).toFixed(1)}%`, warn:data.fraud_indicators?.invoice_match_rate<0.8},
                      {label:"Sales Volatility",  val:`${data.fraud_indicators?.sales_volatility?.toFixed(3)||0}`,    warn:data.fraud_indicators?.sales_volatility>0.8},
                    ].map(({label,val,warn})=>(
                      <div key={label} style={{
                        display:"flex",justifyContent:"space-between",
                        fontSize:12,padding:"10px 12px",borderRadius:10,
                        background:warn?"rgba(255,59,92,0.06)":surfaceBg,
                        border:`1px solid ${warn?"rgba(255,59,92,0.2)":tabBd}`,
                      }}>
                        <span style={{color:muted}}>{label}</span>
                        <span style={{color:warn?"#FF3B5C":txt,fontFamily:"'DM Mono',monospace",fontWeight:600}}>
                          {warn&&"⚠️ "}{val}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Company info */}
                <div style={{background:surfaceBg,border:`1px solid ${tabBd}`,borderRadius:14,padding:16}}>
                  <div style={{fontSize:11,color:muted,fontWeight:700,marginBottom:12,letterSpacing:"0.06em"}}>🏢 COMPANY DETAILS</div>
                  {[
                    {label:"Annual Turnover", val:`₹${(data.company_info?.annual_turnover||0).toLocaleString("en-IN")}`},
                    {label:"Years Active",    val:`${data.company_info?.years_old||0} years`},
                    {label:"Industry",        val:data.company_info?.industry||"N/A"},
                    {label:"State",           val:data.company_info?.state||"N/A"},
                  ].map(({label,val})=>(
                    <div key={label} style={{display:"flex",justifyContent:"space-between",fontSize:12,padding:"6px 0",borderBottom:`1px solid ${tabBd}`}}>
                      <span style={{color:muted}}>{label}</span>
                      <span style={{color:txt,fontWeight:600}}>{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Action buttons ── */}
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginTop:16}}>
              <button onClick={downloadPDF} disabled={pdfLoading}
                style={{padding:13,borderRadius:12,background:"linear-gradient(135deg,#FF3B5C,#FF6B00)",border:"none",color:"white",fontSize:13,cursor:"pointer",fontFamily:"inherit",fontWeight:600,opacity:pdfLoading?0.7:1,transition:"transform 0.2s,box-shadow 0.2s"}}
                onMouseEnter={e=>{if(!pdfLoading){e.currentTarget.style.transform="translateY(-1px)";e.currentTarget.style.boxShadow="0 8px 24px rgba(255,59,92,0.4)";}}}
                onMouseLeave={e=>{e.currentTarget.style.transform="";e.currentTarget.style.boxShadow="";}}>
                {pdfLoading?"⟳ Generating...":"📄 Download PDF"}
              </button>
              <button onClick={onClose}
                style={{padding:13,borderRadius:12,background:surfaceBg,border:`1px solid ${modalBord}`,color:txt,fontSize:13,cursor:"pointer",fontFamily:"inherit",transition:"background 0.2s"}}
                onMouseEnter={e=>e.currentTarget.style.background=isDark?"rgba(255,255,255,0.1)":"rgba(0,0,0,0.07)"}
                onMouseLeave={e=>e.currentTarget.style.background=surfaceBg}>
                Close Report
              </button>
            </div>
          </>
        ):(
          <div style={{textAlign:"center",padding:40,color:muted}}>
            <div style={{fontSize:40,marginBottom:12}}>⚠️</div>
            <div>Could not load report</div>
          </div>
        )}
      </div>
    </div>
  );
}
function ReanalyzeButton({ token, isDark }) {
  const [status,   setStatus]   = useState(null);
  const [running,  setRunning]  = useState(false);
  const [showPanel,setShowPanel]= useState(false);

  const txt   = isDark ? "#F5F5F7" : "#111";
  const muted = isDark ? "#8E8E93" : "#666";
  const cardBg= isDark ? "#1C1C1E" : "#fff";
  const cardBd= isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)";

  const authHeaders = token
    ? { Authorization:`Bearer ${token}`, "Content-Type":"application/json" }
    : {};

  // ── Poll status while running ──
  useEffect(() => {
    if (!running) return;
    const interval = setInterval(async () => {
      try {
        const res  = await fetch(`${API}/api/reanalyze/status`);
        const data = await res.json();
        setStatus(data);
        if (!data.running) {
          setRunning(false);
          clearInterval(interval);
        }
      } catch {}
    }, 1000);
    return () => clearInterval(interval);
  }, [running]);

  const handleReanalyze = async () => {
    try {
      const res = await fetch(`${API}/api/reanalyze`, {
        method: "POST", headers: authHeaders,
      });
      if (res.ok) {
        setRunning(true);
        setShowPanel(true);
        setStatus({ running:true, progress:0, message:"Starting..." });
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to start");
      }
    } catch {
      alert("Cannot connect to API");
    }
  };

  return (
    <div style={{ position:"relative" }}>
      <button
        onClick={() => running ? setShowPanel(!showPanel) : handleReanalyze()}
        disabled={running}
        style={{
          padding:"6px 14px", borderRadius:10,
          background: running
            ? "rgba(255,59,92,0.1)"
            : "rgba(255,255,255,0.06)",
          border:`1px solid ${running?"rgba(255,59,92,0.3)":"rgba(255,255,255,0.1)"}`,
          color: running ? "#FF3B5C" : muted,
          fontSize:12, cursor: running ? "default" : "pointer",
          fontFamily:"inherit", fontWeight:500,
          display:"flex", alignItems:"center", gap:6,
          transition:"all 0.2s",
          whiteSpace:"nowrap",
        }}
        onMouseEnter={e=>{if(!running)e.currentTarget.style.background="rgba(255,255,255,0.1)";}}
        onMouseLeave={e=>{if(!running)e.currentTarget.style.background="rgba(255,255,255,0.06)";}}
      >
        <span style={{
          display:"inline-block",
          animation: running ? "spin 1s linear infinite" : "none"
        }}>🔄</span>
        {running ? `${status?.progress||0}%` : "Re-analyze"}
      </button>

      {/* Status panel */}
      {showPanel && status && (
        <div style={{
          position:"absolute", top:"calc(100% + 8px)", right:0,
          width:300, background:cardBg,
          border:`1px solid ${cardBd}`, borderRadius:16,
          padding:20, zIndex:200,
          boxShadow:"0 16px 48px rgba(0,0,0,0.3)",
          animation:"slideUp 0.2s ease",
        }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
            <div style={{ fontSize:13, fontWeight:700, color:txt }}>🔄 Re-analysis</div>
            <button onClick={()=>setShowPanel(false)} style={{ background:"none", border:"none", color:muted, cursor:"pointer", fontSize:16 }}>✕</button>
          </div>

          {/* Progress bar */}
          <div style={{ height:6, background:isDark?"rgba(255,255,255,0.06)":"rgba(0,0,0,0.08)", borderRadius:3, overflow:"hidden", marginBottom:10 }}>
            <div style={{
              height:"100%",
              width:`${status.progress||0}%`,
              background:"linear-gradient(90deg,#FF3B5C,#FF6B00)",
              borderRadius:3,
              transition:"width 0.5s ease",
              boxShadow:"0 0 8px rgba(255,59,92,0.5)",
            }}/>
          </div>

          <div style={{ fontSize:12, color: status.completed ? "#30D158" : muted, marginBottom:12 }}>
            {status.message}
          </div>

          {/* Steps */}
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            {[
              {label:"Load models",     done:status.progress>=25},
              {label:"XGBoost scoring", done:status.progress>=40},
              {label:"Anomaly detect",  done:status.progress>=55},
              {label:"Graph analysis",  done:status.progress>=70},
              {label:"Rule scoring",    done:status.progress>=85},
              {label:"Update database", done:status.progress>=100},
            ].map(({label,done})=>(
              <div key={label} style={{ display:"flex", alignItems:"center", gap:8 }}>
                <div style={{
                  width:16, height:16, borderRadius:"50%", flexShrink:0,
                  background: done ? "#30D158" : isDark?"rgba(255,255,255,0.06)":"rgba(0,0,0,0.08)",
                  display:"flex", alignItems:"center", justifyContent:"center",
                  fontSize:10, transition:"background 0.3s",
                }}>
                  {done ? "✓" : ""}
                </div>
                <span style={{ fontSize:11, color: done ? txt : muted }}>{label}</span>
              </div>
            ))}
          </div>

          {status.completed && (
            <button onClick={()=>{setShowPanel(false);window.location.reload();}}
              style={{ width:"100%", marginTop:14, padding:"10px", borderRadius:10, background:"linear-gradient(135deg,#30D158,#1A8A35)", border:"none", color:"white", fontSize:12, cursor:"pointer", fontFamily:"inherit", fontWeight:600 }}>
              ✅ Refresh Dashboard
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   MAIN APP
═══════════════════════════════════════════════════════════════════════ */
export default function App(){
  const[user,setUser]=useState(()=>{const s=localStorage.getItem("gst_user");return s?JSON.parse(s):null;});
  const[token,setToken]=useState(()=>localStorage.getItem("gst_token")||"");
  const[stats,setStats]=useState(null);
  const[topRisks,setTopRisks]=useState([]);
  const[search,setSearch]=useState("");
  const[searchResults,setSearchResults]=useState([]);
  const[searching,setSearching]=useState(false);
  const[selectedGstin,setSelectedGstin]=useState(null);
  const[activeTab,setActiveTab]=useState("dashboard");
  const[alerts,setAlerts]=useState([]);
  const[alertsLoading,setAlertsLoading]=useState(false);
  const[apiOnline,setApiOnline]=useState(false);
  const[loaded,setLoaded]=useState(false);
  const[mobileMenuOpen,setMobileMenuOpen]=useState(false);

  /* ── Theme state ── */
  const[isDark,setIsDark]=useState(()=>{
    const saved=localStorage.getItem("gst_theme");
    return saved!==null?saved==="dark":true;
  });
  const toggleTheme=()=>{
    setIsDark(d=>{localStorage.setItem("gst_theme",d?"light":"dark");return !d;});
  };

  const handleLogin=(u,t)=>{setUser(u);setToken(t);};
  const handleLogout=()=>{localStorage.removeItem("gst_token");localStorage.removeItem("gst_user");setUser(null);setToken("");};
  const authHeaders=useMemo(()=>token?{Authorization:`Bearer ${token}`}:{},[token]);

  useEffect(()=>{
    if(!user)return;
    Promise.all([
      fetch(`${API}/api/dashboard/stats`,{headers:authHeaders}).then(r=>r.json()),
      fetch(`${API}/api/top-risks?n=10`,{headers:authHeaders}).then(r=>r.json()),
    ]).then(([s,t])=>{setStats(s);setTopRisks(t.top_risks||[]);setApiOnline(true);})
    .catch(()=>{setStats(MOCK.stats);setTopRisks(MOCK.topRisks);})
    .finally(()=>setLoaded(true));
  },[user,authHeaders]);

  useEffect(()=>{
    if(!user||activeTab!=="alerts")return;
    setAlertsLoading(true);
    fetch(`${API}/api/alerts?page_size=50`,{headers:authHeaders})
      .then(r=>r.json()).then(d=>setAlerts(d.alerts||[]))
      .catch(()=>setAlerts(MOCK.topRisks))
      .finally(()=>setAlertsLoading(false));
  },[activeTab,user,authHeaders]);

  useEffect(()=>{
    if(!search.trim()||search.length<3){setSearchResults([]);return;}
    const t=setTimeout(()=>{
      setSearching(true);
      fetch(`${API}/api/search?q=${search}&limit=8`,{headers:authHeaders})
        .then(r=>r.json()).then(d=>setSearchResults(d.results||[]))
        .catch(()=>setSearchResults([]))
        .finally(()=>setSearching(false));
    },350);
    return()=>clearTimeout(t);
  },[search,authHeaders]);

  if(!user) return<Login onLogin={handleLogin} isDark={isDark} onToggleTheme={toggleTheme}/>;

  const fraudTypes=stats?.fraud_type_breakdown||{};
  const pieData=Object.entries(fraudTypes).map(([name,value],i)=>({name:name.replace(/_/g," "),value,color:CHART_COLORS[i%CHART_COLORS.length]}));
  const barData=[
    {name:"Critical",count:stats?.critical_count||56,fill:"#FF3B5C"},
    {name:"High",    count:stats?.high_count||485,   fill:"#FF8C00"},
    {name:"Medium",  count:stats?.medium_count||471,  fill:"#FFD60A"},
    {name:"Low",     count:stats?.low_count||3988,    fill:"#30D158"},
  ];
  const modelData=[
    {model:"XGBoost",  accuracy:94.8,precision:98.9,recall:95.5},
    {model:"IsoForest",accuracy:47,  precision:35.7,recall:13.5},
    {model:"Graph",    accuracy:51,  precision:87.4,recall:18.8},
    {model:"Ensemble", accuracy:95.76,precision:99.5,recall:79.2},
  ];
  const radialData=[
    {name:"Accuracy", value:95.76,fill:"#30D158"},
    {name:"Precision",value:99.50,fill:"#0A84FF"},
    {name:"Recall",   value:79.20,fill:"#BF5AF2"},
    {name:"AUC-ROC",  value:98.28,fill:"#FF8C00"},
  ];

  /* ── Theme-derived values ── */
  const bg       = isDark?"#0A0A0B":"#F2F2F7";
  const cardBg   = isDark?"rgba(255,255,255,0.025)":"rgba(255,255,255,0.9)";
  const cardBord = isDark?"rgba(255,255,255,0.07)":"rgba(0,0,0,0.08)";
  const txt      = isDark?"#F5F5F7":"#111";
  const muted    = isDark?"#8E8E93":"#666";
  const headerBg = isDark?"rgba(10,10,11,0.92)":"rgba(242,242,247,0.92)";
  const navActive= isDark?"rgba(255,59,92,0.12)":"rgba(255,59,92,0.1)";
  const surfaceBg= isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.04)";

  if(!loaded) return(
    <div style={{minHeight:"100vh",background:bg,display:"flex",alignItems:"center",justifyContent:"center",flexDirection:"column",gap:16,transition:"background 0.4s"}}>
      <div style={{width:52,height:52,border:`3px solid ${isDark?"rgba(255,255,255,0.08)":"rgba(0,0,0,0.1)"}`,borderTop:"3px solid #FF3B5C",borderRadius:"50%",animation:"spin 0.8s linear infinite"}}/>
      <div style={{color:muted,fontSize:13,fontFamily:"'DM Mono',monospace"}}>LOADING FRAUD INTELLIGENCE...</div>
    </div>
  );

  const navTabs=[["dashboard","📊","Dashboard"],["alerts","🚨","Alerts"],["search","🔍","Search"],["bulk","📤","Bulk"],["heatmap","🗺️","Heatmap"],["users","👥","Users"],["analytics","📊","Analytics"]];

  return(
    <div style={{minHeight:"100vh",background:bg,color:txt,fontFamily:"'Sora',sans-serif",transition:"background 0.4s,color 0.4s"}}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=DM+Mono:ital,wght@0,400;0,500&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:4px}
        ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:${isDark?"rgba(255,255,255,0.1)":"rgba(0,0,0,0.15)"};border-radius:2px}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes fadeIn{from{opacity:0}to{opacity:1}}
        @keyframes slideUp{from{transform:translateY(28px);opacity:0}to{transform:translateY(0);opacity:1}}
        @keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
        @keyframes glow{0%,100%{box-shadow:0 0 20px rgba(255,59,92,0.3)}50%{box-shadow:0 0 40px rgba(255,59,92,0.5)}}
        @keyframes ripple{to{transform:scale(1);opacity:0}}
        @keyframes pulseRing{0%{transform:scale(1);opacity:0.5}100%{transform:scale(1.7);opacity:0}}
        @keyframes shimmerBar{0%{background-position:-200% 0}100%{background-position:200% 0}}
        @keyframes tabSlide{from{opacity:0;transform:translateX(12px)}to{opacity:1;transform:translateX(0)}}
        @keyframes statusPop{0%{transform:scale(1)}50%{transform:scale(1.4)}100%{transform:scale(1)}}
        .nav-btn{background:none;border:none;cursor:pointer;padding:8px 14px;border-radius:10px;font-family:inherit;font-size:13px;font-weight:500;transition:all 0.2s;white-space:nowrap}
        .nav-btn:hover{background:${isDark?"rgba(255,255,255,0.06)":"rgba(0,0,0,0.05)"}}
        .nav-btn.active{background:${navActive};color:#FF3B5C}
        .row-hover{transition:background 0.15s,transform 0.15s;position:relative;overflow:hidden}
        .row-hover:hover{background:${isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.03)"}!important;cursor:pointer;transform:translateX(3px)}
        .search-inp:focus{outline:none;border-color:rgba(255,59,92,0.6)!important;box-shadow:0 0 0 3px rgba(255,59,92,0.1)}
        .tab-content{animation:tabSlide 0.3s ease}
        .card{background:${cardBg};border:1px solid ${cardBord};border-radius:20px;transition:background 0.4s,border-color 0.4s}
        .hint-btn:hover{background:${isDark?"rgba(255,255,255,0.08)":"rgba(0,0,0,0.07)"}!important;color:${txt}!important}
        .logout-btn:hover{background:rgba(255,59,92,0.2)!important}
        .score-bar{background-image:linear-gradient(90deg,transparent,rgba(255,255,255,0.25),transparent);background-size:200% 100%;animation:shimmerBar 2.2s ease-in-out infinite}
        @media(max-width:900px){
          .chart-grid{grid-template-columns:1fr!important}
          .main-grid{grid-template-columns:1fr!important}
        }
        @media(max-width:768px){
          .desktop-nav{display:none!important}
          .mobile-menu-btn{display:flex!important}
          .stat-grid{grid-template-columns:1fr 1fr!important}
          .model-grid{grid-template-columns:1fr 1fr!important}
          .alert-table{grid-template-columns:1fr 80px 70px!important}
          .alert-table .hide-mobile{display:none!important}
          .header-user{display:none!important}
        }
        @media(max-width:480px){
          .stat-grid{grid-template-columns:1fr!important}
          .model-grid{grid-template-columns:1fr!important}
          .risk-rank{display:none!important}
          .risk-row{grid-template-columns:1fr 36px 68px!important;gap:8px!important}
          .risk-gauge-size{width:36px!important;height:36px!important}
        }
        @media(max-width:400px){
          .modal-score-grid{grid-template-columns:1fr!important}
          .modal-indicators-grid{grid-template-columns:1fr!important}
        }
      `}</style>

      {/* ── HEADER ── */}
      <header style={{padding:"12px 16px",display:"flex",alignItems:"center",justifyContent:"space-between",borderBottom:`1px solid ${cardBord}`,position:"sticky",top:0,zIndex:100,background:headerBg,backdropFilter:"blur(24px)",gap:12,transition:"background 0.4s,border-color 0.4s"}}>
        <div style={{display:"flex",alignItems:"center",gap:10,flexShrink:0}}>
          <div style={{position:"relative"}}>
            <div style={{width:36,height:36,borderRadius:11,background:"linear-gradient(135deg,#FF3B5C,#FF6B00)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,animation:"float 4s ease-in-out infinite",boxShadow:"0 4px 20px rgba(255,59,92,0.35)"}}>🛡️</div>
            <div style={{position:"absolute",inset:-4,borderRadius:15,border:"1.5px solid rgba(255,59,92,0.4)",animation:"pulseRing 2s ease-out infinite"}}/>
          </div>
          <div style={{fontSize:14,fontWeight:700,color:txt}}>GST FraudShield</div>
        </div>

        {/* Desktop nav */}
        <nav className="desktop-nav" style={{display:"flex",gap:2,flex:1,justifyContent:"center"}}>
          {navTabs.map(([id,icon,label])=>(
            <button key={id} className={`nav-btn ${activeTab===id?"active":""}`} onClick={()=>setActiveTab(id)} style={{color:activeTab===id?"#FF3B5C":muted}}>
              {icon} {label}
            </button>
          ))}
        </nav>

        {/* Theme toggle — always visible on all screen sizes */}
        <div style={{flexShrink:0}}>
          <ThemeToggle isDark={isDark} onToggle={toggleTheme}/>
        </div>

        {/* Mobile menu button */}
        <button className="mobile-menu-btn" onClick={()=>setMobileMenuOpen(!mobileMenuOpen)}
          style={{display:"none",background:surfaceBg,border:`1px solid ${cardBord}`,borderRadius:10,padding:"8px 12px",color:txt,cursor:"pointer",fontSize:18,alignItems:"center"}}>
          {mobileMenuOpen?"✕":"☰"}
        </button>

        <div className="header-user" style={{display:"flex",alignItems:"center",gap:10,flexShrink:0}}>

          <div style={{display:"flex",alignItems:"center",gap:6}}>
            <div style={{position:"relative",width:8,height:8}}>
              <div style={{width:8,height:8,borderRadius:"50%",background:apiOnline?"#30D158":"#FF3B5C",position:"absolute"}}/>
              {apiOnline&&<div style={{width:8,height:8,borderRadius:"50%",background:"#30D158",position:"absolute",animation:"pulseRing 1.5s ease-out infinite"}}/>}
            </div>
            <span style={{fontSize:11,color:muted}}>{apiOnline?"Live":"Demo"}</span>
          </div>
          <div style={{width:1,height:18,background:cardBord}}/>
          <div style={{display:"flex",alignItems:"center",gap:8}}>
            <div style={{width:30,height:30,borderRadius:10,background:surfaceBg,display:"flex",alignItems:"center",justifyContent:"center",fontSize:15}}>{roleIcon(user.role)}</div>
            <div>
              <div style={{fontSize:12,fontWeight:600,color:txt,maxWidth:100,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{user.full_name}</div>
              <div style={{fontSize:10,color:muted,textTransform:"capitalize"}}>{user.role}</div>
            </div>
          </div>
          {/* Re-analyze button — admin only */}
          {user?.role === "admin" && (
            <ReanalyzeButton token={token} isDark={isDark}/>
          )}
          <button onClick={handleLogout} className="logout-btn" style={{padding:"5px 10px",borderRadius:8,border:"1px solid rgba(255,59,92,0.3)",background:"rgba(255,59,92,0.08)",color:"#FF3B5C",fontSize:11,cursor:"pointer",fontFamily:"inherit",whiteSpace:"nowrap",transition:"all 0.2s"}}>Logout</button>
        </div>
      </header>

      {/* Mobile dropdown nav */}
      {mobileMenuOpen&&(
        <div style={{background:headerBg,borderBottom:`1px solid ${cardBord}`,padding:"12px 16px",display:"flex",flexDirection:"column",gap:4,position:"sticky",top:60,zIndex:99,animation:"slideUp 0.25s ease"}}>
          {navTabs.map(([id,icon,label])=>(
            <button key={id} className={`nav-btn ${activeTab===id?"active":""}`}
              onClick={()=>{setActiveTab(id);setMobileMenuOpen(false);}}
              style={{color:activeTab===id?"#FF3B5C":muted,textAlign:"left",width:"100%",padding:"10px 14px"}}>
              {icon} {label}
            </button>
          ))}
          <div style={{borderTop:`1px solid ${cardBord}`,marginTop:8,paddingTop:8,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span style={{fontSize:12,color:muted}}>{roleIcon(user.role)} {user.full_name}</span>
            <button onClick={handleLogout} style={{padding:"5px 10px",borderRadius:8,border:"1px solid rgba(255,59,92,0.3)",background:"rgba(255,59,92,0.08)",color:"#FF3B5C",fontSize:11,cursor:"pointer",fontFamily:"inherit"}}>Logout</button>
          </div>
        </div>
      )}

      <main style={{maxWidth:1300,margin:"0 auto",padding:"20px 16px"}}>

        {/* ── DASHBOARD ── */}
        {activeTab==="dashboard"&&(
          <div className="tab-content">
            <div style={{marginBottom:20,display:"flex",justifyContent:"space-between",alignItems:"flex-end",flexWrap:"wrap",gap:8}}>
              <div>
                <h1 style={{fontSize:"clamp(18px,4vw,24px)",fontWeight:800,color:txt}}>Fraud Intelligence Dashboard</h1>
                <p style={{fontSize:12,color:muted,marginTop:4}}>
                  Real-time detection across {(stats?.total_gstins||5000).toLocaleString()} GSTINs • Logged in as <span style={{color:"#FF3B5C",fontWeight:600}}>{user.full_name}</span>
                </p>
              </div>
              <div style={{fontSize:11,color:muted,fontFamily:"'DM Mono',monospace"}}>{new Date().toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}</div>
            </div>

            {/* Stat cards */}
            <div className="stat-grid" style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:20}}>
              <StatCard label="Total GSTINs"  value={stats?.total_gstins||0}  icon="🏢" color="#0A84FF" delay={0}   sub="Analyzed"         isDark={isDark}/>
              <StatCard label="Critical Alerts" value={stats?.critical_count||0} icon="🔴" color="#FF3B5C" delay={80}  sub="Immediate action"  isDark={isDark}/>
              <StatCard label="High Risk"       value={stats?.high_count||0}    icon="🟠" color="#FF8C00" delay={160} sub="Review soon"       isDark={isDark}/>
              <StatCard label="Total Alerts"    value={stats?.total_alerts||0}  icon="⚡" color="#BF5AF2" delay={240} sub={`${stats?.alert_rate?.toFixed(1)||0}% rate`} isDark={isDark}/>
            </div>

            {/* Charts row 1 */}
            <div className="chart-grid" style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:16}}>
              <div className="card" style={{padding:"18px 20px"}}>
                <div style={{fontSize:14,fontWeight:700,marginBottom:4,color:txt}}>🎭 Fraud Type Distribution</div>
                <div style={{fontSize:11,color:muted,marginBottom:16}}>Breakdown of detected fraud patterns</div>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                      {pieData.map((entry,i)=><Cell key={i} fill={entry.color}/>)}
                    </Pie>
                    <Tooltip content={<ChartTooltip isDark={isDark}/>}/>
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{fontSize:11,color:muted}}/>
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="card" style={{padding:"18px 20px"}}>
                <div style={{fontSize:14,fontWeight:700,marginBottom:4,color:txt}}>📊 Risk Distribution</div>
                <div style={{fontSize:11,color:muted,marginBottom:16}}>GSTINs by risk level</div>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={barData} margin={{top:0,right:0,left:-20,bottom:0}}>
                    <CartesianGrid strokeDasharray="3 3" stroke={isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.06)"}/>
                    <XAxis dataKey="name" tick={{fill:muted,fontSize:11}} axisLine={false} tickLine={false}/>
                    <YAxis tick={{fill:muted,fontSize:10}} axisLine={false} tickLine={false}/>
                    <Tooltip content={<ChartTooltip isDark={isDark}/>}/>
                    <Bar dataKey="count" radius={[6,6,0,0]}>
                      {barData.map((entry,i)=><Cell key={i} fill={entry.fill}/>)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Main content grid */}
            <div className="main-grid" style={{display:"grid",gridTemplateColumns:"1.5fr 1fr",gap:16,marginBottom:16}}>
              {/* Top risks */}
              <div className="card" style={{overflow:"hidden"}}>
                <div style={{padding:"16px 20px 12px",borderBottom:`1px solid ${cardBord}`,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                  <div>
                    <div style={{fontSize:14,fontWeight:700,color:txt}}>🎯 Top Risk GSTINs</div>
                    <div style={{fontSize:11,color:muted,marginTop:2}}>Click for full investigation report</div>
                  </div>
                  <button onClick={()=>setActiveTab("alerts")}
                    style={{fontSize:11,color:"#FF3B5C",background:"rgba(255,59,92,0.1)",border:"1px solid rgba(255,59,92,0.2)",borderRadius:8,padding:"4px 10px",cursor:"pointer",fontFamily:"inherit",whiteSpace:"nowrap",transition:"background 0.2s,transform 0.2s"}}
                    onMouseEnter={e=>{e.currentTarget.style.background="rgba(255,59,92,0.2)";e.currentTarget.style.transform="scale(1.03)";}}
                    onMouseLeave={e=>{e.currentTarget.style.background="rgba(255,59,92,0.1)";e.currentTarget.style.transform="";}}>
                    View All {stats?.total_alerts} →
                  </button>
                </div>
                <div>
                  {topRisks.slice(0,7).map((r,i)=>{
                    const color=riskColor(r.risk_level,isDark);
                    return(
                      <div key={r.gstin} className="row-hover risk-row" onClick={()=>setSelectedGstin(r.gstin)}
                        style={{display:"grid",gridTemplateColumns:"24px 1fr 52px 80px",gap:10,padding:"10px 20px",alignItems:"center",borderBottom:`1px solid ${isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.05)"}`,animation:`slideUp 0.4s ease ${i*50}ms both`}}>
                        <div className="risk-rank" style={{fontSize:11,color:muted,fontFamily:"'DM Mono',monospace",textAlign:"center"}}>#{r.rank}</div>
                        <div>
                          <div style={{fontSize:12,fontFamily:"'DM Mono',monospace",fontWeight:600,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",color:txt}}>{r.gstin}</div>
                          <div style={{fontSize:11,color:muted,marginTop:2,display:"flex",gap:6,flexWrap:"wrap"}}>
                            <span>{fraudIcon(r.fraud_type)} {r.fraud_type?.replace(/_/g," ")}</span>
                            {r.in_circular_ring&&<span style={{color:"#FF8C00"}}>🔄 ring</span>}
                            {r.models_agreeing>=3&&<span style={{color:"#BF5AF2"}}>•{r.models_agreeing} agree</span>}
                          </div>
                        </div>
                        <ScoreGauge score={r.ensemble_score} size={44} isDark={isDark}/>
                        <span style={{padding:"3px 8px",borderRadius:20,fontSize:10,fontWeight:700,background:riskBg(r.risk_level,isDark),color,border:`1px solid ${color}35`,textAlign:"center"}}>{r.risk_level}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Right panels */}
              <div style={{display:"flex",flexDirection:"column",gap:12}}>
                <div className="card" style={{padding:"18px 20px"}}>
                  <div style={{fontSize:14,fontWeight:700,marginBottom:4,color:txt}}>🤖 Model Performance</div>
                  <div style={{fontSize:11,color:muted,marginBottom:12}}>Ensemble accuracy metrics</div>
                  <ResponsiveContainer width="100%" height={160}>
                    <RadialBarChart cx="50%" cy="50%" innerRadius="20%" outerRadius="90%" data={radialData} startAngle={180} endAngle={0}>
                      <RadialBar dataKey="value" cornerRadius={4} background={{fill:isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.05)"}}/>
                      <Tooltip content={<ChartTooltip isDark={isDark}/>} formatter={(v)=>`${v}%`}/>
                    </RadialBarChart>
                  </ResponsiveContainer>
                  <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6}}>
                    {radialData.map(({name,value,fill})=>(
                      <div key={name} style={{display:"flex",alignItems:"center",gap:6}}>
                        <div style={{width:8,height:8,borderRadius:"50%",background:fill,flexShrink:0}}/>
                        <span style={{fontSize:11,color:muted}}>{name}</span>
                        <span style={{fontSize:11,fontWeight:700,color:fill,marginLeft:"auto",fontFamily:"'DM Mono',monospace"}}>{value}%</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card" style={{padding:"16px 20px"}}>
                  <div style={{fontSize:14,fontWeight:700,marginBottom:12,color:txt}}>⚡ Quick Stats</div>
                  {[
                    {label:"Circular Rings",  value:"178",   color:"#FF8C00"},
                    {label:"Shell Clusters",  value:"914",   color:"#BF5AF2"},
                    {label:"Avg Risk Score",  value:`${stats?.avg_risk_score?.toFixed(1)||18.4}%`, color:"#0A84FF"},
                    {label:"Detection Rate",  value:"95.76%",color:"#30D158"},
                  ].map(({label,value,color})=>(
                    <div key={label} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"7px 0",borderBottom:`1px solid ${isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.06)"}`}}>
                      <span style={{fontSize:12,color:muted}}>{label}</span>
                      <span style={{fontSize:13,fontWeight:700,color,fontFamily:"'DM Mono',monospace"}}>{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Model comparison chart */}
            <div className="card" style={{padding:"18px 20px"}}>
              <div style={{fontSize:14,fontWeight:700,marginBottom:4,color:txt}}>📈 Model Comparison</div>
              <div style={{fontSize:11,color:muted,marginBottom:16}}>Accuracy, Precision & Recall across all models</div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={modelData} margin={{top:0,right:0,left:-20,bottom:0}}>
                  <CartesianGrid strokeDasharray="3 3" stroke={isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.06)"}/>
                  <XAxis dataKey="model" tick={{fill:muted,fontSize:11}} axisLine={false} tickLine={false}/>
                  <YAxis tick={{fill:muted,fontSize:10}} axisLine={false} tickLine={false} domain={[0,100]}/>
                  <Tooltip content={<ChartTooltip isDark={isDark}/>} formatter={(v)=>`${v}%`}/>
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{fontSize:11,color:muted}}/>
                  <Bar dataKey="accuracy"  fill="#30D158" radius={[4,4,0,0]} name="Accuracy"/>
                  <Bar dataKey="precision" fill="#0A84FF" radius={[4,4,0,0]} name="Precision"/>
                  <Bar dataKey="recall"    fill="#BF5AF2" radius={[4,4,0,0]} name="Recall"/>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* ── ALERTS ── */}
        {activeTab==="alerts"&&(
          <div className="tab-content">
            <div style={{marginBottom:20,display:"flex",justifyContent:"space-between",alignItems:"flex-end",flexWrap:"wrap",gap:10}}>
              <div>
                <h2 style={{fontSize:"clamp(18px,4vw,22px)",fontWeight:800,color:txt}}>🚨 Fraud Alerts</h2>
                <p style={{fontSize:12,color:muted,marginTop:4}}>Click any row for full report + PDF</p>
              </div>
              <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"}}>
                {[{l:"CRITICAL",c:stats?.critical_count},{l:"HIGH",c:stats?.high_count}].map(({l,c})=>(
                  <div key={l} style={{padding:"4px 12px",borderRadius:20,fontSize:11,fontWeight:700,background:riskBg(l,isDark),color:riskColor(l,isDark),border:`1px solid ${riskColor(l,isDark)}35`}}>{l}: {c}</div>
                ))}
                <button onClick={()=>window.open(`${API}/api/report/bulk/alerts?risk_level=CRITICAL`,"_blank")}
                  style={{padding:"5px 12px",borderRadius:10,background:"linear-gradient(135deg,#FF3B5C,#FF6B00)",border:"none",color:"white",fontSize:11,cursor:"pointer",fontFamily:"inherit",fontWeight:600,transition:"transform 0.2s,box-shadow 0.2s"}}
                  onMouseEnter={e=>{e.currentTarget.style.transform="translateY(-1px)";e.currentTarget.style.boxShadow="0 6px 20px rgba(255,59,92,0.4)";}}
                  onMouseLeave={e=>{e.currentTarget.style.transform="";e.currentTarget.style.boxShadow="";}}>
                  📄 Export All PDF
                </button>
              </div>
            </div>
            {alertsLoading?(
              <div style={{textAlign:"center",padding:60,color:muted}}>
                <div style={{fontSize:32,animation:"spin 0.8s linear infinite",display:"inline-block",marginBottom:12}}>⟳</div>
                <div>Loading alerts...</div>
              </div>
            ):(
              <div className="card" style={{overflow:"hidden"}}>
                <div className="alert-table" style={{display:"grid",gridTemplateColumns:"1fr 100px 80px 80px 80px 80px",padding:"11px 20px",borderBottom:`1px solid ${cardBord}`,fontSize:10,color:muted,fontWeight:700,letterSpacing:"0.06em"}}>
                  <span>GSTIN / TYPE</span>
                  <span style={{textAlign:"center"}}>SCORE</span>
                  <span style={{textAlign:"center"}} className="hide-mobile">XGB</span>
                  <span style={{textAlign:"center"}} className="hide-mobile">ANOMALY</span>
                  <span style={{textAlign:"center"}} className="hide-mobile">GRAPH</span>
                  <span style={{textAlign:"center"}}>RISK</span>
                </div>
                {(alerts.length?alerts:MOCK.topRisks).map((a,i)=>{
                  const color=riskColor(a.risk_level,isDark);
                  return(
                    <div key={a.gstin} className="row-hover alert-table"
                      onClick={()=>setSelectedGstin(a.gstin)}
                      style={{display:"grid",gridTemplateColumns:"1fr 100px 80px 80px 80px 80px",padding:"12px 20px",alignItems:"center",borderBottom:`1px solid ${isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.05)"}`,animation:`slideUp 0.3s ease ${i*30}ms both`}}>
                      <div>
                        <div style={{fontSize:12,fontFamily:"'DM Mono',monospace",fontWeight:600,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",color:txt}}>{a.gstin}</div>
                        <div style={{fontSize:11,color:muted,marginTop:2,display:"flex",gap:8,flexWrap:"wrap"}}>
                          <span>{fraudIcon(a.fraud_type)} {a.fraud_type?.replace(/_/g," ")}</span>
                          {a.in_circular_ring&&<span style={{color:"#FF8C00"}}>🔄 circular ring</span>}
                          {a.models_agreeing>=3&&<span style={{color:"#BF5AF2"}}>• {a.models_agreeing} models agree</span>}
                        </div>
                      </div>
                      <div style={{textAlign:"center",fontSize:14,fontWeight:800,color,fontFamily:"'DM Mono',monospace"}}>{a.ensemble_score?.toFixed(1)}%</div>
                      <div className="hide-mobile" style={{textAlign:"center",fontSize:12,color:"#0A84FF",fontFamily:"'DM Mono',monospace"}}>{a.xgb_score?.toFixed(0)}%</div>
                      <div className="hide-mobile" style={{textAlign:"center",fontSize:12,color:"#BF5AF2",fontFamily:"'DM Mono',monospace"}}>{a.anomaly_score?.toFixed(0)}%</div>
                      <div className="hide-mobile" style={{textAlign:"center",fontSize:12,color:"#FF9F0A",fontFamily:"'DM Mono',monospace"}}>{a.graph_risk_score?.toFixed(0)}%</div>
                      <div style={{textAlign:"center"}}>
                        <span style={{padding:"3px 8px",borderRadius:20,fontSize:10,fontWeight:700,background:riskBg(a.risk_level,isDark),color,border:`1px solid ${color}35`}}>{a.risk_level}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ── SEARCH ── */}
        {activeTab==="search"&&(
          <div className="tab-content">
            <div style={{maxWidth:600,margin:"0 auto"}}>
              <div style={{textAlign:"center",marginBottom:32}}>
                <div style={{fontSize:48,marginBottom:14,animation:"float 3s ease-in-out infinite",display:"inline-block"}}>🔍</div>
                <h2 style={{fontSize:"clamp(20px,4vw,26px)",fontWeight:800,color:txt}}>GSTIN Lookup</h2>
                <p style={{fontSize:13,color:muted,marginTop:6}}>Search any GSTIN for instant AI fraud analysis + PDF report</p>
              </div>
              <div style={{position:"relative",marginBottom:24}}>
                <input className="search-inp" value={search} onChange={e=>setSearch(e.target.value)}
                  placeholder="Enter GSTIN (e.g. 27VVZYP7446E1ZH)..."
                  style={{width:"100%",padding:"16px 52px 16px 20px",fontSize:14,background:isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.04)",border:`1px solid ${isDark?"rgba(255,255,255,0.12)":"rgba(0,0,0,0.12)"}`,borderRadius:16,color:txt,fontFamily:"'DM Mono',monospace",transition:"all 0.2s"}}/>
                <div style={{position:"absolute",right:14,top:"50%",transform:"translateY(-50%)",fontSize:16}}>
                  {searching?<span style={{animation:"spin 0.8s linear infinite",display:"inline-block"}}>⟳</span>:"🔍"}
                </div>
              </div>
              {searchResults.length>0&&(
                <div className="card" style={{overflow:"hidden"}}>
                  {searchResults.map((r,i)=>{
                    const color=riskColor(r.risk_level,isDark);
                    return(
                      <div key={r.gstin} className="row-hover" onClick={()=>setSelectedGstin(r.gstin)}
                        style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"14px 20px",borderBottom:`1px solid ${isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.05)"}`,animation:`slideUp 0.3s ease ${i*50}ms both`,gap:12}}>
                        <div style={{minWidth:0}}>
                          <div style={{fontSize:13,fontFamily:"'DM Mono',monospace",fontWeight:600,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",color:txt}}>{r.gstin}</div>
                          <div style={{fontSize:11,color:muted,marginTop:3}}>{fraudIcon(r.fraud_type)} {r.fraud_type?.replace(/_/g," ")}</div>
                        </div>
                        <div style={{display:"flex",alignItems:"center",gap:10,flexShrink:0}}>
                          <span style={{fontSize:18,fontWeight:800,color,fontFamily:"'DM Mono',monospace"}}>{r.ensemble_score?.toFixed(1)}%</span>
                          <span style={{padding:"4px 10px",borderRadius:20,fontSize:11,fontWeight:700,background:riskBg(r.risk_level,isDark),color,border:`1px solid ${color}35`}}>{r.risk_level}</span>
                          <span style={{color:muted}}>→</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              {search.length>=3&&searchResults.length===0&&!searching&&(
                <div style={{textAlign:"center",padding:40,color:muted}}>
                  <div style={{fontSize:36,marginBottom:10}}>🔎</div>
                  <div>No results for "{search}"</div>
                </div>
              )}
              {!search&&(
                <div style={{textAlign:"center",paddingTop:12}}>
                  <div style={{fontSize:12,color:muted,marginBottom:12}}>Try these high-risk GSTINs:</div>
                  <div style={{display:"flex",gap:8,justifyContent:"center",flexWrap:"wrap"}}>
                    {["27VVZYP","12XUUHW","17WTALS","09ZKRQH"].map(hint=>(
                      <button key={hint} className="hint-btn" onClick={()=>setSearch(hint)}
                        style={{padding:"8px 14px",borderRadius:20,fontSize:12,background:isDark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.05)",border:`1px solid ${isDark?"rgba(255,255,255,0.1)":"rgba(0,0,0,0.1)"}`,color:muted,cursor:"pointer",fontFamily:"'DM Mono',monospace",transition:"all 0.2s"}}>
                        {hint}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── BULK UPLOAD ── */}
        {activeTab==="bulk"&&(
          <div className="tab-content">
            <BulkUpload token={token}/>
          </div>
        )}
        {activeTab==="heatmap"&&(
          <div className="tab-content">
            <IndiaHeatmap token={token} isDark={isDark}/>
          </div>
        )}
        {activeTab==="users"&&(
          <div className="tab-content">
            <UserManagement token={token} currentUser={user} isDark={isDark}/>
          </div>
        )}
        {activeTab==="analytics"&&(
          <div className="tab-content">
            <Analytics token={token} isDark={isDark}/>
          </div>
        )}
        
      </main>

      {selectedGstin&&<GSTINModal gstin={selectedGstin} onClose={()=>setSelectedGstin(null)} token={token} isDark={isDark}/>}
    </div>
  );
}
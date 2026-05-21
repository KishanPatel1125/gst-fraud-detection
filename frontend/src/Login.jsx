import { useState } from "react";

const API = "https://gst-fraud-detection-production.up.railway.app";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");
  const [showPass, setShowPass] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const form = new FormData();
      form.append("username", username);
      form.append("password", password);

      const res  = await fetch(`${API}/api/auth/login`, {
        method: "POST", body: form,
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Invalid credentials");
        return;
      }

      // Save token and user
      localStorage.setItem("gst_token", data.access_token);
      localStorage.setItem("gst_user",  JSON.stringify(data.user));
      onLogin(data.user, data.access_token);

    } catch {
      setError("Cannot connect to server. Check API.");
    } finally {
      setLoading(false);
    }
  };

  const quickLogin = (u, p) => { setUsername(u); setPassword(p); };

  return (
    <div style={{ minHeight:"100vh", background:"#0A0A0B", display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Sora',sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        @keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
        @keyframes fadeIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes glow{0%,100%{box-shadow:0 0 20px rgba(255,59,92,0.3)}50%{box-shadow:0 0 40px rgba(255,59,92,0.5)}}
        .inp{width:100%;padding:14px 16px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:12px;color:#F5F5F7;font-family:inherit;font-size:14px;transition:all 0.2s;outline:none}
        .inp:focus{border-color:rgba(255,59,92,0.6);box-shadow:0 0 0 3px rgba(255,59,92,0.1);background:rgba(255,255,255,0.07)}
        .inp::placeholder{color:#8E8E93}
        .btn-login{width:100%;padding:15px;background:linear-gradient(135deg,#FF3B5C,#FF6B00);border:none;border-radius:12px;color:white;font-family:inherit;font-size:15px;font-weight:700;cursor:pointer;transition:all 0.2s;letter-spacing:0.02em}
        .btn-login:hover{transform:translateY(-1px);box-shadow:0 8px 30px rgba(255,59,92,0.4)}
        .btn-login:active{transform:translateY(0)}
        .btn-login:disabled{opacity:0.6;cursor:not-allowed;transform:none}
        .quick-btn{padding:8px 14px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.04);color:#8E8E93;font-family:inherit;font-size:12px;cursor:pointer;transition:all 0.2s;flex:1}
        .quick-btn:hover{background:rgba(255,255,255,0.08);color:#F5F5F7;border-color:rgba(255,255,255,0.2)}
        .eye-btn{position:absolute;right:14px;top:50%;transform:translateY(-50%);background:none;border:none;color:#8E8E93;cursor:pointer;font-size:18px;padding:4px}
      `}</style>

      {/* Background glow */}
      <div style={{ position:"fixed", top:"20%", left:"30%", width:400, height:400, borderRadius:"50%", background:"rgba(255,59,92,0.06)", filter:"blur(80px)", pointerEvents:"none" }} />
      <div style={{ position:"fixed", bottom:"20%", right:"25%", width:300, height:300, borderRadius:"50%", background:"rgba(255,140,0,0.05)", filter:"blur(60px)", pointerEvents:"none" }} />

      <div style={{ width:"min(440px,92vw)", animation:"fadeIn 0.5s ease" }}>

        {/* Logo */}
        <div style={{ textAlign:"center", marginBottom:32 }}>
          <div style={{ width:64, height:64, borderRadius:20, background:"linear-gradient(135deg,#FF3B5C,#FF6B00)", display:"inline-flex", alignItems:"center", justifyContent:"center", fontSize:30, marginBottom:16, animation:"float 3s ease-in-out infinite", boxShadow:"0 8px 32px rgba(255,59,92,0.4)" }}>
            🛡️
          </div>
          <h1 style={{ fontSize:24, fontWeight:800, color:"#F5F5F7", letterSpacing:"-0.02em" }}>GST FraudShield</h1>
          <p style={{ fontSize:13, color:"#8E8E93", marginTop:6, letterSpacing:"0.04em" }}>AI-POWERED TAX INTELLIGENCE</p>
        </div>

        {/* Login card */}
        <div style={{ background:"rgba(255,255,255,0.03)", border:"1px solid rgba(255,255,255,0.08)", borderRadius:24, padding:32, backdropFilter:"blur(20px)" }}>
          <h2 style={{ fontSize:18, fontWeight:700, color:"#F5F5F7", marginBottom:6 }}>Sign In</h2>
          <p style={{ fontSize:13, color:"#8E8E93", marginBottom:24 }}>Access the fraud detection dashboard</p>

          {error && (
            <div style={{ background:"rgba(255,59,92,0.1)", border:"1px solid rgba(255,59,92,0.3)", borderRadius:10, padding:"10px 14px", marginBottom:16, fontSize:13, color:"#FF3B5C" }}>
              ⚠️ {error}
            </div>
          )}

          <form onSubmit={handleLogin}>
            <div style={{ marginBottom:14 }}>
              <label style={{ fontSize:12, color:"#8E8E93", display:"block", marginBottom:6, fontWeight:500 }}>USERNAME</label>
              <input className="inp" type="text" placeholder="Enter username" value={username} onChange={e=>setUsername(e.target.value)} required autoComplete="username" />
            </div>

            <div style={{ marginBottom:24, position:"relative" }}>
              <label style={{ fontSize:12, color:"#8E8E93", display:"block", marginBottom:6, fontWeight:500 }}>PASSWORD</label>
              <div style={{ position:"relative" }}>
                <input className="inp" type={showPass?"text":"password"} placeholder="Enter password" value={password} onChange={e=>setPassword(e.target.value)} required style={{ paddingRight:44 }} autoComplete="current-password" />
                <button type="button" className="eye-btn" onClick={()=>setShowPass(!showPass)}>
                  {showPass ? "🙈" : "👁️"}
                </button>
              </div>
            </div>

            <button type="submit" className="btn-login" disabled={loading}>
              {loading ? (
                <span style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:10 }}>
                  <span style={{ width:16, height:16, border:"2px solid rgba(255,255,255,0.3)", borderTop:"2px solid white", borderRadius:"50%", animation:"spin 0.8s linear infinite", display:"inline-block" }} />
                  Signing in...
                </span>
              ) : "Sign In →"}
            </button>
          </form>

          {/* Quick login */}
          <div style={{ marginTop:24 }}>
            <div style={{ fontSize:11, color:"#8E8E93", textAlign:"center", marginBottom:10, letterSpacing:"0.04em" }}>QUICK LOGIN (DEMO)</div>
            <div style={{ display:"flex", gap:8 }}>
              <button className="quick-btn" onClick={()=>quickLogin("admin","secret")}>
                👑 Admin
              </button>
              <button className="quick-btn" onClick={()=>quickLogin("officer","secret")}>
                🏛️ Officer
              </button>
              <button className="quick-btn" onClick={()=>quickLogin("ca","secret")}>
                📊 CA
              </button>
            </div>
            <div style={{ fontSize:11, color:"#8E8E93", textAlign:"center", marginTop:8 }}>
              All demo accounts use password: <span style={{ fontFamily:"'DM Mono',monospace", color:"#F5F5F7" }}>secret</span>
            </div>
          </div>
        </div>

        {/* Role info */}
        <div style={{ marginTop:16, display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8 }}>
          {[
            { role:"Admin",   icon:"👑", desc:"Full access",       color:"#FF3B5C" },
            { role:"Officer", icon:"🏛️", desc:"View + investigate", color:"#FF8C00" },
            { role:"CA",      icon:"📊", desc:"Reports only",       color:"#30D158" },
          ].map(({role,icon,desc,color})=>(
            <div key={role} style={{ background:"rgba(255,255,255,0.02)", border:"1px solid rgba(255,255,255,0.06)", borderRadius:12, padding:"10px 12px", textAlign:"center" }}>
              <div style={{ fontSize:18, marginBottom:4 }}>{icon}</div>
              <div style={{ fontSize:11, fontWeight:700, color, marginBottom:2 }}>{role}</div>
              <div style={{ fontSize:10, color:"#8E8E93" }}>{desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
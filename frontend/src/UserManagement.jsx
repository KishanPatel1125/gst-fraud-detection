// UserManagement.jsx
// Admin-only user management dashboard
// Add/remove users, change passwords, view audit log

import { useState, useEffect } from "react";

const API = "https://gst-fraud-detection-production.up.railway.app";

const roleIcon  = r => ({ admin:"👑", officer:"🏛️", ca:"📊" }[r] || "👤");
const roleColor = r => ({ admin:"#FF3B5C", officer:"#FF8C00", ca:"#30D158" }[r] || "#8E8E93");
const roleBg    = r => ({ admin:"rgba(255,59,92,0.12)", officer:"rgba(255,140,0,0.12)", ca:"rgba(48,209,88,0.12)" }[r] || "rgba(142,142,147,0.12)");

export default function UserManagement({ token, currentUser, isDark = true }) {
  const [users,        setUsers]        = useState([]);
  const [auditLogs,    setAuditLogs]    = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [activeSection,setActiveSection]= useState("users");
  const [showAddForm,  setShowAddForm]  = useState(false);
  const [showPassForm, setShowPassForm] = useState(null);
  const [error,        setError]        = useState("");
  const [success,      setSuccess]      = useState("");

  // ── Form states ──
  const [newUser, setNewUser] = useState({
    username:"", password:"", full_name:"", email:"", role:"officer"
  });
  const [passData, setPassData] = useState({
    username:"", new_password:""
  });

  const txt    = isDark ? "#F5F5F7" : "#111";
  const muted  = isDark ? "#8E8E93" : "#666";
  const cardBg = isDark ? "rgba(255,255,255,0.025)" : "rgba(255,255,255,0.9)";
  const cardBd = isDark ? "rgba(255,255,255,0.07)"  : "rgba(0,0,0,0.08)";
  const surfBg = isDark ? "rgba(255,255,255,0.04)"  : "rgba(0,0,0,0.04)";
  const inpBg  = isDark ? "rgba(255,255,255,0.05)"  : "rgba(0,0,0,0.04)";
  const inpBd  = isDark ? "rgba(255,255,255,0.1)"   : "rgba(0,0,0,0.12)";

  const authHeaders = {
    "Authorization": `Bearer ${token}`,
    "Content-Type":  "application/json",
  };

  // ── Load users ──
  const loadUsers = async () => {
    setLoading(true);
    try {
      const res  = await fetch(`${API}/api/users`, { headers: authHeaders });
      const data = await res.json();
      if (res.ok) setUsers(data.users || []);
      else setError(data.detail || "Failed to load users");
    } catch {
      setError("Cannot connect to API");
    } finally {
      setLoading(false);
    }
  };

  // ── Load audit log ──
  const loadAuditLog = async () => {
    try {
      const res  = await fetch(`${API}/api/audit-log?limit=50`, { headers: authHeaders });
      const data = await res.json();
      if (res.ok) setAuditLogs(data.logs || []);
    } catch {}
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (currentUser?.role !== "admin") return;
    loadUsers();
    loadAuditLog();
  }, []);

  // ── Show message ──
  const showMsg = (msg, isError = false) => {
    if (isError) { setError(msg); setTimeout(() => setError(""), 4000); }
    else { setSuccess(msg); setTimeout(() => setSuccess(""), 4000); }
  };

  // ── Add user ──
  const handleAddUser = async (e) => {
    e.preventDefault();
    if (!newUser.username || !newUser.password || !newUser.full_name) {
      showMsg("All fields required", true); return;
    }
    try {
      const res  = await fetch(`${API}/api/users`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify(newUser),
      });
      const data = await res.json();
      if (res.ok) {
        showMsg(`✅ User "${newUser.username}" created successfully!`);
        setNewUser({ username:"", password:"", full_name:"", email:"", role:"officer" });
        setShowAddForm(false);
        loadUsers();
      } else {
        showMsg(data.detail || "Failed to create user", true);
      }
    } catch {
      showMsg("Cannot connect to API", true);
    }
  };

  // ── Change password ──
  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (!passData.new_password || passData.new_password.length < 4) {
      showMsg("Password must be at least 4 characters", true); return;
    }
    try {
      const res  = await fetch(`${API}/api/users/password`, {
        method: "PATCH",
        headers: authHeaders,
        body: JSON.stringify(passData),
      });
      const data = await res.json();
      if (res.ok) {
        showMsg(`✅ Password updated for "${passData.username}"`);
        setShowPassForm(null);
        setPassData({ username:"", new_password:"" });
      } else {
        showMsg(data.detail || "Failed to update password", true);
      }
    } catch {
      showMsg("Cannot connect to API", true);
    }
  };

  // ── Toggle user ──
  const handleToggleUser = async (username, isDisabled) => {
    try {
      const res  = await fetch(`${API}/api/users/${username}/toggle`, {
        method: "PATCH",
        headers: authHeaders,
      });
      const data = await res.json();
      if (res.ok) {
        showMsg(`✅ User "${username}" ${data.disabled ? "disabled" : "enabled"}`);
        loadUsers();
      } else {
        showMsg(data.detail || "Failed", true);
      }
    } catch {
      showMsg("Cannot connect to API", true);
    }
  };

  // ── Delete user ──
  const handleDeleteUser = async (username) => {
    if (!window.confirm(`Delete user "${username}"? This cannot be undone.`)) return;
    try {
      const res  = await fetch(`${API}/api/users/${username}`, {
        method: "DELETE",
        headers: authHeaders,
      });
      const data = await res.json();
      if (res.ok) {
        showMsg(`✅ User "${username}" deleted`);
        loadUsers();
      } else {
        showMsg(data.detail || "Failed to delete", true);
      }
    } catch {
      showMsg("Cannot connect to API", true);
    }
  };

  // ── Input style ──
  const inpStyle = {
    width:"100%", padding:"12px 14px",
    background:inpBg, border:`1px solid ${inpBd}`,
    borderRadius:10, color:txt,
    fontFamily:"inherit", fontSize:13,
    outline:"none", transition:"all 0.2s",
  };

  // ── Not admin ──
  if (currentUser?.role !== "admin") {
    return (
      <div style={{ textAlign:"center", padding:80 }}>
        <div style={{ fontSize:52, marginBottom:16 }}>🔒</div>
        <h2 style={{ fontSize:20, fontWeight:700, color:txt, marginBottom:8 }}>Admin Only</h2>
        <p style={{ fontSize:14, color:muted }}>User management requires admin access.</p>
        <p style={{ fontSize:13, color:muted, marginTop:6 }}>Login with the admin account to access this section.</p>
      </div>
    );
  }

  return (
    <div style={{ fontFamily:"'Sora',sans-serif" }}>

      {/* Header */}
      <div style={{ marginBottom:24, display:"flex", justifyContent:"space-between", alignItems:"flex-end", flexWrap:"wrap", gap:12 }}>
        <div>
          <h2 style={{ fontSize:22, fontWeight:800, color:txt }}>👥 User Management</h2>
          <p style={{ fontSize:13, color:muted, marginTop:4 }}>Manage system users and access control</p>
        </div>
        <button onClick={() => setShowAddForm(true)} style={{
          padding:"10px 20px", borderRadius:12,
          background:"linear-gradient(135deg,#FF3B5C,#FF6B00)",
          border:"none", color:"white", fontSize:13,
          cursor:"pointer", fontFamily:"inherit", fontWeight:600,
          boxShadow:"0 4px 16px rgba(255,59,92,0.3)",
          transition:"transform 0.2s,box-shadow 0.2s",
        }}
          onMouseEnter={e=>{e.currentTarget.style.transform="translateY(-2px)";e.currentTarget.style.boxShadow="0 8px 24px rgba(255,59,92,0.4)";}}
          onMouseLeave={e=>{e.currentTarget.style.transform="";e.currentTarget.style.boxShadow="0 4px 16px rgba(255,59,92,0.3)";}}>
          + Add New User
        </button>
      </div>

      {/* Messages */}
      {error && (
        <div style={{ background:"rgba(255,59,92,0.1)", border:"1px solid rgba(255,59,92,0.3)", borderRadius:12, padding:"10px 16px", marginBottom:16, fontSize:13, color:"#FF3B5C" }}>
          ⚠️ {error}
        </div>
      )}
      {success && (
        <div style={{ background:"rgba(48,209,88,0.1)", border:"1px solid rgba(48,209,88,0.3)", borderRadius:12, padding:"10px 16px", marginBottom:16, fontSize:13, color:"#30D158" }}>
          {success}
        </div>
      )}

      {/* Section tabs */}
      <div style={{ display:"flex", gap:8, marginBottom:20 }}>
        {[["users","👥 Users"],["audit","📋 Audit Log"]].map(([id,label])=>(
          <button key={id} onClick={()=>setActiveSection(id)} style={{
            padding:"8px 18px", borderRadius:10, border:`1px solid ${cardBd}`,
            background: activeSection===id ? "rgba(255,59,92,0.12)" : surfBg,
            color: activeSection===id ? "#FF3B5C" : muted,
            fontSize:13, fontWeight:500, cursor:"pointer",
            fontFamily:"inherit", transition:"all 0.2s",
          }}>{label}</button>
        ))}
      </div>

      {/* ── USERS SECTION ── */}
      {activeSection==="users" && (
        <div>
          {/* Stats */}
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:20 }}>
            {[
              { label:"Total Users",   value:users.length,                          color:"#0A84FF", icon:"👥" },
              { label:"Active Users",  value:users.filter(u=>!u.disabled).length,   color:"#30D158", icon:"✅" },
              { label:"Disabled",      value:users.filter(u=>u.disabled).length,    color:"#FF3B5C", icon:"🚫" },
            ].map(({ label, value, color, icon }) => (
              <div key={label} style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:16, padding:"16px 18px" }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <div>
                    <div style={{ fontSize:11, color:muted, marginBottom:4 }}>{label}</div>
                    <div style={{ fontSize:26, fontWeight:800, color, fontFamily:"'DM Mono',monospace" }}>{value}</div>
                  </div>
                  <div style={{ fontSize:24 }}>{icon}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Users table */}
          {loading ? (
            <div style={{ textAlign:"center", padding:60, color:muted }}>
              <div style={{ fontSize:32, animation:"spin 0.8s linear infinite", display:"inline-block", marginBottom:12 }}>⟳</div>
              <div>Loading users...</div>
            </div>
          ) : (
            <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, overflow:"hidden" }}>
              {/* Table header */}
              <div style={{ display:"grid", gridTemplateColumns:"1fr 140px 120px 160px", padding:"12px 20px", borderBottom:`1px solid ${cardBd}`, fontSize:10, color:muted, fontWeight:700, letterSpacing:"0.06em" }}>
                <span>USER</span>
                <span style={{textAlign:"center"}}>ROLE</span>
                <span style={{textAlign:"center"}}>STATUS</span>
                <span style={{textAlign:"center"}}>ACTIONS</span>
              </div>

              {users.map((u, i) => (
                <div key={u.username} style={{
                  display:"grid", gridTemplateColumns:"1fr 140px 120px 160px",
                  padding:"14px 20px", alignItems:"center",
                  borderBottom:`1px solid ${isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.05)"}`,
                  background: u.disabled ? (isDark?"rgba(255,255,255,0.01)":"rgba(0,0,0,0.02)") : "transparent",
                  opacity: u.disabled ? 0.6 : 1,
                  transition:"background 0.2s",
                }}>
                  {/* User info */}
                  <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                    <div style={{
                      width:40, height:40, borderRadius:13,
                      background:`linear-gradient(135deg,${roleColor(u.role)}33,${roleColor(u.role)}11)`,
                      border:`1px solid ${roleColor(u.role)}44`,
                      display:"flex", alignItems:"center", justifyContent:"center",
                      fontSize:20, flexShrink:0,
                    }}>
                      {roleIcon(u.role)}
                    </div>
                    <div>
                      <div style={{ fontSize:13, fontWeight:600, color:txt }}>{u.full_name}</div>
                      <div style={{ fontSize:11, color:muted, marginTop:2, fontFamily:"'DM Mono',monospace" }}>@{u.username}</div>
                      {u.email && <div style={{ fontSize:11, color:muted, marginTop:1 }}>{u.email}</div>}
                    </div>
                    {u.username === currentUser?.username && (
                      <span style={{ padding:"2px 8px", borderRadius:20, fontSize:10, background:"rgba(10,132,255,0.12)", color:"#0A84FF", border:"1px solid rgba(10,132,255,0.2)", fontWeight:600 }}>You</span>
                    )}
                  </div>

                  {/* Role */}
                  <div style={{ textAlign:"center" }}>
                    <span style={{ padding:"4px 12px", borderRadius:20, fontSize:11, fontWeight:700, background:roleBg(u.role), color:roleColor(u.role), border:`1px solid ${roleColor(u.role)}35`, textTransform:"capitalize" }}>
                      {roleIcon(u.role)} {u.role}
                    </span>
                  </div>

                  {/* Status */}
                  <div style={{ textAlign:"center" }}>
                    <span style={{
                      padding:"4px 12px", borderRadius:20, fontSize:11, fontWeight:600,
                      background: u.disabled ? "rgba(255,59,92,0.1)" : "rgba(48,209,88,0.1)",
                      color: u.disabled ? "#FF3B5C" : "#30D158",
                      border: `1px solid ${u.disabled?"rgba(255,59,92,0.2)":"rgba(48,209,88,0.2)"}`,
                    }}>
                      {u.disabled ? "🚫 Disabled" : "✅ Active"}
                    </span>
                  </div>

                  {/* Actions */}
                  <div style={{ display:"flex", gap:6, justifyContent:"center", flexWrap:"wrap" }}>
                    {/* Change password */}
                    <button onClick={() => { setShowPassForm(u.username); setPassData({ username:u.username, new_password:"" }); }}
                      title="Change Password"
                      style={{ padding:"5px 10px", borderRadius:8, border:`1px solid ${cardBd}`, background:surfBg, color:muted, fontSize:12, cursor:"pointer", fontFamily:"inherit", transition:"all 0.2s" }}
                      onMouseEnter={e=>{e.currentTarget.style.color="#0A84FF";e.currentTarget.style.borderColor="#0A84FF44";}}
                      onMouseLeave={e=>{e.currentTarget.style.color=muted;e.currentTarget.style.borderColor=cardBd;}}>
                      🔑
                    </button>

                    {/* Toggle enable/disable */}
                    {u.username !== currentUser?.username && (
                      <button onClick={() => handleToggleUser(u.username, u.disabled)}
                        title={u.disabled ? "Enable User" : "Disable User"}
                        style={{ padding:"5px 10px", borderRadius:8, border:`1px solid ${cardBd}`, background:surfBg, color:muted, fontSize:12, cursor:"pointer", fontFamily:"inherit", transition:"all 0.2s" }}
                        onMouseEnter={e=>{e.currentTarget.style.color=u.disabled?"#30D158":"#FFD60A";e.currentTarget.style.borderColor=u.disabled?"#30D15844":"#FFD60A44";}}
                        onMouseLeave={e=>{e.currentTarget.style.color=muted;e.currentTarget.style.borderColor=cardBd;}}>
                        {u.disabled ? "✅" : "⏸️"}
                      </button>
                    )}

                    {/* Delete */}
                    {u.username !== currentUser?.username && (
                      <button onClick={() => handleDeleteUser(u.username)}
                        title="Delete User"
                        style={{ padding:"5px 10px", borderRadius:8, border:`1px solid ${cardBd}`, background:surfBg, color:muted, fontSize:12, cursor:"pointer", fontFamily:"inherit", transition:"all 0.2s" }}
                        onMouseEnter={e=>{e.currentTarget.style.color="#FF3B5C";e.currentTarget.style.borderColor="rgba(255,59,92,0.4)";e.currentTarget.style.background="rgba(255,59,92,0.08)";}}
                        onMouseLeave={e=>{e.currentTarget.style.color=muted;e.currentTarget.style.borderColor=cardBd;e.currentTarget.style.background=surfBg;}}>
                        🗑️
                      </button>
                    )}
                  </div>
                </div>
              ))}

              {users.length === 0 && !loading && (
                <div style={{ textAlign:"center", padding:40, color:muted }}>
                  <div style={{ fontSize:36, marginBottom:12 }}>👥</div>
                  <div>No users found</div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── AUDIT LOG SECTION ── */}
      {activeSection==="audit" && (
        <div>
          <div style={{ background:cardBg, border:`1px solid ${cardBd}`, borderRadius:20, overflow:"hidden" }}>
            <div style={{ padding:"16px 20px", borderBottom:`1px solid ${cardBd}`, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <div style={{ fontSize:14, fontWeight:700, color:txt }}>📋 System Audit Log</div>
              <button onClick={loadAuditLog} style={{ fontSize:12, color:muted, background:surfBg, border:`1px solid ${cardBd}`, borderRadius:8, padding:"4px 12px", cursor:"pointer", fontFamily:"inherit" }}>
                🔄 Refresh
              </button>
            </div>

            <div style={{ display:"grid", gridTemplateColumns:"140px 1fr 120px 160px", padding:"11px 20px", borderBottom:`1px solid ${cardBd}`, fontSize:10, color:muted, fontWeight:700, letterSpacing:"0.06em" }}>
              <span>TIME</span>
              <span>ACTION / DETAILS</span>
              <span style={{textAlign:"center"}}>GSTIN</span>
              <span style={{textAlign:"center"}}>USER</span>
            </div>

            {auditLogs.length > 0 ? auditLogs.map((log, i) => (
              <div key={log.id} style={{
                display:"grid", gridTemplateColumns:"140px 1fr 120px 160px",
                padding:"12px 20px", alignItems:"center",
                borderBottom:`1px solid ${isDark?"rgba(255,255,255,0.04)":"rgba(0,0,0,0.05)"}`,
                animation:`slideUp 0.3s ease ${i*20}ms both`,
              }}>
                <div style={{ fontSize:11, color:muted, fontFamily:"'DM Mono',monospace" }}>
                  {log.created_at ? new Date(log.created_at).toLocaleString("en-IN",{ month:"short", day:"2-digit", hour:"2-digit", minute:"2-digit" }) : "N/A"}
                </div>
                <div>
                  <div style={{ fontSize:12, fontWeight:600, color:txt }}>
                    {log.action?.replace(/_/g," ")}
                  </div>
                  {log.details && (
                    <div style={{ fontSize:11, color:muted, marginTop:2, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                      {log.details}
                    </div>
                  )}
                </div>
                <div style={{ textAlign:"center", fontSize:11, fontFamily:"'DM Mono',monospace", color:log.gstin?"#0A84FF":muted }}>
                  {log.gstin || "—"}
                </div>
                <div style={{ textAlign:"center", fontSize:11, color:muted }}>
                  {log.user || "system"}
                </div>
              </div>
            )) : (
              <div style={{ textAlign:"center", padding:40, color:muted }}>
                <div style={{ fontSize:36, marginBottom:12 }}>📋</div>
                <div>No audit logs found</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── ADD USER MODAL ── */}
      {showAddForm && (
        <div onClick={() => setShowAddForm(false)} style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.8)", backdropFilter:"blur(12px)", zIndex:1000, display:"flex", alignItems:"center", justifyContent:"center", padding:20 }}>
          <div onClick={e => e.stopPropagation()} style={{ background:isDark?"#141416":"#fff", border:`1px solid ${cardBd}`, borderRadius:24, padding:32, width:"min(480px,100%)", animation:"slideUp 0.3s ease" }}>
            <h3 style={{ fontSize:18, fontWeight:700, color:txt, marginBottom:6 }}>➕ Add New User</h3>
            <p style={{ fontSize:13, color:muted, marginBottom:24 }}>Create a new system user account</p>

            <form onSubmit={handleAddUser}>
              {[
                { label:"Username",  key:"username",  type:"text",     placeholder:"e.g. john_doe" },
                { label:"Full Name", key:"full_name", type:"text",     placeholder:"e.g. John Doe" },
                { label:"Email",     key:"email",     type:"email",    placeholder:"e.g. john@gst.gov.in" },
                { label:"Password",  key:"password",  type:"password", placeholder:"Min 4 characters" },
              ].map(({ label, key, type, placeholder }) => (
                <div key={key} style={{ marginBottom:14 }}>
                  <label style={{ fontSize:12, color:muted, display:"block", marginBottom:6, fontWeight:500, letterSpacing:"0.04em" }}>
                    {label.toUpperCase()}
                  </label>
                  <input
                    type={type}
                    placeholder={placeholder}
                    value={newUser[key]}
                    onChange={e => setNewUser({ ...newUser, [key]: e.target.value })}
                    required
                    style={inpStyle}
                    onFocus={e => { e.target.style.borderColor="rgba(255,59,92,0.6)"; e.target.style.boxShadow="0 0 0 3px rgba(255,59,92,0.1)"; }}
                    onBlur={e  => { e.target.style.borderColor=inpBd; e.target.style.boxShadow="none"; }}
                  />
                </div>
              ))}

              <div style={{ marginBottom:24 }}>
                <label style={{ fontSize:12, color:muted, display:"block", marginBottom:6, fontWeight:500, letterSpacing:"0.04em" }}>ROLE</label>
                <select
                  value={newUser.role}
                  onChange={e => setNewUser({ ...newUser, role: e.target.value })}
                  style={{ ...inpStyle, cursor:"pointer" }}>
                  <option value="officer">🏛️ GST Officer — View and investigate</option>
                  <option value="ca">📊 CA / Auditor — Reports only</option>
                  <option value="admin">👑 Admin — Full access</option>
                </select>
              </div>

              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
                <button type="submit" style={{ padding:13, borderRadius:12, background:"linear-gradient(135deg,#FF3B5C,#FF6B00)", border:"none", color:"white", fontSize:13, cursor:"pointer", fontFamily:"inherit", fontWeight:600 }}>
                  Create User
                </button>
                <button type="button" onClick={() => setShowAddForm(false)} style={{ padding:13, borderRadius:12, background:isDark?"rgba(255,255,255,0.06)":"rgba(0,0,0,0.06)", border:`1px solid ${cardBd}`, color:txt, fontSize:13, cursor:"pointer", fontFamily:"inherit" }}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── CHANGE PASSWORD MODAL ── */}
      {showPassForm && (
        <div onClick={() => setShowPassForm(null)} style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.8)", backdropFilter:"blur(12px)", zIndex:1000, display:"flex", alignItems:"center", justifyContent:"center", padding:20 }}>
          <div onClick={e => e.stopPropagation()} style={{ background:isDark?"#141416":"#fff", border:`1px solid ${cardBd}`, borderRadius:24, padding:32, width:"min(420px,100%)", animation:"slideUp 0.3s ease" }}>
            <h3 style={{ fontSize:18, fontWeight:700, color:txt, marginBottom:6 }}>🔑 Change Password</h3>
            <p style={{ fontSize:13, color:muted, marginBottom:24 }}>
              Updating password for: <span style={{ color:txt, fontWeight:600, fontFamily:"'DM Mono',monospace" }}>@{showPassForm}</span>
            </p>

            <form onSubmit={handleChangePassword}>
              <div style={{ marginBottom:20 }}>
                <label style={{ fontSize:12, color:muted, display:"block", marginBottom:6, fontWeight:500, letterSpacing:"0.04em" }}>NEW PASSWORD</label>
                <input
                  type="password"
                  placeholder="Enter new password (min 4 characters)"
                  value={passData.new_password}
                  onChange={e => setPassData({ ...passData, new_password: e.target.value })}
                  required
                  minLength={4}
                  style={inpStyle}
                  onFocus={e => { e.target.style.borderColor="rgba(255,59,92,0.6)"; e.target.style.boxShadow="0 0 0 3px rgba(255,59,92,0.1)"; }}
                  onBlur={e  => { e.target.style.borderColor=inpBd; e.target.style.boxShadow="none"; }}
                  autoFocus
                />
              </div>

              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
                <button type="submit" style={{ padding:13, borderRadius:12, background:"linear-gradient(135deg,#0A84FF,#0055AA)", border:"none", color:"white", fontSize:13, cursor:"pointer", fontFamily:"inherit", fontWeight:600 }}>
                  Update Password
                </button>
                <button type="button" onClick={() => setShowPassForm(null)} style={{ padding:13, borderRadius:12, background:isDark?"rgba(255,255,255,0.06)":"rgba(0,0,0,0.06)", border:`1px solid ${cardBd}`, color:txt, fontSize:13, cursor:"pointer", fontFamily:"inherit" }}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
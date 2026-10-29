import { useState, type FormEvent } from "react";
import { createFriend, createLetter } from "./api";

const scenes = [
  { value: "cat-garden", label: "Cat garden" },
  { value: "racing-night", label: "Night racing circuit" },
  { value: "comic-rooftop", label: "Comic rooftop" },
  { value: "moonlit-hills", label: "Moonlit hills" },
];

export default function AdminPanel() {
  const [friend, setFriend] = useState({ login_id: "", password: "", display_name: "", birth_month: "1", birth_day: "1", timezone: "Asia/Kolkata", scene: "moonlit-hills" });
  const [publicId, setPublicId] = useState("");
  const [year, setYear] = useState(String(new Date().getFullYear() + 1));
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [published, setPublished] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleFriend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      const result = await createFriend({
        login_id: friend.login_id.trim().toLowerCase(), password: friend.password,
        display_name: friend.display_name.trim(), birth_month: Number(friend.birth_month),
        birth_day: Number(friend.birth_day), timezone: friend.timezone,
        theme: { scene: friend.scene },
      });
      setPublicId(result.public_id);
      setMessage("Friend account created. Save the private account reference below; it is needed to attach a letter.");
      setFriend(current => ({ ...current, password: "" }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Couldn't create account."); }
    finally { setBusy(false); }
  }

  async function handleLetter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!publicId) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await createLetter(publicId, { year: Number(year), content_type: "letter", body: { title: title.trim(), text: body }, published });
      setMessage(`Letter capsule created (reference: ${result.id}). ${published ? "It is published and will remain locked until the birthday unlock time." : "It is still a draft and is not visible to the friend."}`);
      setTitle(""); setBody("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Couldn't create letter."); }
    finally { setBusy(false); }
  }

  return <section className="admin-panel" aria-labelledby="admin-heading">
    <div className="admin-heading"><div><span className="eyebrow">PRIVATE SETUP</span><h2 id="admin-heading">Savepoint workshop</h2></div><span className="admin-tag">ADMIN ONLY</span></div>
    <p className="admin-intro">Create one friend's login, choose their world, then attach a birthday letter. Passwords are never shown again after submission.</p>
    <form className="admin-form" onSubmit={handleFriend}>
      <h3>01 / Friend account</h3>
      <div className="admin-fields">
        <label>Login ID<input required minLength={3} maxLength={64} pattern="[a-z0-9_.-]+" value={friend.login_id} onChange={e=>setFriend({...friend,login_id:e.target.value})} autoComplete="off"/></label>
        <label>Temporary password<input required type="password" minLength={12} maxLength={256} value={friend.password} onChange={e=>setFriend({...friend,password:e.target.value})} autoComplete="new-password"/></label>
        <label>Display name<input required maxLength={80} value={friend.display_name} onChange={e=>setFriend({...friend,display_name:e.target.value})}/></label>
        <label>Timezone<select value={friend.timezone} onChange={e=>setFriend({...friend,timezone:e.target.value})}><option value="Asia/Kolkata">India (Asia/Kolkata)</option><option value="UTC">UTC</option><option value="Asia/Dubai">Dubai</option><option value="Europe/London">London</option><option value="America/New_York">New York</option></select></label>
        <label>Birth month<input type="number" min="1" max="12" required value={friend.birth_month} onChange={e=>setFriend({...friend,birth_month:e.target.value})}/></label>
        <label>Birth day<input type="number" min="1" max="31" required value={friend.birth_day} onChange={e=>setFriend({...friend,birth_day:e.target.value})}/></label>
        <label className="admin-wide">Personal world<select value={friend.scene} onChange={e=>setFriend({...friend,scene:e.target.value})}>{scenes.map(scene=><option key={scene.value} value={scene.value}>{scene.label}</option>)}</select></label>
      </div>
      <button className="primary admin-submit" disabled={busy}>Create friend account</button>
    </form>
    {publicId && <form className="admin-form" onSubmit={handleLetter}>
      <h3>02 / Birthday letter</h3>
      <p className="admin-id">Account reference: <code>{publicId}</code></p>
      <div className="admin-fields">
        <label>Capsule year<input type="number" min="2000" max="2200" required value={year} onChange={e=>setYear(e.target.value)}/></label>
        <label>Letter title<input required maxLength={120} value={title} onChange={e=>setTitle(e.target.value)}/></label>
        <label className="admin-wide">Letter text<textarea required minLength={1} maxLength={20000} rows={7} value={body} onChange={e=>setBody(e.target.value)} /></label>
        <label className="admin-check"><input type="checkbox" checked={published} onChange={e=>setPublished(e.target.checked)}/> Publish now (otherwise save as a private draft)</label>
      </div>
      <button className="primary admin-submit" disabled={busy}>Create birthday capsule</button>
    </form>}
    {message && <p className="admin-message" role="status">{message}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    <p className="admin-warning">Early build: this panel has no friend directory, password reset, delivery notifications, or production audit log. Keep account references and passwords private.</p>
  </section>;
}

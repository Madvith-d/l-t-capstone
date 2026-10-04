"use client";
import { FormEvent, useEffect, useState } from "react";
import { CalendarDays, LoaderCircle, Plus, Trash2 } from "lucide-react";
import { api, Plan, Subject } from "@/lib/api";

type DraftSubject = Subject & { key: string };
const newSubject = (): DraftSubject => ({ key: crypto.randomUUID(), name: "", topics: [], difficulty: 3 });
const initialSubject: DraftSubject = { key: "initial-subject", name: "", topics: [], difficulty: 3 };

export function PlannerWorkspace() {
  const [plan, setPlan] = useState<Plan>();
  const [subjects, setSubjects] = useState<DraftSubject[]>([initialSubject]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [instruction, setInstruction] = useState("");

  useEffect(() => {
    api.plans().then((plans) => setPlan(plans[0])).catch((reason) => setError(reason instanceof Error ? reason.message : "Plans could not be loaded.")).finally(() => setLoading(false));
  }, []);

  function updateSubject(key: string, patch: Partial<DraftSubject>) {
    setSubjects((items) => items.map((item) => item.key === key ? { ...item, ...patch } : item));
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError(""); const data = new FormData(event.currentTarget);
    try {
      const payloadSubjects = subjects.map(({ name, topics, difficulty }) => ({ name: name.trim(), topics, difficulty })).filter((subject) => subject.name && subject.topics.length);
      setPlan(await api.createPlan({ subjects: payloadSubjects, exam_date: data.get("examDate"), available_hours_per_day: Number(data.get("hours")) }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The plan could not be created."); } finally { setLoading(false); }
  }

  async function modify(event: FormEvent) {
    event.preventDefault(); if (!plan || !instruction.trim()) return; setLoading(true); setError("");
    try { setPlan(await api.modifyPlan(plan.id, instruction)); setInstruction(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The change could not be applied."); }
    finally { setLoading(false); }
  }

  if (loading && !plan && subjects.length === 0) return <section className="planner workspace"><div className="thinking"><LoaderCircle className="spinner" /> Loading planner…</div></section>;

  return <section className="planner workspace"><header className="workspace__head"><div><p className="context-label">Deterministic planner</p><h1>Build time you can keep.</h1></div>{plan && <span className="status">Version {plan.version}</span>}</header>
    {!plan ? <form className="planner-form" onSubmit={create}>
      <div className="wide subject-editor"><div className="subject-editor__head"><strong>Subjects</strong><button type="button" onClick={() => setSubjects((items) => [...items, newSubject()])}><Plus size={16}/> Add subject</button></div>
        {subjects.map((subject, index) => <fieldset key={subject.key}><legend>Subject {index + 1}</legend><label>Name<input required value={subject.name} onChange={(event) => updateSubject(subject.key, { name: event.target.value })} placeholder="DBMS"/></label><label>Topics<input required value={subject.topics.join(", ")} onChange={(event) => updateSubject(subject.key, { topics: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} placeholder="SQL, Normalization, Transactions"/></label><label>Difficulty<select value={subject.difficulty} onChange={(event) => updateSubject(subject.key, { difficulty: Number(event.target.value) })}>{[1,2,3,4,5].map((value) => <option value={value} key={value}>{value}</option>)}</select></label>{subjects.length > 1 && <button className="icon-button" type="button" aria-label={`Remove subject ${index + 1}`} onClick={() => setSubjects((items) => items.filter((item) => item.key !== subject.key))}><Trash2 size={16}/></button>}</fieldset>)}
      </div>
      <label>Exam date<input name="examDate" type="date" required/></label><label>Hours per day<input name="hours" type="number" min="0.5" max="16" step="0.5" defaultValue="3" required/></label><button className="primary" disabled={loading}>{loading ? "Building plan…" : "Create study plan"}</button>
    </form> : <div className="plan-view"><div className="plan-summary"><CalendarDays/><div><strong>{plan.sessions.length} study sessions</strong><span>Before {new Date(plan.exam_date).toLocaleDateString()}</span></div><button type="button" className="secondary" onClick={() => setPlan(undefined)}>Create another plan</button></div><div className="schedule">{plan.sessions.map((session) => <article key={session.id ?? `${session.session_date}-${session.subject}-${session.topic}`}><time>{new Date(`${session.session_date}T12:00:00`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</time><div><strong>{session.subject}</strong><span>{session.topic}</span></div><b>{session.duration_minutes} min</b></article>)}</div><form className="modifier" onSubmit={modify}><label htmlFor="instruction">Modify this plan</label><div><input id="instruction" value={instruction} onChange={(event) => setInstruction(event.target.value)} placeholder="I cannot study on Saturday"/><button disabled={loading || !instruction.trim()}>{loading ? "Applying…" : "Apply change"}</button></div></form></div>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </section>;
}

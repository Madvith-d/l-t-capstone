"use client";
import { FormEvent, useState } from "react";
import { CalendarDays, LoaderCircle } from "lucide-react";
import { api, Plan } from "@/lib/api";

export function PlannerWorkspace() {
  const [plan, setPlan] = useState<Plan>(); const [loading, setLoading] = useState(false); const [error, setError] = useState(""); const [instruction, setInstruction] = useState("");
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError(""); const data = new FormData(event.currentTarget);
    try {
      const subjects = String(data.get("subjects")).split("\n").map((line) => {
        const [name, topicText = "General review"] = line.split(":", 2);
        return { name: name.trim(), topics: topicText.split(",").map((value) => value.trim()).filter(Boolean), difficulty: Number(data.get("difficulty")) };
      }).filter((subject) => subject.name && subject.topics.length);
      setPlan(await api.createPlan({ subjects, exam_date: data.get("examDate"), available_hours_per_day: Number(data.get("hours")) }));
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The plan could not be created."); } finally { setLoading(false); }
  }
  async function modify(event: FormEvent) { event.preventDefault(); if (!plan || !instruction.trim()) return; setLoading(true); setError(""); try { setPlan(await api.modifyPlan(plan.id, instruction)); setInstruction(""); } catch (reason) { setError(reason instanceof Error ? reason.message : "The change could not be applied."); } finally { setLoading(false); } }
  return <section className="planner workspace"><header className="workspace__head"><div><p className="context-label">Deterministic planner</p><h1>Build time you can keep.</h1></div>{plan && <span className="status">Version {plan.version}</span>}</header>
    {!plan ? <form className="planner-form" onSubmit={create}><label className="wide">Subjects and topics<textarea name="subjects" required rows={4} placeholder={"DBMS: SQL, Normalization, Transactions\nOperating Systems: Scheduling, Memory"}/><small>Enter one subject per line, followed by colon-separated topics.</small></label><label>Difficulty<select name="difficulty" defaultValue="3"><option value="1">1 — Light</option><option value="2">2</option><option value="3">3 — Moderate</option><option value="4">4</option><option value="5">5 — Difficult</option></select></label><label>Exam date<input name="examDate" type="date" required/></label><label>Hours per day<input name="hours" type="number" min="0.5" max="16" step="0.5" defaultValue="3" required/></label><button className="primary" disabled={loading}>{loading ? "Building plan…" : "Create study plan"}</button></form> : <div className="plan-view"><div className="plan-summary"><CalendarDays/><div><strong>{plan.sessions.length} study sessions</strong><span>Before {new Date(plan.exam_date).toLocaleDateString()}</span></div></div><div className="schedule">{plan.sessions.map((session) => <article key={session.id ?? `${session.session_date}-${session.subject}-${session.topic}`}><time>{new Date(`${session.session_date}T12:00:00`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</time><div><strong>{session.subject}</strong><span>{session.topic}</span></div><b>{session.duration_minutes} min</b></article>)}</div><form className="modifier" onSubmit={modify}><label htmlFor="instruction">Modify this plan</label><div><input id="instruction" value={instruction} onChange={(event) => setInstruction(event.target.value)} placeholder="I cannot study on Saturday"/><button disabled={loading || !instruction.trim()}>Apply change</button></div></form></div>}
    {error && <p className="form-error" role="alert">{error} Review the constraints and try again.</p>}
  </section>;
}

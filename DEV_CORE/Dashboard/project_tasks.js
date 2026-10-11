/* Project shell: private data and authorization always come from the API. */
(() => {
  "use strict";
  const ids = ["login", "workspace", "project-input", "user-input", "password-input", "connect", "message",
    "project-title", "identity", "rights", "tasks", "empty", "refresh", "logout", "previous", "next", "page",
    "context-panel", "context-status", "context-card", "context-decisions", "context-provenance",
    "context-warnings", "context-omissions", "context-form", "context-query", "context-search",
    "audit-panel", "audit-form", "audit-task", "audit-search", "audit-status", "audit-events", "audit-next"];
  const ui = Object.fromEntries(ids.map(id => [id, document.getElementById(id)]));
  const limit = 20;
  let session = null, tasks = [], offset = 0, busy = false;
  let context = null, contextBusy = false, contextMessage = "", contextGeneration = 0, contextController = null;
  let audit = null, auditBusy = false, auditMessage = "", auditGeneration = 0, auditController = null, auditTask = "";
  const contextWarnings = {
    card_changed_since_review: "La fiche a changé depuis sa revue.",
    context_review_expired: "La revue du contexte est ancienne : vérifiez les faits actuels.",
    review_date_in_future: "La date de revue du contexte est dans le futur."
  };

  class ApiError extends Error {
    constructor(status) { super("API request failed"); this.status = status; }
  }
  async function request(path, options = {}) {
    const response = await fetch(path, { ...options, credentials: "same-origin", cache: "no-store" });
    if (!response.ok) throw new ApiError(response.status);
    return response.json();
  }
  const canMutate = () => session && session.actions.includes("task.mutate");
  const canReadContext = () => session && session.actions.includes("context.read");
  const canReadAudit = () => session && session.actions.includes("task.audit.read");
  const sessionKey = () => session && JSON.stringify([session.project, session.user_id, session.csrf_token]);
  const validVersion = task => Number.isSafeInteger(task.version) && task.version > 0;
  const message = text => { ui.message.textContent = text; };
  function clearSession() {
    clearContext(); ui["context-query"].value = "";
    clearAudit(); ui["audit-task"].value = "";
    session = null; tasks = []; offset = 0; ui["password-input"].value = "";
  }
  function clearAudit() {
    auditGeneration++; auditController?.abort(); auditController = null;
    audit = null; auditBusy = false; auditMessage = "";
    renderAudit();
  }
  function renderAudit() {
    ui["audit-panel"].hidden = !canReadAudit();
    ui["audit-panel"].setAttribute("aria-busy", String(auditBusy));
    ui["audit-status"].textContent = canReadAudit() ? auditMessage : "";
    ui["audit-events"].replaceChildren();
    for (const event of audit?.events || []) {
      const row = document.createElement("tr");
      cell(row, event.created_at); cell(row, event.task_id); cell(row, event.actor);
      cell(row, `${({"task.complete": "Clôture", "task.delete": "Suppression", "task.pause": "Pause", "task.resume": "Reprise"})[event.action]} · ${event.before.status} (v${event.before.version}) → ${event.after.status} (v${event.after.version})`);
      ui["audit-events"].append(row);
    }
    ui["audit-task"].disabled = ui["audit-search"].disabled = busy || auditBusy || !canReadAudit();
    ui["audit-next"].disabled = busy || auditBusy || !canReadAudit() || !audit?.has_more;
  }
  const auditUUID = value => typeof value === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value);
  const taskIdentifier = value => typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value) && !value.includes("..");
  function validateAudit(result, raw, project, filter, before) {
    if (new TextEncoder().encode(raw).length > 65536 || JSON.stringify(result) + "\n" !== raw ||
        result?.success !== true || result.project !== project || !Array.isArray(result.events) || result.events.length > limit ||
        JSON.stringify(result.supported_actions) !== '["task.complete","task.delete","task.pause","task.resume"]' || typeof result.has_more !== "boolean" ||
        !Object.hasOwn(result, "next_before_id")) throw new Error("Invalid audit page");
    const identities = new Set(), events = [];
    for (const event of result.events) {
      if (!event || event.project !== project || !auditUUID(event.id) || identities.has(event.id) || event.id === before ||
          !taskIdentifier(event.task_id) || (filter && event.task_id !== filter) ||
          !["task.complete", "task.delete", "task.pause", "task.resume"].includes(event.action) ||
          typeof event.actor !== "string" || !event.actor.trim() || [...event.actor].length > 128 || /[\u0000-\u001f\u007f]/.test(event.actor) ||
          typeof event.created_at !== "string" || !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(event.created_at)) throw new Error("Invalid audit event");
      const date = event.created_at.replace(" ", "T") + "Z";
      if (!Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0, 19) !== date.slice(0, 19)) throw new Error("Invalid audit date");
      for (const state of [event.before, event.after]) {
        if (!state || !["todo", "in_progress", "paused", "done", "blocked", "deleted"].includes(state.status) ||
            !Number.isSafeInteger(state.version) || state.version < 1) throw new Error("Invalid audit state");
      }
      const source = ({"task.pause": "in_progress", "task.resume": "paused"})[event.action];
      if (source && event.before.status !== source) throw new Error("Invalid audit transition");
      if (event.after.version !== event.before.version + 1 || event.after.status !== ({"task.complete": "done", "task.delete": "deleted", "task.pause": "paused", "task.resume": "in_progress"})[event.action]) throw new Error("Invalid audit transition");
      identities.add(event.id);
      events.push({id: event.id, task_id: event.task_id, actor: event.actor, action: event.action, created_at: event.created_at,
        before: {status: event.before.status, version: event.before.version}, after: {status: event.after.status, version: event.after.version}});
    }
    if (result.has_more ? (!events.length || !auditUUID(result.next_before_id) || result.next_before_id !== events.at(-1).id) : result.next_before_id !== null) throw new Error("Invalid audit cursor");
    return {events, has_more: result.has_more, next_before_id: result.next_before_id};
  }
  async function auditBody(response) {
    if (!response.body?.getReader) {
      const text = await response.text();
      if (new TextEncoder().encode(text).length > 65536) throw new Error("Audit exceeds bound");
      return text;
    }
    const reader = response.body.getReader(), decoder = new TextDecoder("utf-8", {fatal: true});
    let bytes = 0, text = "";
    try {
      while (true) {
        const part = await reader.read();
        if (part.done) break;
        bytes += part.value.byteLength;
        if (bytes > 65536) throw new Error("Audit exceeds bound");
        text += decoder.decode(part.value, {stream: true});
      }
      return text + decoder.decode();
    } catch (error) { await reader.cancel().catch(() => {}); throw error; }
    finally { reader.releaseLock(); }
  }
  async function loadAudit(filter = "", before = null) {
    clearAudit();
    if (!canReadAudit()) return;
    auditTask = filter;
    const generation = auditGeneration, key = sessionKey(), project = session.project;
    const isCurrent = () => generation === auditGeneration && key === sessionKey() && canReadAudit();
    const controller = new AbortController(); auditController = controller;
    auditBusy = true; auditMessage = "Chargement de l’historique…"; renderAudit();
    try {
      const response = await fetch(`/api/project/task-audit?project=${encodeURIComponent(project)}&limit=${limit}${filter ? `&task_id=${encodeURIComponent(filter)}` : ""}${before ? `&before_id=${encodeURIComponent(before)}` : ""}`,
        {credentials: "same-origin", cache: "no-store", signal: controller.signal});
      if (!isCurrent()) return;
      if (!response.ok) throw new ApiError(response.status);
      const raw = await auditBody(response);
      if (!isCurrent()) return;
      audit = validateAudit(JSON.parse(raw), raw, project, filter, before);
      auditMessage = audit.events.length ? "Modifications enregistrées affichées." : "Aucune modification enregistrée pour cette sélection.";
    } catch (error) {
      if (!isCurrent()) return;
      if (error.status === 401 || error.status === 403) {
        clearSession(); render(); message("Accès à l’historique refusé. Reconnectez-vous pour vérifier vos droits."); return;
      }
      auditMessage = error.status === 400 ? "Cette sélection n’est plus disponible. Affichez les dernières modifications." :
        "L’historique n’est pas disponible. Les tâches restent accessibles.";
    } finally {
      if (isCurrent()) { auditBusy = false; auditController = null; renderAudit(); }
    }
  }
  function clearContext() {
    contextGeneration++; contextController?.abort(); contextController = null;
    context = null; contextBusy = false; contextMessage = "";
    renderContext();
  }
  function renderContext() {
    ui["context-panel"].hidden = !session;
    ui["context-panel"].setAttribute("aria-busy", String(contextBusy));
    ui["context-status"].textContent = session ? (canReadContext() ? contextMessage :
      "Cette session n’autorise pas la consultation de la fiche et des décisions.") : "";
    ui["context-card"].textContent = context ? context.card : "";
    ui["context-decisions"].replaceChildren();
    for (const decision of context?.decisions || []) {
      const item = document.createElement("li"), title = document.createElement("strong");
      title.textContent = `${decision.id} · ${decision.status === "effective" ? "En vigueur" : "Proposée"}`;
      item.append(title);
      for (const text of [decision.decision, `Justification : ${decision.rationale}`,
        `Validation : ${decision.validation}`, `Sources déclarées : ${decision.sources.join(" ; ")}`,
        `Date : ${decision.date || "non établie"}`]) {
        const paragraph = document.createElement("p"); paragraph.textContent = text; item.append(paragraph);
      }
      ui["context-decisions"].append(item);
    }
    ui["context-provenance"].textContent = context ?
      `Revue : ${context.provenance.reviewed_at} · Volume : ${context.measurement.used}/${context.measurement.budget} octets UTF-8. Références déclarées, non vérifiées par cette lecture.` : "";
    ui["context-warnings"].textContent = context ? context.warnings.map(warning => contextWarnings[warning]).join(" ") : "";
    ui["context-omissions"].textContent = context ? [
      ...context.omitted.map(item => `${item.id} : ${item.reason === "budget" ? "hors budget" : "non pertinent pour ce sujet"}`),
      ...(context.excluded_superseded.length ? [`Décisions remplacées exclues : ${context.excluded_superseded.join(", ")}`] : [])
    ].join(" ; ") : "";
    ui["context-query"].disabled = ui["context-search"].disabled = busy || contextBusy || !canReadContext();
  }
  function validateContext(result, raw, project) {
    const strings = values => Array.isArray(values) && values.every(value => typeof value === "string" && value);
    const measured = result?.measurement, provenance = result?.provenance;
    if (result?.project !== project || result.schema_version !== 1 ||
        typeof result.card !== "string" || !result.card.trim() ||
        measured?.unit !== "utf8_bytes" || measured.scope !== "complete_json_line" || measured.model_tokens_measured !== false ||
        !Number.isSafeInteger(measured.budget) || measured.budget < 256 || measured.budget > 65536 ||
        !Number.isSafeInteger(measured.used) || measured.used < 1 || measured.used > measured.budget ||
        measured.used !== new TextEncoder().encode(raw).length ||
        typeof provenance?.card_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(provenance.card_sha256) ||
        typeof provenance.manifest_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(provenance.manifest_sha256) ||
        typeof provenance.reviewed_at !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(provenance.reviewed_at) || provenance.source_contents_verified !== false ||
        !Array.isArray(result.warnings) || result.warnings.some(warning => typeof warning !== "string" || !Object.hasOwn(contextWarnings, warning)) ||
        !Array.isArray(result.decisions) || !strings(result.excluded_superseded) || !Array.isArray(result.omitted)) {
      throw new Error("Invalid scoped context response");
    }
    const identities = new Set();
    for (const decision of result.decisions) {
      if (!decision || typeof decision.id !== "string" || !decision.id || identities.has(decision.id) ||
          result.excluded_superseded.includes(decision.id) || !["effective", "proposed"].includes(decision.status) ||
          typeof decision.required !== "boolean" || (decision.required && decision.status !== "effective") ||
          (decision.date != null && (typeof decision.date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(decision.date))) ||
          [decision.decision, decision.rationale, decision.validation].some(value => typeof value !== "string" || !value.trim()) ||
          !strings(decision.sources) || !decision.sources.length) throw new Error("Invalid context decision");
      identities.add(decision.id);
    }
    if (result.omitted.some(item => !item || typeof item.id !== "string" || !item.id ||
        identities.has(item.id) || !["budget", "not_relevant"].includes(item.reason))) throw new Error("Invalid context omissions");
    return result;
  }
  async function loadContext(query = "") {
    clearContext();
    if (!canReadContext()) return;
    const generation = contextGeneration, key = sessionKey(), project = session.project;
    const isCurrent = () => generation === contextGeneration && key === sessionKey() && canReadContext();
    const controller = new AbortController(); contextController = controller;
    contextBusy = true; contextMessage = "Chargement de la fiche et des décisions…"; renderContext();
    try {
      const response = await fetch(`/api/project/context?project=${encodeURIComponent(project)}${query ? `&query=${encodeURIComponent(query)}` : ""}`,
        {credentials: "same-origin", cache: "no-store", signal: controller.signal});
      if (!isCurrent()) return;
      if (!response.ok) throw new ApiError(response.status);
      const raw = await response.text();
      if (!isCurrent()) return;
      context = validateContext(JSON.parse(raw), raw, project);
      contextMessage = "Fiche et décisions chargées.";
    } catch (error) {
      if (!isCurrent()) return;
      if (error.status === 401 || error.status === 403) {
        clearSession(); render();
        message(error.status === 401 ? "Session absente ou expirée. Reconnectez-vous." : "Accès refusé pour ce projet ou cette session.");
        return;
      }
      contextMessage = error.status === 413 ? "La fiche et ses décisions obligatoires dépassent le budget. Aucun contexte partiel chargé." :
        "Le contexte n’est pas disponible. Les tâches restent accessibles ; actualisez ou réessayez le sujet.";
    } finally {
      if (isCurrent()) { contextBusy = false; contextController = null; renderContext(); }
    }
  }
  function cell(row, text) {
    const element = document.createElement("td"); element.textContent = text; row.append(element); return element;
  }
  function render() {
    ui.login.hidden = Boolean(session); ui.workspace.hidden = !session;
    for (const id of ["project-input", "user-input", "password-input", "connect", "refresh", "logout"]) ui[id].disabled = busy;
    ui.workspace.setAttribute("aria-busy", String(busy));
    ui["project-title"].textContent = session ? `Projet ${session.project}` : "";
    ui.identity.textContent = session ? `Utilisateur : ${session.user_id}` : "";
    ui.rights.textContent = session ? (canMutate() ? "Consultation et modification autorisées." : "Consultation uniquement.") : "";
    ui.tasks.replaceChildren();
    for (const task of tasks) {
      const row = document.createElement("tr");
      cell(row, `${task.id} · ${task.title}`); cell(row, task.status);
      const actions = cell(row, "");
      if (canMutate()) {
        for (const [label, method, path] of [["Terminer", "POST", "/api/done"], ["Supprimer", "DELETE", "/api/delete"], ["Pause", "POST", "/api/pause"], ["Reprendre", "POST", "/api/resume"]]) {
          if (path === "/api/done" && task.status === "done") continue;
          if (path === "/api/pause" && task.status !== "in_progress") continue;
          if (path === "/api/resume" && task.status !== "paused") continue;
          const button = document.createElement("button"); button.type = "button"; button.textContent = label;
          button.disabled = busy || !validVersion(task);
          if (!validVersion(task)) button.title = "Version de tâche indisponible : actualisez après migration.";
          button.addEventListener("click", () => run(() => mutate(task, method, path)));
          actions.append(button);
        }
      }
      ui.tasks.append(row);
    }
    ui.empty.hidden = tasks.length !== 0;
    ui.page.textContent = `Page ${Math.floor(offset / limit) + 1}`;
    ui.previous.disabled = busy || !session || offset === 0;
    ui.next.disabled = busy || !session || tasks.length < limit;
    renderContext();
    renderAudit();
  }
  async function load() {
    // Clear displayed data before revalidating membership and loading a page.
    const previousKey = sessionKey();
    tasks = []; clearContext(); clearAudit(); render();
    const current = await request("/api/auth/session");
    if (typeof current.project !== "string" || !current.project || typeof current.user_id !== "string" ||
        !Array.isArray(current.actions) || !current.actions.includes("task.read") ||
        typeof current.csrf_token !== "string" || !/^[a-f0-9]{64}$/.test(current.csrf_token)) {
      clearSession(); throw new Error("Invalid session response");
    }
    if (session && session.project !== current.project) offset = 0;
    session = current;
    if (previousKey !== sessionKey()) { ui["context-query"].value = ""; ui["audit-task"].value = ""; auditTask = ""; }
    const result = await request(`/api/dashboard/tasks?project=${encodeURIComponent(session.project)}&limit=${limit}&offset=${offset}`);
    if (!Array.isArray(result) || result.some(task => !task || task.project !== session.project ||
        typeof task.id !== "string" || typeof task.title !== "string" || typeof task.status !== "string")) {
      throw new Error("Invalid scoped task response");
    }
    tasks = result;
    // Context has its own loading state; a slow read must not hold task actions.
    void loadContext();
  }
  async function mutate(task, method, path) {
    if (!canMutate() || !validVersion(task) || task.project !== session.project) return;
    const label = ({"/api/done": "Terminer", "/api/delete": "Supprimer", "/api/pause": "Mettre en pause", "/api/resume": "Reprendre"})[path];
    if (!window.confirm(`${label} ${task.id} dans ${session.project} ?`)) {
      message("Action annulée."); return;
    }
    try {
      await request(path, { method, headers: { "Content-Type": "application/json", "X-CSRF-Token": session.csrf_token },
        body: JSON.stringify({ project: session.project, id: task.id, expected_version: task.version }) });
    } catch (error) {
      if (error.status === 409 || error.status === 403) {
        await load();
        message(error.status === 409 ? "La tâche a changé. Liste actualisée : vérifiez avant une nouvelle action." :
          "Action refusée. Vos droits et la liste ont été actualisés.");
        return;
      }
      throw error;
    }
    await load(); message("Action enregistrée.");
  }
  async function run(operation, { initial = false, login = false } = {}) {
    if (busy) return;
    busy = true; render(); message("Chargement…");
    try { await operation(); }
    catch (error) {
      if (error.status === 401 || error.status === 403) {
        clearSession();
        message(initial && error.status === 401 ? "Connectez-vous pour consulter votre projet." :
          error.status === 401 ? (login ? "Connexion refusée. Vérifiez vos identifiants ou réessayez plus tard." :
            "Session absente ou expirée. Reconnectez-vous.") :
            "Accès refusé pour ce projet ou cette session.");
      } else {
        message(error.status === 429 ? "Connexions en cours. Réessayez dans quelques instants." :
          error.status === 503 ? "Service indisponible. Réessayez plus tard." :
          "La requête n’a pas abouti. Actualisez pour vérifier l’état avant une nouvelle action.");
      }
    } finally { busy = false; render(); }
  }
  ui.login.addEventListener("submit", event => {
    event.preventDefault();
    if (busy) return;
    const project = ui["project-input"].value.trim(), user_id = ui["user-input"].value.trim(), password = ui["password-input"].value;
    ui["password-input"].value = "";
    if (!project || !user_id || !password) { message("Projet, utilisateur et mot de passe requis."); return; }
    run(async () => {
      await request("/api/auth/session", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project, user_id, password }) });
      offset = 0; await load(); message("Session ouverte.");
    }, { login: true });
  });
  ui.refresh.addEventListener("click", () => run(async () => { await load(); message("Liste actualisée."); }));
  ui["context-form"].addEventListener("submit", event => {
    event.preventDefault();
    if (busy || contextBusy || !canReadContext()) return;
    const query = ui["context-query"].value.trim();
    if (query.length > 4096) return;
    void loadContext(query);
  });
  ui.previous.addEventListener("click", () => run(async () => { offset = Math.max(0, offset - limit); await load(); message("Liste actualisée."); }));
  ui["audit-form"].addEventListener("submit", event => {
    event.preventDefault();
    if (busy || auditBusy || !canReadAudit()) return;
    const filter = ui["audit-task"].value.trim();
    if (filter && !taskIdentifier(filter)) { clearAudit(); auditMessage = "Identifiant de tâche invalide."; renderAudit(); return; }
    void loadAudit(filter);
  });
  ui["audit-next"].addEventListener("click", () => {
    if (busy || auditBusy || !canReadAudit() || !audit?.has_more) return;
    void loadAudit(auditTask, audit.next_before_id);
  });
  ui.next.addEventListener("click", () => run(async () => { offset += limit; await load(); message("Liste actualisée."); }));
  ui.logout.addEventListener("click", () => run(async () => {
    await request("/api/auth/session", { method: "DELETE", headers: { "X-CSRF-Token": session.csrf_token } });
    clearSession(); message("Session fermée.");
  }));
  run(async () => { await load(); message("Session reprise."); }, { initial: true });
})();

// Presentation for the project-scoped team snapshot; no extra data requests.
function syncTeamCockpit(data) {
  if (data) {
    window.devcoreTeamCounts = data.counts || {};
    window.devcoreTeamHealth = data.service_health || {};
  }
  const counts = window.devcoreTeamCounts || {};
  const health = window.devcoreTeamHealth || {};
  document.querySelectorAll('[data-team-service]').forEach(element => {
    const online = health.services?.[element.dataset.teamService];
    element.textContent = online === true ? 'En ligne' : online === false ? 'Indisponible' : 'Non supervisé';
    element.className = online ? 'status-ok' : 'status-todo';
  });
  const counter = document.getElementById('task-count');
  if (counter) counter.textContent = counts.tasks ?? '—';
  const api = document.getElementById('api-ok');
  if (api) {
    api.textContent = ':20131 ' + (health.services?.gateway ? '✓' : '—');
    api.className = health.services?.gateway ? 'v-ok' : 'v-dim';
  }
  const system = document.getElementById('sys-status');
  if (system) {
    system.textContent = health.status === 'ready' ? 'ONLINE' : health.status === 'degraded' ? 'DEGRADED' : '—';
    system.className = health.status === 'ready' ? 'v-ok' : 'v-dim';
  }
  for (const [label, key] of [['SCHEDULER', 'scheduler'], ['REPOWISE', 'repowise']]) {
    const segment = Array.from(document.querySelectorAll('.seg')).find(el => el.textContent.trim().startsWith(label));
    const span = segment?.querySelector('span');
    if (span) {
      span.textContent = health.services?.[key] ? (key === 'repowise' ? 'MCP' : 'ACTIVE') : '—';
      span.className = health.services?.[key] ? 'v-ok' : 'v-dim';
    }
  }
}

showDetails = function(project, taskId, status, button, event) {
  event?.stopPropagation();
  const map = JSON.parse(document.getElementById('task-details-data')?.textContent || '{}');
  const detail = map[`${project}_${taskId}`];
  if (!detail || project !== window.devcoreActiveProject) return;
  const bubble = document.getElementById('details-bubble');
  bubble.innerHTML = '<div class="bubble-header"><span></span><button class="bubble-close" onclick="closeDetails(event)">×</button></div><div class="bubble-content" style="white-space:pre-wrap"></div>';
  bubble.querySelector('.bubble-header span').textContent = '⚙ DÉTAILS : ' + taskId;
  bubble.querySelector('.bubble-content').textContent = detail;
  bubble.style.display = 'block';
  bubble.style.width = '360px';
  const rect = button.getBoundingClientRect();
  bubble.style.left = Math.max(10, Math.min(rect.right - 360, window.innerWidth - 370)) + 'px';
  bubble.style.top = Math.max(10, Math.min(rect.bottom + 8, window.innerHeight - bubble.offsetHeight - 10)) + 'px';
  bubble.classList.add('show');
};

showInteractions = function(project, taskId, button, event) {
  event?.stopPropagation();
  const map = JSON.parse(document.getElementById('task-interactions-data')?.textContent || '{}');
  const value = map[`${project}_${taskId}`];
  if (!value || value.project !== window.devcoreActiveProject || value.task_id !== taskId) return;
  const modal = document.getElementById('interactions-modal');
  const body = document.getElementById('interactions-body');
  document.getElementById('interactions-title').textContent = `Interactions : ${taskId} (${project})`;
  body.replaceChildren();
  const title = document.createElement('strong');
  title.textContent = value.title;
  body.append(title);
  const note = document.createElement('p');
  note.textContent = 'Aucune télémétrie de jetons, coût ou fichiers attribuée à cette tâche.';
  body.append(note);
  const heading = document.createElement('h4');
  heading.textContent = 'Événements récents attribués';
  body.append(heading);
  for (const record of value.events || []) {
    const row = document.createElement('div');
    row.className = 'component';
    row.textContent = `${record.event_type} · ${record.created_at}`;
    body.append(row);
  }
  if (!value.events?.length) {
    const empty = document.createElement('p');
    empty.textContent = 'Aucun événement récent attribué à cette tâche.';
    body.append(empty);
  }
  modal.classList.add('team-interactions-open');
  modal.style.display = 'flex';
};
closeInteractions = function() {
  const modal = document.getElementById('interactions-modal');
  modal.classList.remove('team-interactions-open');
  modal.style.display = 'none';
};
syncTeamCockpit();

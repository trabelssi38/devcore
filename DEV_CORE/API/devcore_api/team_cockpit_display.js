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

let teamProjectTab = 'active';

async function loadTeamProjects() {
  const panel = document.getElementById('team-projects');
  if (!panel) return;
  try {
    const response = await teamFetch('/api/auth/session', {cache:'no-store'});
    if (!response.ok) throw new Error('Session indisponible');
    const session = await response.json();
    teamProjectTab = session.projects.find(p => p.id === session.project)?.status === 'archived'
      ? 'archived' : 'active';
    panel.replaceChildren();
    const heading = document.createElement('h3');
    heading.textContent = 'Mes projets';
    panel.append(heading);
    const tabs = document.createElement('div');
    tabs.className = 'team-project-tabs';
    for (const [key, label] of [['active','Actifs'],['archived','Archivés']]) {
      const button = document.createElement('button');
      const count = session.projects.filter(p => (p.status === 'archived') === (key === 'archived')).length;
      button.type = 'button';
      button.className = 'team-project-tab' + (teamProjectTab === key ? ' selected' : '');
      button.textContent = `${label} (${count})`;
      button.setAttribute('aria-pressed', String(teamProjectTab === key));
      button.addEventListener('click', () => { teamProjectTab = key; renderProjects(); });
      tabs.append(button);
    }
    panel.append(tabs);
    const error = document.createElement('p');
    error.setAttribute('role', 'alert');
    const list = document.createElement('div');
    list.className = 'team-project-list';
    panel.append(list);
    panel.append(error);
    function renderProjects() {
      list.replaceChildren();
      for (const project of session.projects.filter(p => (p.status === 'archived') === (teamProjectTab === 'archived'))) {
        const card = document.createElement('article');
        card.className = 'project-row team-project-card' + (project.id === session.project ? ' selected' : '');
        card.dataset.project = project.id;
        const headingRow = document.createElement('div');
        headingRow.className = 'team-project-heading';
        const dot = document.createElement('span');
        dot.className = 'project-dot ' + (project.status === 'archived' ? 'status-todo' : 'status-ok');
        const name = document.createElement('strong');
        name.textContent = project.name;
        const progress = document.createElement('strong');
        const percent = project.tasks ? Math.round(100 * project.completed_tasks / project.tasks) : 0;
        progress.textContent = percent + '%';
        headingRow.append(dot, name, progress);
        const active = document.createElement('div');
        active.className = 'component-detail';
        active.textContent = project.active_tasks
          ? `${project.active_tasks} tâche(s) active(s) · ${project.tasks} tâches`
          : `Aucune tâche active · ${project.tasks} tâches`;
        const bar = document.createElement('div');
        bar.className = 'team-progress';
        const fill = document.createElement('span');
        fill.style.width = percent + '%';
        bar.append(fill);
        const totals = document.createElement('div');
        totals.className = 'component-detail';
        totals.textContent = `${project.completed_tasks} terminées · ${new Intl.NumberFormat('fr-FR').format(project.tokens)} jetons attribués`;
        const actions = document.createElement('div');
        actions.className = 'team-project-actions';
        const open = document.createElement('button');
        open.type = 'button';
        open.className = 'team-project-open';
        open.textContent = project.id === session.project ? 'Projet ouvert' : 'Ouvrir';
        open.disabled = project.id === session.project;
        open.addEventListener('click', () => switchProject(project));
        const archive = document.createElement('button');
        archive.type = 'button';
        archive.className = 'team-project-archive';
        archive.textContent = project.status === 'archived' ? 'Désarchiver' : 'Archiver';
        archive.disabled = !project.can_archive;
        archive.addEventListener('click', async () => {
          archive.disabled = true;
          error.textContent = '';
          try {
            const response = await teamFetch('/api/auth/session', {method:'POST',
              headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token},
              body:JSON.stringify({project:project.id,archive_project:true,archived:project.status!=='archived'})});
            if (!response.ok) throw new Error('Archivage refusé');
            const nowArchived = project.status !== 'archived';
            if (project.id === session.project && nowArchived) {
              const next = session.projects.find(item => item.id !== project.id && item.status !== 'archived');
              if (next) { await switchProject(next); return; }
              teamProjectTab = 'archived';
            }
            await loadTeamProjects();
          } catch (failure) { error.textContent = failure.message; archive.disabled = false; }
        });
        actions.append(open, archive);
        card.append(headingRow, active, bar, totals, actions);
        list.append(card);
      }
      if (!list.children.length) {
        const empty = document.createElement('p');
        empty.textContent = teamProjectTab === 'archived' ? 'Aucun projet archivé.' : 'Aucun projet actif.';
        list.append(empty);
      }
    }
    async function switchProject(project) {
      panel.querySelectorAll('.team-project-open').forEach(item => item.disabled = true);
      error.textContent = '';
      try {
        const result = await teamFetch('/api/auth/session', {
          method:'POST', headers:{'Content-Type':'application/json', 'X-CSRF-Token':session.csrf_token},
          body:JSON.stringify({project:project.id, switch_project:true})
        });
        if (!result.ok) throw new Error('Changement de projet refusé');
        const path = ['/cockpit', '/cockpit/terminal', '/index.html', '/index_terminal.html'].includes(location.pathname)
          ? location.pathname : '/cockpit';
        location.assign(path + '?' + new URLSearchParams({project:project.id}));
      } catch (failure) {
        error.textContent = failure.message;
        panel.querySelectorAll('.team-project-open').forEach(item => item.disabled = item.dataset.project === session.project);
      }
    }
    renderProjects();
  } catch (failure) {
    panel.textContent = 'Liste des projets indisponible. Rechargez la page.';
  }
}
loadTeamProjects();

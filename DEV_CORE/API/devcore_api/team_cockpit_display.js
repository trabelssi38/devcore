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

const TEAM_PROJECTS_PER_PAGE = 4;
let teamProjectPage = 0;

function makeProjectIconButton(className, label, paths, disabled, onClick) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'team-project-icon ' + className;
  button.setAttribute('aria-label', label);
  button.setAttribute('title', label);
  button.disabled = disabled;
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.setAttribute('viewBox', '0 0 24 24');
  icon.setAttribute('aria-hidden', 'true');
  for (const definition of paths) {
    const shape = document.createElementNS('http://www.w3.org/2000/svg', definition.tag);
    for (const [key, value] of Object.entries(definition.attrs)) shape.setAttribute(key, value);
    icon.append(shape);
  }
  button.append(icon);
  button.addEventListener('click', onClick);
  return button;
}

async function loadTeamProjects() {
  const panel = document.getElementById('team-projects');
  if (!panel) return;
  try {
    const response = await teamFetch('/api/auth/session', {cache:'no-store'});
    if (!response.ok) throw new Error('Session indisponible');
    const session = await response.json();
    const projects = session.projects || [];
    const pageCount = Math.max(1, Math.ceil(projects.length / TEAM_PROJECTS_PER_PAGE));
    teamProjectPage = Math.min(teamProjectPage, pageCount - 1);
    panel.replaceChildren();
    const heading = document.createElement('h3');
    heading.textContent = 'Mes projets';
    panel.append(heading);
    const error = document.createElement('p');
    error.setAttribute('role', 'alert');
    const list = document.createElement('div');
    list.className = 'team-project-list';
    const pagination = document.createElement('div');
    pagination.className = 'team-project-pagination';
    const previous = document.createElement('button');
    previous.type = 'button';
    previous.className = 'team-project-page team-project-previous';
    previous.textContent = '‹';
    previous.setAttribute('aria-label', 'Projets précédents');
    const pageLabel = document.createElement('span');
    pageLabel.className = 'team-project-page-label';
    const next = document.createElement('button');
    next.type = 'button';
    next.className = 'team-project-page team-project-next';
    next.textContent = '›';
    next.setAttribute('aria-label', 'Projets suivants');
    previous.addEventListener('click', () => { teamProjectPage--; renderProjects(); });
    next.addEventListener('click', () => { teamProjectPage++; renderProjects(); });
    pagination.append(previous, pageLabel, next);
    const loading = document.createElement('div');
    loading.className = 'team-project-refresh';
    loading.setAttribute('role', 'status');
    loading.setAttribute('aria-live', 'polite');
    panel.append(list);
    panel.append(pagination);
    panel.append(error);
    panel.append(loading);
    function renderProjects() {
      list.replaceChildren();
      const pages = Math.max(1, Math.ceil(projects.length / TEAM_PROJECTS_PER_PAGE));
      teamProjectPage = Math.max(0, Math.min(teamProjectPage, pages - 1));
      previous.disabled = teamProjectPage === 0;
      next.disabled = teamProjectPage >= pages - 1;
      pagination.hidden = pages <= 1;
      pageLabel.textContent = `${teamProjectPage + 1} / ${pages}`;
      const visibleProjects = projects.slice(teamProjectPage * TEAM_PROJECTS_PER_PAGE,
        (teamProjectPage + 1) * TEAM_PROJECTS_PER_PAGE);
      for (const project of visibleProjects) {
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
        const projectState = project.status === 'archived' ? 'Archivé' : 'Actif';
        active.textContent = project.active_tasks
          ? `${projectState} · ${project.active_tasks} tâche(s) active(s) · ${project.tasks} tâches`
          : `${projectState} · Aucune tâche active · ${project.tasks} tâches`;
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
        const open = makeProjectIconButton('team-project-open', `Ouvrir ${project.name}`,
          [{tag:'path',attrs:{d:'M14 3h7v7'}},{tag:'path',attrs:{d:'M10 14 21 3'}},
           {tag:'path',attrs:{d:'M19 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h6'}}],
          project.id === session.project, () => switchProject(project));
        open.dataset.project = project.id;
        const isArchived = project.status === 'archived';
        const archive = makeProjectIconButton('team-project-archive',
          `${isArchived ? 'Désarchiver' : 'Archiver'} ${project.name}`,
          isArchived
            ? [{tag:'path',attrs:{d:'M3 9h18v11H3z'}},{tag:'path',attrs:{d:'M2 4h20v5H2z'}},
               {tag:'path',attrs:{d:'M12 17v-5m0 0-2 2m2-2 2 2'}}]
            : [{tag:'path',attrs:{d:'M3 9h18v11H3z'}},{tag:'path',attrs:{d:'M2 4h20v5H2z'}},
               {tag:'path',attrs:{d:'M9 13h6'}}],
          !project.can_archive, async () => {
            archive.disabled = true;
            error.textContent = '';
            try {
              const response = await teamFetch('/api/auth/session', {method:'POST',
                headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token},
                body:JSON.stringify({project:project.id,archive_project:true,archived:!isArchived})});
              if (!response.ok) throw new Error('Archivage refusé');
              if (project.id === session.project && !isArchived) {
                const nextActive = projects.find(item => item.id !== project.id && item.status !== 'archived');
                if (nextActive) { await switchProject(nextActive); return; }
              }
              await loadTeamProjects();
            } catch (failure) { error.textContent = failure.message; archive.disabled = !project.can_archive; }
          });
        actions.append(open, archive);
        card.append(headingRow, active, bar, totals, actions);
        list.append(card);
      }
      if (!list.children.length) {
        const empty = document.createElement('p');
        empty.textContent = 'Aucun projet Git accessible.';
        list.append(empty);
      }
    }
    async function switchProject(project) {
      panel.querySelectorAll('.team-project-open').forEach(item => item.disabled = true);
      error.textContent = '';
      panel.classList.add('team-projects-switching');
      panel.setAttribute('aria-busy', 'true');
      loading.textContent = `Actualisation des données de ${project.name}…`;
      loading.hidden = false;
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
        panel.classList.remove('team-projects-switching');
        panel.setAttribute('aria-busy', 'false');
        loading.textContent = '';
        loading.hidden = true;
        panel.querySelectorAll('.team-project-open').forEach(item => item.disabled = item.dataset.project === session.project);
      }
    }
    renderProjects();
  } catch (failure) {
    panel.textContent = 'Liste des projets indisponible. Rechargez la page.';
  }
}
loadTeamProjects();

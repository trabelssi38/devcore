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

let teamProjectTab = null;
let teamProjectRequest = null;
let teamProjectGeneration = 0;

async function refreshTeamProjectData(project = window.devcoreActiveProject) {
  const generation = ++teamProjectGeneration;
  teamProjectRequest?.abort();
  const controller = new AbortController();
  teamProjectRequest = controller;
  const deadline = setTimeout(() => controller.abort(), 20000);
  try {
    const offset = Number(new URLSearchParams(location.search).get('task_offset') || 0);
    const url = `/api/dashboard?${new URLSearchParams({project, task_offset: String(offset)})}`;
    const response = await teamFetch(url, {cache:'no-store', signal:controller.signal});
    checkDashboardResponseAccess(response);
    if (!response.ok) throw new Error('Données du projet indisponibles');
    const data = await readDashboardJson(response);
    validateDashboardSnapshot(data);
    if (data.project !== project || generation !== teamProjectGeneration ||
        project !== window.devcoreActiveProject) return false;
    for (const [key, id] of Object.entries({
      tasks_pipeline:'tasks-pipeline', token_activity_report:'token-activity-report',
      services_monitoring:'services-monitoring', automation_hooks:'automation-hooks',
      context_composition:'context-composition', metrics_service_summary:'metrics-service-summary',
      event_bus_recent:'event-bus-recent', knowledge_graph_summary:'knowledge-graph-summary',
      plugin_status:'plugin-status'
    })) {
      const element = document.getElementById(id);
      const html = data.sections[key];
      if (element && typeof html === 'string' && element.innerHTML !== html) {
        const wasOpen = key === 'token_activity_report' && element.querySelector('details')?.open;
        updateContainerHTML(id, html);
        if (wasOpen) element.querySelector('details')?.setAttribute('open', '');
      }
    }
    for (const [id, value] of [
      ['task-details-data', data.task_details || {}],
      ['task-interactions-data', data.task_interactions || {}],
      ['token-metrics-data', data.token_metrics || {}]
    ]) {
      const element = document.getElementById(id);
      if (element) element.textContent = JSON.stringify(value);
    }
    const projectName = document.querySelector('[data-team-project-name]');
    if (projectName) projectName.textContent = project;
    const profileProject = document.querySelector('[data-team-profile-project]');
    if (profileProject) profileProject.textContent = project;
    window.taskDetailsMap = data.task_details || {};
    window.activeFilteredProject = null;
    updateTokenReport(null);
    updateRepowiseHealth(null);
    recordAppliedDashboardSnapshot(data);
    syncTeamCockpit(data);
    return true;
  } catch (failure) {
    if (failure.name !== 'AbortError') console.error('Project data load failed:', failure);
    return false;
  } finally {
    clearTimeout(deadline);
    if (teamProjectRequest === controller) teamProjectRequest = null;
  }
}

// The team view changes data in place; the historical template's broad refresh
// would also repaint unrelated service and layout panels.
performDashboardRefresh = () => refreshTeamProjectData();

function reconnectTeamProjectStream() {
  if (typeof dashboardStreamAbort !== 'undefined') {
    dashboardStreamAbort?.abort();
    dashboardStreamAbort = null;
    dashboardLastEventId = null;
    dashboardAppliedSnapshotCursor = null;
    if (dashboardStreamRetryId) clearTimeout(dashboardStreamRetryId);
    dashboardStreamRetryId = null;
    connectDashboardStream();
  } else if (window.devcoreTeamEventSource) {
    window.devcoreTeamEventSource.close();
    connectStream();
  }
}

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
  panel.classList.add('team-projects-loading');
  panel.setAttribute('aria-busy', 'true');
  try {
    const response = await teamFetch('/api/auth/session', {cache:'no-store'});
    if (!response.ok) throw new Error('Session indisponible');
    const session = await response.json();
    let projects = session.projects || [];
    if (teamProjectTab === null) {
      teamProjectTab = projects.find(project => project.id === session.project)?.status === 'archived'
        ? 'archived' : 'active';
    }
    panel.replaceChildren();
    const tabs = document.createElement('div');
    tabs.className = 'team-project-tabs';
    tabs.setAttribute('role', 'tablist');
    tabs.setAttribute('aria-label', 'État des projets');
    const tabButtons = {};
    for (const [key, label] of [['active', 'Actifs'], ['archived', 'Archivés']]) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'team-project-tab';
      button.setAttribute('role', 'tab');
      button.setAttribute('aria-controls', 'team-project-list');
      button.textContent = `${label} (${projects.filter(project =>
        (project.status === 'archived') === (key === 'archived')).length})`;
      button.addEventListener('click', () => {
        teamProjectTab = key;
        list.scrollTop = 0;
        renderProjects();
      });
      tabButtons[key] = button;
      tabs.append(button);
    }
    panel.append(tabs);
    const error = document.createElement('p');
    error.setAttribute('role', 'alert');
    error.className = 'team-project-error';
    const list = document.createElement('div');
    list.className = 'team-project-list';
    list.id = 'team-project-list';
    list.setAttribute('role', 'tabpanel');
    list.setAttribute('tabindex', '0');
    panel.append(list);
    panel.append(error);
    function markSelectedProject() {
      for (const card of panel.querySelectorAll('.team-project-card')) {
        const selected = card.dataset.project === session.project;
        card.classList.toggle('selected', selected);
        if (selected) card.setAttribute('aria-current', 'page');
        else card.removeAttribute('aria-current');
        const select = card.querySelectorAll('.team-project-select')[0];
        if (select) {
          select.disabled = selected;
          select.setAttribute('aria-label', selected
            ? `Projet ouvert : ${projects.find(project => project.id === card.dataset.project)?.name || card.dataset.project}`
            : `Consulter ${projects.find(project => project.id === card.dataset.project)?.name || card.dataset.project}`);
        }
      }
    }
    function renderProjects() {
      list.replaceChildren();
      for (const [key, button] of Object.entries(tabButtons)) {
        button.classList.toggle('selected', key === teamProjectTab);
        button.setAttribute('aria-selected', String(key === teamProjectTab));
      }
      const visibleProjects = projects.filter(project =>
        (project.status === 'archived') === (teamProjectTab === 'archived'));
      for (const project of visibleProjects) {
        const card = document.createElement('article');
        card.className = 'project-row team-project-card' + (project.id === session.project ? ' selected' : '');
        card.dataset.project = project.id;
        if (project.id === session.project) card.setAttribute('aria-current', 'page');
        const select = document.createElement('button');
        select.type = 'button';
        select.className = 'team-project-select';
        select.dataset.project = project.id;
        select.disabled = project.id === session.project;
        select.setAttribute('aria-label', select.disabled
          ? `Projet ouvert : ${project.name}` : `Consulter ${project.name}`);
        select.addEventListener('click', () => switchProject(project));
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
        const footer = document.createElement('div');
        footer.className = 'team-project-footer';
        const actions = document.createElement('div');
        actions.className = 'team-project-actions';
        const isArchived = project.status === 'archived';
        const archive = makeProjectIconButton('team-project-archive',
          `${isArchived ? 'Désarchiver' : 'Archiver'} ${project.name}`,
          isArchived
            ? [{tag:'path',attrs:{d:'M3 9h18v11H3z'}},{tag:'path',attrs:{d:'M2 4h20v5H2z'}},
               {tag:'path',attrs:{d:'M12 17v-5m0 0-2 2m2-2 2 2'}}]
            : [{tag:'path',attrs:{d:'M3 9h18v11H3z'}},{tag:'path',attrs:{d:'M2 4h20v5H2z'}},
               {tag:'path',attrs:{d:'M9 13h6'}}],
          !project.can_archive, async event => {
            event?.stopPropagation();
            archive.disabled = true;
            error.textContent = '';
            try {
              const response = await teamFetch('/api/auth/session', {method:'POST',
                headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token},
                body:JSON.stringify({project:project.id,archive_project:true,archived:!isArchived})});
              if (!response.ok) throw new Error('Archivage refusé');
              if (project.id === session.project && !isArchived) {
                const nextActive = projects.find(item => item.id !== project.id && item.status !== 'archived');
                if (nextActive) {
                  if (!await switchProject(nextActive)) await loadTeamProjects();
                  return;
                }
                teamProjectTab = 'archived';
              }
              await loadTeamProjects();
            } catch (failure) { error.textContent = failure.message; archive.disabled = !project.can_archive; }
          });
        actions.append(archive);
        footer.append(totals, actions);
        card.append(select, headingRow, active, bar, footer);
        list.append(card);
      }
      if (!list.children.length) {
        const empty = document.createElement('p');
        empty.textContent = teamProjectTab === 'archived' ? 'Aucun projet archivé.' : 'Aucun projet actif.';
        list.append(empty);
      }
    }
    async function switchProject(project) {
      panel.querySelectorAll('.team-project-select').forEach(item => item.disabled = true);
      error.textContent = '';
      panel.classList.add('team-projects-switching');
      panel.setAttribute('aria-busy', 'true');
      const target = Array.from(panel.querySelectorAll('.team-project-card'))
        .find(item => item.dataset.project === project.id);
      target?.classList.add('team-project-pending');
      try {
        const result = await teamFetch('/api/auth/session', {
          method:'POST', headers:{'Content-Type':'application/json', 'X-CSRF-Token':session.csrf_token},
          body:JSON.stringify({project:project.id, switch_project:true})
        });
        if (!result.ok) throw new Error('Changement de projet refusé');
        const nextSession = await result.json();
        if (nextSession.project !== project.id) throw new Error('Session de projet incohérente');
        Object.assign(session, nextSession);
        projects = nextSession.projects || projects;
        window.devcoreActiveProject = project.id;
        const path = ['/cockpit', '/cockpit/terminal', '/index.html', '/index_terminal.html'].includes(location.pathname)
          ? location.pathname : '/cockpit';
        history.replaceState(null, '', path + '?' + new URLSearchParams({project:project.id}));
        const loaded = await refreshDashboard();
        if (!loaded) throw new Error('Données du projet indisponibles ; réessayez depuis la liste');
        reconnectTeamProjectStream();
        markSelectedProject();
        target?.classList.remove('team-project-pending');
        panel.classList.remove('team-projects-switching');
        panel.setAttribute('aria-busy', 'false');
        return true;
      } catch (failure) {
        error.textContent = failure.message;
        panel.classList.remove('team-projects-switching');
        panel.setAttribute('aria-busy', 'false');
        target?.classList.remove('team-project-pending');
        markSelectedProject();
        return false;
      }
    }
    renderProjects();
    panel.classList.remove('team-projects-initial', 'team-projects-loading', 'team-projects-switching');
    panel.setAttribute('aria-busy', 'false');
  } catch (failure) {
    panel.classList.remove('team-projects-loading');
    panel.setAttribute('aria-busy', 'false');
    if (!panel.querySelectorAll('.team-project-list').length) {
      panel.textContent = 'Liste des projets indisponible. Rechargez la page.';
    }
  }
}

function setupTeamProfile() {
  const profile = document.getElementById('team-profile');
  const logout = document.getElementById('team-logout');
  const error = document.getElementById('team-profile-error');
  if (!profile || !logout || !error) return;
  document.addEventListener('click', event => {
    if (!profile.contains(event.target)) profile.open = false;
  });
  logout.addEventListener('click', async event => {
    event.preventDefault();
    if (logout.dataset.busy === 'true') return;
    logout.dataset.busy = 'true';
    logout.setAttribute('aria-disabled', 'true');
    error.textContent = '';
    try {
      const sessionResponse = await teamFetch('/api/auth/session', {cache:'no-store'});
      if (!sessionResponse.ok) throw new Error('Session indisponible');
      const session = await sessionResponse.json();
      const response = await teamFetch('/api/auth/session', {
        method:'DELETE', credentials:'same-origin',
        headers:{'X-CSRF-Token':session.csrf_token}
      });
      if (!response.ok) throw new Error('Déconnexion impossible');
      location.assign('/login?' + new URLSearchParams({project:session.project}));
    } catch (failure) {
      error.textContent = failure.message;
      logout.dataset.busy = 'false';
      logout.removeAttribute('aria-disabled');
    }
  });
}

setupTeamProfile();
loadTeamProjects();

"""Real PostgreSQL session navigation on an isolated temporary cluster."""
import json
import os
from pathlib import Path
import socket
import subprocess

import pg8000.dbapi
import pytest


@pytest.fixture(scope='module')
def cluster(tmp_path_factory):
    root = tmp_path_factory.mktemp('navigation-postgres').resolve()
    binaries = Path('C:/Program Files/PostgreSQL/17/bin')
    if not (binaries/'initdb.exe').exists():
        pytest.skip('PostgreSQL 17 binaries required')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    data = root/'postgres'
    def command(*args):
        subprocess.run(list(map(str,args)),check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120)
    command(binaries/'initdb.exe','-D',data,'-U','fixture_owner','-A','trust','--encoding=UTF8')
    try:
        command(binaries/'pg_ctl.exe','-D',data,'-l',root/'postgres.log','-o',f'-h 127.0.0.1 -p {port}','start','-w')
        command(binaries/'psql.exe','-h','127.0.0.1','-p',port,'-U','fixture_owner','-d','postgres',
                '-v','ON_ERROR_STOP=1','-f',Path(__file__).resolve().parents[1]/'devcore_engine/persistence/schema.sql')
        yield port
    finally:
        command(binaries/'pg_ctl.exe','-D',data,'stop','-m','fast','-w')


@pytest.fixture
def navigation(cluster, tmp_path, monkeypatch):
    monkeypatch.setenv('DEVCORE_LOCAL_ROOT',str(tmp_path/'local'))
    monkeypatch.setenv('DEVCORE_DATA_ROOT',str(tmp_path/'data'))
    admin = pg8000.dbapi.connect(user='fixture_owner',host='127.0.0.1',port=cluster,database='postgres')
    cursor=admin.cursor()
    cursor.execute('TRUNCATE organizations,users CASCADE')
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='navigation_app'")
    if not cursor.fetchone():
        cursor.execute('CREATE ROLE navigation_app LOGIN NOBYPASSRLS')
    cursor.execute('GRANT USAGE ON SCHEMA public TO navigation_app')
    cursor.execute('GRANT SELECT ON users,projects,project_memberships,sessions TO navigation_app')
    cursor.execute('GRANT INSERT,UPDATE ON sessions TO navigation_app')
    cursor.execute("INSERT INTO organizations(id,name) VALUES ('o','Fixture')")
    cursor.execute("INSERT INTO workspaces(id,organization_id,name) VALUES ('w','o','Fixture')")
    cursor.execute("""INSERT INTO projects(id,workspace_id,name,root_path,status) VALUES
        ('alpha','w','Alpha','C:/fixture','active'),('beta','w','Beta <script>','C:/fixture','needs_review'),
        ('hidden','w','Private','C:/fixture','active'),('archived','w','Archived','C:/fixture','archived')""")
    from argon2 import PasswordHasher
    cursor.execute("INSERT INTO users(id,email,display_name,password_hash,status) VALUES ('alice','alice@fixture','Alice',%s,'active')",(PasswordHasher().hash('fixture-password'),))
    cursor.execute("""INSERT INTO project_memberships(id,project_id,user_id,role) VALUES
        ('a','alpha','alice','owner'),('b','beta','alice','reader'),('c','archived','alice','owner')""")
    admin.commit()
    dsn=f'postgresql://navigation_app@127.0.0.1:{cluster}/postgres'
    from devcore_engine.security.postgres_password_sessions import create_password_session
    session,secret=create_password_session(dsn,'alice','fixture-password','alpha','http://testserver')
    yield dsn,session,secret,admin
    admin.close()


def test_catalogue_rotation_role_and_cookie_revocation(navigation):
    from devcore_engine.security.postgres_project_navigation import accessible_projects,switch_project
    from devcore_engine.security.postgres_browser_sessions import authorize_session
    from devcore_engine.security.browser_sessions import csrf_for_session
    from devcore_engine.security.identity import AuthenticationRequired,ProjectAccessDenied
    dsn,session,secret,_=navigation
    assert [p['id'] for p in accessible_projects(dsn,secret,'http://testserver')]==['alpha','beta']
    with pytest.raises(ProjectAccessDenied):
        authorize_session(dsn,secret,'beta','task.read','http://testserver')
    changed,new_secret=switch_project(dsn,secret,'beta','http://testserver',csrf_for_session(secret))
    assert changed.project_id=='beta' and changed.expires_at==session.expires_at
    assert 'task.mutate' not in changed.actions
    with pytest.raises(AuthenticationRequired):
        authorize_session(dsn,secret,'alpha','task.read','http://testserver')
    authorize_session(dsn,new_secret,'beta','task.read','http://testserver')
    with pytest.raises(ProjectAccessDenied):
        authorize_session(dsn,new_secret,'alpha','task.read','http://testserver')


@pytest.mark.parametrize('target',['hidden','archived','bad-csrf','bad-origin','revoked-membership','bearer-scope'])
def test_navigation_denies_unauthorized_changes(navigation,target):
    # The parametrized target is a scenario; origin/CSRF are derived below.
    from devcore_engine.security.postgres_project_navigation import switch_project,accessible_projects
    from devcore_engine.security.postgres_browser_sessions import authorize_session
    from devcore_engine.security.browser_sessions import csrf_for_session
    from devcore_engine.security.identity import ProjectAccessDenied
    dsn,session,secret,admin=navigation
    cursor=admin.cursor()
    if target=='revoked-membership':
        cursor.execute("DELETE FROM project_memberships WHERE project_id='beta'")
    if target=='bearer-scope':
        cursor.execute("UPDATE sessions SET metadata=metadata-'password_admitted' WHERE id=%s",(session.session_id,))
    admin.commit()
    if target=='bearer-scope':
        assert [p['id'] for p in accessible_projects(dsn,secret,'http://testserver')]==['alpha']
    with pytest.raises(ProjectAccessDenied):
        switch_project(dsn,secret,target if target in ('hidden','archived') else 'beta',
                       'http://evil' if target=='bad-origin' else 'http://testserver',
                       'wrong' if target=='bad-csrf' else csrf_for_session(secret))
    authorize_session(dsn,secret,'alpha','task.read','http://testserver')


def test_http_session_projects_and_switch(navigation,monkeypatch):
    from fastapi.testclient import TestClient
    from devcore_api import create_app
    from devcore_engine.security.browser_sessions import csrf_for_session
    dsn,_,secret,_=navigation
    monkeypatch.setenv('DEVCORE_IDENTITY_READ_MODE','postgres')
    monkeypatch.setenv('DEVCORE_DATABASE_URL',dsn)
    client=TestClient(create_app(require_auth=True))
    client.cookies.set('devcore_session',secret)
    response=client.get('/api/auth/session')
    assert response.status_code==200
    assert [p['id'] for p in response.json()['projects']]==['alpha','beta']
    response=client.post('/api/auth/session',json={'switch_project':True,'project':'beta'},
                         headers={'Origin':'http://testserver','X-CSRF-Token':csrf_for_session(secret)})
    assert response.status_code==200, response.text
    assert response.json()['project']=='beta'
    assert 'httponly' in response.headers['set-cookie'].lower()
    client.cookies.clear()
    client.cookies.set('devcore_session',secret)
    assert client.get('/api/auth/session').status_code==401

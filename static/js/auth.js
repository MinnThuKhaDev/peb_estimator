/* ---------- session storage ---------- */
function getSession() {
  try { return JSON.parse(localStorage.getItem('peb_session') || 'null'); }
  catch (e) { return null; }
}
function setSession(s) { localStorage.setItem('peb_session', JSON.stringify(s)); }
function clearSession() { localStorage.removeItem('peb_session'); }

function authHeader() {
  const s = getSession();
  return s && s.token ? { 'Authorization': 'Bearer ' + s.token } : {};
}

function showLogin(show) {
  document.getElementById('loginModal').style.display = show ? 'flex' : 'none';
}

function doLogout() {
  clearSession();
  location.reload();
}

/* ---------- login flow ---------- */
let _pendingLogin = null; // {username, password} while waiting for a 2FA code

async function doLogin() {
  const username = document.getElementById('loginUser').value.trim();
  const password = document.getElementById('loginPass').value;
  const totpRow = document.getElementById('login2faRow');
  const totp_code = document.getElementById('loginTotp').value.trim();
  const errEl = document.getElementById('loginError');
  errEl.textContent = '';

  if (!username || !password) { errEl.textContent = 'Enter a username and password.'; return; }

  try {
    const resp = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, totp_code: totp_code || null })
    });
    const data = await resp.json();
    if (!resp.ok) { errEl.textContent = data.detail || 'Login failed.'; return; }

    if (data.requires_2fa) {
      totpRow.style.display = 'block';
      errEl.textContent = 'Enter your 2FA code to continue.';
      return;
    }

    setSession({ token: data.token, is_admin: data.is_admin, username });
    showLogin(false);
    afterLogin();
  } catch (e) {
    errEl.textContent = 'Could not reach the server: ' + e.message;
  }
}

function afterLogin() {
  const s = getSession();
  document.getElementById('whoAmI').textContent = 'Signed in as ' + s.username + (s.is_admin ? ' (admin)' : '');
  document.getElementById('adminNavItem').style.display = s.is_admin ? '' : 'none';
  if (typeof refreshHistory === 'function') refreshHistory();
  load2FAStatus();
  if (s.is_admin) loadUsers();
}

/* ---------- boot ---------- */
window.addEventListener('DOMContentLoaded', () => {
  const s = getSession();
  if (s && s.token) {
    showLogin(false);
    afterLogin();
  } else {
    showLogin(true);
  }
});

/* ---------- 2FA setup (any logged-in user) ---------- */
async function load2FAStatus() {
  // We don't have a dedicated "am I 2FA enabled" endpoint, so infer it from
  // the users list for admins, or just show the setup option for everyone.
  const statusEl = document.getElementById('twofaStatus');
  statusEl.textContent = 'Set up 2FA below, or disable it if you no longer want it.';
  document.getElementById('setup2faBtn').style.display = '';
  document.getElementById('disable2faBtn').style.display = '';
}

async function start2FASetup() {
  const box = document.getElementById('twofaSetupBox');
  try {
    const resp = await fetch('/api/auth/2fa/setup', { method: 'POST', headers: authHeader() });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Setup failed');
    document.getElementById('twofaSecret').textContent = data.secret;
    document.getElementById('twofaQr').src =
      'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + encodeURIComponent(data.provisioning_uri);
    box.style.display = 'block';
  } catch (e) {
    document.getElementById('twofaStatus').textContent = 'Error: ' + e.message;
  }
}

async function confirm2FA() {
  const code = document.getElementById('twofaConfirmCode').value.trim();
  const statusEl = document.getElementById('twofaConfirmStatus');
  try {
    const resp = await fetch('/api/auth/2fa/enable', {
      method: 'POST', headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Could not confirm code');
    statusEl.textContent = '2FA is now enabled on your account.';
    document.getElementById('twofaSetupBox').style.display = 'none';
  } catch (e) {
    statusEl.textContent = 'Error: ' + e.message;
  }
}

async function disable2FA() {
  if (!confirm('Turn off 2FA for your account?')) return;
  await fetch('/api/auth/2fa/disable', { method: 'POST', headers: authHeader() });
  document.getElementById('twofaStatus').textContent = '2FA disabled.';
}

/* ---------- admin: user management ---------- */
async function loadUsers() {
  const wrap = document.getElementById('usersTableWrap');
  try {
    const resp = await fetch('/api/users', { headers: authHeader() });
    const users = await resp.json();
    if (!resp.ok) throw new Error(users.detail || 'Could not load users');
    let html = `<table><thead><tr><th>Username</th><th>Role</th><th>2FA</th><th>Created</th><th></th></tr></thead><tbody>`;
    users.forEach(u => {
      html += `<tr><td>${u.username}</td><td>${u.is_admin ? 'Admin' : 'Standard'}</td>
        <td>${u.totp_enabled ? 'On' : 'Off'}</td><td>${(u.created_at || '').toString().slice(0,10)}</td>
        <td><button class="btn link" onclick="deleteUser(${u.id})">delete</button></td></tr>`;
    });
    html += '</tbody></table>';
    wrap.innerHTML = html;
  } catch (e) {
    wrap.innerHTML = '<p class="note" style="color:#c0392b">' + e.message + '</p>';
  }
}

async function createUser() {
  const username = document.getElementById('newUserName').value.trim();
  const password = document.getElementById('newUserPass').value;
  const is_admin = document.getElementById('newUserAdmin').value === 'true';
  const statusEl = document.getElementById('createUserStatus');
  try {
    const resp = await fetch('/api/users', {
      method: 'POST', headers: { ...authHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, is_admin })
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Could not create user');
    statusEl.textContent = 'Created "' + username + '".';
    document.getElementById('newUserName').value = '';
    document.getElementById('newUserPass').value = '';
    loadUsers();
  } catch (e) {
    statusEl.textContent = 'Error: ' + e.message;
  }
}

async function deleteUser(id) {
  if (!confirm('Delete this account?')) return;
  await fetch('/api/users/' + id, { method: 'DELETE', headers: authHeader() });
  loadUsers();
}

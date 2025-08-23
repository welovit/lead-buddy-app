// lead_app_frontend/app.js
// This script provides client‑side functionality for the Lead Buddy front‑end.
// It handles user registration, login, fetching categories and daily leads,
// updating lead statuses and adding notes.  The API endpoints should be
// served by the backend defined in lead_app_backend/lead_app_server.py.

(() => {
  const API_BASE = 'const API_BASE = 'https://lead-buddy-backend.onrender.com';
';

  // DOM elements
  const authSection = document.getElementById('auth-section');
  const mainSection = document.getElementById('main-section');
  const loginTab = document.getElementById('login-tab');
  const registerTab = document.getElementById('register-tab');
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const authError = document.getElementById('auth-error');
  const userNameSpan = document.getElementById('user-name');
  const logoutButton = document.getElementById('logout-button');
  const settingsButton = document.getElementById('settings-button');
  const settingsSection = document.getElementById('settings-section');
  const settingsForm = document.getElementById('settings-form');
  const settingsCancel = document.getElementById('settings-cancel');
  const settingsError = document.getElementById('settings-error');
  const categoriesList = document.getElementById('categories-list');
  const leadsContainer = document.getElementById('leads-container');
  const refreshLeadsButton = document.getElementById('refresh-leads');
  const leadsSection = document.getElementById('leads-section');

  // Manage leads elements
  const manageLeadsButton = document.getElementById('manage-leads-button');
  const manageLeadsSection = document.getElementById('manage-leads-section');
  const manageLeadsContainer = document.getElementById('manage-leads-container');
  const statusFilterSelect = document.getElementById('status-filter');
  const backToDailyButton = document.getElementById('back-to-daily');

  // Helper: switch between login and register forms
  function showLoginForm() {
    loginForm.classList.remove('hidden');
    registerForm.classList.add('hidden');
    loginTab.classList.add('active');
    registerTab.classList.remove('active');
    authError.textContent = '';
  }

  function showRegisterForm() {
    loginForm.classList.add('hidden');
    registerForm.classList.remove('hidden');
    loginTab.classList.remove('active');
    registerTab.classList.add('active');
    authError.textContent = '';
  }

  // Load token and user name from localStorage
  function loadSession() {
    const token = localStorage.getItem('token');
    const userName = localStorage.getItem('userName');
    return { token, userName };
  }

  function saveSession(token, userName) {
    localStorage.setItem('token', token);
    if (userName) localStorage.setItem('userName', userName);
  }

  function clearSession() {
    localStorage.removeItem('token');
    localStorage.removeItem('userName');
  }

  // Toggle sections based on authentication state
  function updateUIForAuth() {
    const { token, userName } = loadSession();
    if (token) {
      // Authenticated
      authSection.classList.add('hidden');
      mainSection.classList.remove('hidden');
      userNameSpan.textContent = userName || 'User';
      fetchCategories();
      fetchLeads();
      // Default view: show daily leads section and hide manage section
      leadsSection.classList.remove('hidden');
      manageLeadsSection.classList.add('hidden');
    } else {
      // Not authenticated
      authSection.classList.remove('hidden');
      mainSection.classList.add('hidden');
    }
  }

  // API calls
  async function apiRequest(path, options = {}) {
    const { token } = loadSession();
    const headers = options.headers || {};
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    if (options.body && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
    const response = await fetch(API_BASE + path, {
      ...options,
      headers,
    });
    if (response.status === 204) {
      return {};
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw data;
    }
    return data;
  }

  async function registerUser(event) {
    event.preventDefault();
    const name = document.getElementById('register-name').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const phone = document.getElementById('register-phone').value.trim();
    const company = document.getElementById('register-company').value.trim();
    const overview = document.getElementById('register-overview').value.trim();
    const timezone = document.getElementById('register-timezone').value.trim() || 'UTC';
    const countriesStr = document.getElementById('register-countries').value.trim();
    const categoriesStr = document.getElementById('register-categories').value.trim();
    const countries = countriesStr ? countriesStr.split(',').map(c => c.trim()).filter(Boolean) : [];
    const categories = categoriesStr ? categoriesStr.split(',').map(c => c.trim()).filter(Boolean).map(c => {
      const n = parseInt(c, 10);
      return isNaN(n) ? c : n;
    }) : [];
    try {
      await apiRequest('/register', {
        method: 'POST',
        body: JSON.stringify({
          name,
          email,
          password,
          phone,
          company_name: company,
          company_overview: overview,
          timezone,
          countries,
          categories,
        }),
      });
      // Auto login after successful registration
      await loginUserWithCredentials(email, password, name);
    } catch (err) {
      authError.textContent = err.error || 'Registration failed';
    }
  }

  async function loginUserWithCredentials(email, password, nameHint) {
    try {
      const data = await apiRequest('/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      // Save token and name
      saveSession(data.token, nameHint || email);
      // Update UI
      updateUIForAuth();
    } catch (err) {
      authError.textContent = err.error || 'Login failed';
    }
  }

  async function loginUser(event) {
    event.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    await loginUserWithCredentials(email, password, email);
  }

  async function fetchCategories() {
    try {
      const data = await apiRequest('/categories');
      // Render categories as tags
      categoriesList.innerHTML = '';
      if (data.categories && data.categories.length > 0) {
        data.categories.forEach(cat => {
          const span = document.createElement('span');
          span.textContent = `${cat.id}: ${cat.name}`;
          categoriesList.appendChild(span);
        });
      }
    } catch (err) {
      console.error('Failed to fetch categories', err);
    }
  }

  async function fetchLeads() {
    try {
      const data = await apiRequest('/leads/daily');
      renderLeads(data.leads || []);
    } catch (err) {
      if (err.error) {
        alert('Error: ' + err.error);
      } else {
        alert('Failed to fetch leads');
      }
    }
  }

  function renderLeads(leads) {
    leadsContainer.innerHTML = '';
    if (leads.length === 0) {
      const p = document.createElement('p');
      p.textContent = 'No leads available. Please check back later.';
      leadsContainer.appendChild(p);
      return;
    }
    leads.forEach(lead => {
      const card = document.createElement('div');
      card.className = 'lead-card';
      const title = document.createElement('h3');
      title.textContent = lead.full_name;
      card.appendChild(title);
      const details = document.createElement('div');
      details.className = 'details';
      details.innerHTML =
        `<strong>Company:</strong> ${lead.company} (${lead.category})<br>` +
        `<strong>Email:</strong> ${lead.email || 'N/A'}<br>` +
        `<strong>Phone:</strong> ${lead.phone || 'N/A'}<br>` +
        `<strong>Country:</strong> ${lead.country || 'N/A'}<br>` +
        `<strong>Overview:</strong> ${lead.company_overview || 'N/A'}<br>` +
        `<a href="${lead.company_website}" target="_blank">Company Website</a>`;
      card.appendChild(details);
      // Actions container
      const actions = document.createElement('div');
      actions.className = 'actions';
      // Status select
      const statusSelect = document.createElement('select');
      ['not_interested', 'maybe', 'interested'].forEach(value => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent =
          value === 'not_interested'
            ? 'Not Interested'
            : value === 'maybe'
            ? 'Maybe'
            : 'Interested';
        statusSelect.appendChild(option);
      });
      actions.appendChild(statusSelect);
      // Next action date
      const dateInput = document.createElement('input');
      dateInput.type = 'date';
      dateInput.className = 'hidden';
      actions.appendChild(dateInput);
      // Notes area
      const noteArea = document.createElement('textarea');
      noteArea.placeholder = 'Add a note...';
      noteArea.rows = 2;
      actions.appendChild(noteArea);
      // Buttons for status update and adding note
      const updateBtn = document.createElement('button');
      updateBtn.textContent = 'Update Status';
      actions.appendChild(updateBtn);
      const noteBtn = document.createElement('button');
      noteBtn.textContent = 'Save Note';
      actions.appendChild(noteBtn);
      card.appendChild(actions);
      leadsContainer.appendChild(card);

      // Show date input if status is maybe or interested
      statusSelect.addEventListener('change', () => {
        if (statusSelect.value === 'maybe' || statusSelect.value === 'interested') {
          dateInput.classList.remove('hidden');
        } else {
          dateInput.classList.add('hidden');
        }
      });
      // Update status handler
      updateBtn.addEventListener('click', async () => {
        const status = statusSelect.value;
        const nextDate = dateInput.value || null;
        try {
          await apiRequest('/lead_status', {
            method: 'POST',
            body: JSON.stringify({
              lead_id: lead.lead_id,
              status,
              next_action_date: nextDate,
            }),
          });
          alert('Status updated');
        } catch (err) {
          alert(err.error || 'Failed to update status');
        }
      });
      // Add note handler
      noteBtn.addEventListener('click', async () => {
        const content = noteArea.value.trim();
        if (!content) {
          alert('Please enter a note');
          return;
        }
        try {
          await apiRequest('/notes', {
            method: 'POST',
            body: JSON.stringify({
              lead_id: lead.lead_id,
              content,
            }),
          });
          alert('Note saved');
          noteArea.value = '';
        } catch (err) {
          alert(err.error || 'Failed to save note');
        }
      });
    });
  }

  // Fetch all leads (history) optionally filtered by status
  async function fetchAllLeads(status = '') {
    try {
      const query = status ? `?status=${encodeURIComponent(status)}` : '';
      const data = await apiRequest(`/leads${query}`);
      renderManageLeads(data.leads || []);
    } catch (err) {
      if (err.error) {
        alert('Error: ' + err.error);
      } else {
        alert('Failed to fetch leads history');
      }
    }
  }

  // Render leads in manage section
  function renderManageLeads(leads) {
    manageLeadsContainer.innerHTML = '';
    if (leads.length === 0) {
      const p = document.createElement('p');
      p.textContent = 'No leads found for the selected filter.';
      manageLeadsContainer.appendChild(p);
      return;
    }
    leads.forEach(lead => {
      const card = document.createElement('div');
      card.className = 'lead-card';
      const title = document.createElement('h3');
      title.textContent = lead.full_name;
      card.appendChild(title);
      const details = document.createElement('div');
      details.className = 'details';
      let nextActionText = lead.next_action_date ? `<br><strong>Next Action:</strong> ${lead.next_action_date}` : '';
      details.innerHTML =
        `<strong>Status:</strong> ${lead.status || 'N/A'}<br>` +
        `<strong>Company:</strong> ${lead.company} (${lead.category})<br>` +
        `<strong>Email:</strong> ${lead.email || 'N/A'}<br>` +
        `<strong>Phone:</strong> ${lead.phone || 'N/A'}<br>` +
        `<strong>Country:</strong> ${lead.country || 'N/A'}${nextActionText}<br>` +
        `<strong>Overview:</strong> ${lead.company_overview || 'N/A'}<br>` +
        `<a href="${lead.company_website}" target="_blank">Company Website</a>`;
      card.appendChild(details);
      // Existing notes
      if (lead.notes) {
        const notesDiv = document.createElement('div');
        notesDiv.className = 'notes';
        const pre = document.createElement('pre');
        pre.textContent = lead.notes;
        notesDiv.appendChild(pre);
        card.appendChild(notesDiv);
      }
      // Actions container for manage leads
      const actions = document.createElement('div');
      actions.className = 'actions';
      // Status select with current status as selected option. Include default statuses and current status if custom.
      const statusSelect = document.createElement('select');
      const statuses = ['not_interested', 'maybe', 'interested'];
      // Add custom status if not in default list
      if (lead.status && !statuses.includes(lead.status)) {
        statuses.push(lead.status);
      }
      statuses.forEach(value => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent =
          value === 'not_interested'
            ? 'Not Interested'
            : value === 'maybe'
            ? 'Maybe'
            : value === 'interested'
            ? 'Interested'
            : value;
        if (lead.status === value) option.selected = true;
        statusSelect.appendChild(option);
      });
      actions.appendChild(statusSelect);
      // Next action date input; prefill with lead.next_action_date
      const dateInput = document.createElement('input');
      dateInput.type = 'date';
      dateInput.value = lead.next_action_date || '';
      // Show date input only for maybe/interested statuses
      if (statusSelect.value === 'maybe' || statusSelect.value === 'interested') {
        dateInput.classList.remove('hidden');
      } else {
        dateInput.classList.add('hidden');
      }
      actions.appendChild(dateInput);
      // Note area for adding new note
      const noteArea = document.createElement('textarea');
      noteArea.placeholder = 'Add a note...';
      noteArea.rows = 2;
      actions.appendChild(noteArea);
      // Buttons
      const updateBtn = document.createElement('button');
      updateBtn.textContent = 'Update Status';
      actions.appendChild(updateBtn);
      const noteBtn = document.createElement('button');
      noteBtn.textContent = 'Save Note';
      actions.appendChild(noteBtn);
      card.appendChild(actions);
      manageLeadsContainer.appendChild(card);

      // Show/hide date input based on status
      statusSelect.addEventListener('change', () => {
        if (statusSelect.value === 'maybe' || statusSelect.value === 'interested') {
          dateInput.classList.remove('hidden');
        } else {
          dateInput.classList.add('hidden');
        }
      });
      // Update status handler
      updateBtn.addEventListener('click', async () => {
        const status = statusSelect.value;
        const nextDate = dateInput.value || null;
        try {
          await apiRequest('/lead_status', {
            method: 'POST',
            body: JSON.stringify({ lead_id: lead.lead_id, status, next_action_date: nextDate }),
          });
          alert('Status updated');
          // Refresh manage leads to reflect changes
          fetchAllLeads(statusFilterSelect.value);
        } catch (err) {
          alert(err.error || 'Failed to update status');
        }
      });
      // Add note handler
      noteBtn.addEventListener('click', async () => {
        const content = noteArea.value.trim();
        if (!content) {
          alert('Please enter a note');
          return;
        }
        try {
          await apiRequest('/notes', {
            method: 'POST',
            body: JSON.stringify({ lead_id: lead.lead_id, content }),
          });
          alert('Note saved');
          noteArea.value = '';
          // Refresh list to show new note
          fetchAllLeads(statusFilterSelect.value);
        } catch (err) {
          alert(err.error || 'Failed to save note');
        }
      });
    });
  }

  // Event listeners
  loginTab.addEventListener('click', showLoginForm);
  registerTab.addEventListener('click', showRegisterForm);
  loginForm.addEventListener('submit', loginUser);
  registerForm.addEventListener('submit', registerUser);
  logoutButton.addEventListener('click', () => {
    clearSession();
    updateUIForAuth();
  });
  refreshLeadsButton.addEventListener('click', fetchLeads);
  if (settingsButton) {
    settingsButton.addEventListener('click', () => {
      fetchUserProfile();
    });
  }
  if (settingsCancel) {
    settingsCancel.addEventListener('click', () => {
      settingsSection.classList.add('hidden');
      settingsError.textContent = '';
    });
  }
  if (settingsForm) {
    settingsForm.addEventListener('submit', updateUserProfile);
  }

  // Manage leads event listeners
  if (manageLeadsButton) {
    manageLeadsButton.addEventListener('click', () => {
      // Show manage section and fetch leads
      leadsSection.classList.add('hidden');
      manageLeadsSection.classList.remove('hidden');
      // Reset filter to current value (default '') and fetch
      fetchAllLeads(statusFilterSelect.value);
    });
  }
  if (backToDailyButton) {
    backToDailyButton.addEventListener('click', () => {
      manageLeadsSection.classList.add('hidden');
      leadsSection.classList.remove('hidden');
    });
  }
  if (statusFilterSelect) {
    statusFilterSelect.addEventListener('change', () => {
      fetchAllLeads(statusFilterSelect.value);
    });
  }

  // Initialize UI on page load
  updateUIForAuth();

  // Fetch user profile and populate settings form
  async function fetchUserProfile() {
    try {
      const profile = await apiRequest('/user/profile');
      // Populate fields
      document.getElementById('settings-phone').value = profile.phone || '';
      document.getElementById('settings-company').value = profile.company_name || '';
      document.getElementById('settings-overview').value = profile.company_overview || '';
      document.getElementById('settings-timezone').value = profile.timezone || '';
      document.getElementById('settings-countries').value = profile.countries ? profile.countries.join(', ') : '';
      document.getElementById('settings-categories').value = profile.categories ? profile.categories.map(c => c.id).join(', ') : '';
      settingsSection.classList.remove('hidden');
      settingsError.textContent = '';
    } catch (err) {
      alert(err.error || 'Failed to load profile');
    }
  }

  // Update user profile via API
  async function updateUserProfile(event) {
    event.preventDefault();
    // Gather updated values
    const phone = document.getElementById('settings-phone').value.trim();
    const company = document.getElementById('settings-company').value.trim();
    const overview = document.getElementById('settings-overview').value.trim();
    const timezone = document.getElementById('settings-timezone').value.trim();
    const countriesStr = document.getElementById('settings-countries').value.trim();
    const categoriesStr = document.getElementById('settings-categories').value.trim();
    const countries = countriesStr ? countriesStr.split(',').map(c => c.trim()).filter(Boolean) : [];
    const categories = categoriesStr ? categoriesStr.split(',').map(c => {
      const n = parseInt(c.trim(), 10);
      return isNaN(n) ? c.trim() : n;
    }).filter(Boolean) : [];
    const body = {};
    if (phone !== '') body.phone = phone;
    if (company !== '') body.company_name = company;
    if (overview !== '') body.company_overview = overview;
    if (timezone !== '') body.timezone = timezone;
    body.countries = countries;
    body.categories = categories;
    try {
      await apiRequest('/user/profile', {
        method: 'PUT',
        body: JSON.stringify(body),
      });
      settingsSection.classList.add('hidden');
      settingsError.textContent = '';
      // Refresh categories and leads to reflect new preferences
      fetchCategories();
      fetchLeads();
      alert('Profile updated');
    } catch (err) {
      settingsError.textContent = err.error || 'Failed to update profile';
    }
  }
})();

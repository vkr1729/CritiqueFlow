(function () {
  'use strict';

  var state = {
    folderPath: '',
    selectedFiles: [],
    fileList: [],
    lastResult: null,
    currentSessionId: null,
    currentSessionTitle: '',
    loading: false
  };

  var els = {};
  var saveTimers = {};

  function $(id) { return document.getElementById(id); }

  function init() {
    els.folderPath = $('folder-path');
    els.btnLoad = $('btn-load-files');
    els.fileList = $('file-list');
    els.queryInput = $('query-input');
    els.btnRun = $('btn-run-harness');
    els.loadingBar = $('loading-bar');
    els.queryError = $('query-error');
    els.exportSuccess = $('export-success');
    els.resultsSection = $('results-section');
    els.resultsMeta = $('results-meta');
    els.resultsContent = $('results-content');
    els.btnExport = $('btn-export');
    els.chainViewer = $('chain-viewer');
    els.statusDot = $('status-dot');
    els.footerStatus = $('footer-status');
    els.sessionList = $('session-list');
    els.btnClearHistory = $('btn-clear-history');
    els.envEditor = $('env-editor');
    els.promptAuditor = $('prompt-auditor-editor');
    els.promptEvaluator = $('prompt-evaluator-editor');
    els.skillsList = $('skills-list');
    els.btnLearnSkills = $('btn-learn-skills');
    els.summaryDashboard = $('summary-dashboard');
    els.confidenceValue = $('confidence-value');
    els.iterationsValue = $('iterations-value');
    els.verdictValue = $('verdict-value');
    els.filesValue = $('files-value');
    els.miniConfidence = $('mini-confidence');
    els.sessionBreadcrumb = $('session-breadcrumb');
    els.modelName = $('model-name');
    els.sidebarToggle = $('sidebar-collapse-toggle');
    els.chainToggle = $('chain-collapse-toggle');
    els.appLayout = $('app-layout');
    els.sidebarContent = document.querySelector('.sidebar-content');
    els.chainContent = document.querySelector('.chain-content');
    els.chainCollapsedIndicator = document.querySelector('.chain-collapsed-indicator');

    els.btnLoad.addEventListener('click', loadFiles);
    els.btnRun.addEventListener('click', runQuery);
    els.btnExport.addEventListener('click', exportMarkdown);
    els.btnClearHistory.addEventListener('click', clearAllHistory);
    els.btnLearnSkills.addEventListener('click', triggerLearning);
    els.queryInput.addEventListener('keydown', function (e) {
      if (e.ctrlKey && e.key === 'Enter') runQuery();
    });

    els.sidebarToggle.addEventListener('click', toggleSidebar);
    els.chainToggle.addEventListener('click', toggleChainPanel);

    document.querySelectorAll('.tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        switchTab(btn.dataset.tab);
      });
    });

    els.promptAuditor.addEventListener('blur', function () {
      savePrompt('auditor', els.promptAuditor.value);
    });
    els.promptEvaluator.addEventListener('blur', function () {
      savePrompt('evaluator', els.promptEvaluator.value);
    });

    // Event delegation for chain-viewer panel
    $('chain-viewer').addEventListener('click', function (e) {
      var step = e.target.closest('.timeline-step');
      if (step) {
        step.classList.toggle('expanded');
      }
    });

    // Restore collapse state
    restorePanelState();
    updateStatus('ready');
    loadSessionList();
    fetchModelName();
  }

  /* === Panel Collapse/Expand === */

  function toggleSidebar() {
    els.appLayout.classList.toggle('sidebar-collapsed');
    savePanelState();
  }

  function toggleChainPanel() {
    els.appLayout.classList.toggle('chain-collapsed');
    savePanelState();
  }

  function savePanelState() {
    localStorage.setItem('sidebarCollapsed', els.appLayout.classList.contains('sidebar-collapsed'));
    localStorage.setItem('chainCollapsed', els.appLayout.classList.contains('chain-collapsed'));
  }

  function restorePanelState() {
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
      els.appLayout.classList.add('sidebar-collapsed');
    }
    if (localStorage.getItem('chainCollapsed') === 'true') {
      els.appLayout.classList.add('chain-collapsed');
    }
  }

  /* === Tab System === */

  function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(function (b) {
      b.classList.toggle('active', b.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-panel').forEach(function (p) {
      p.classList.toggle('active', p.id === 'tab-' + tabName);
    });
    if (tabName === 'workspace') goToWorkspace();
    if (tabName === 'configure') goToConfigure();
  }

  function goToWorkspace() {
    loadSessionList();
  }

  function goToConfigure() {
    loadSettings();
    loadPrompt('auditor', els.promptAuditor);
    loadPrompt('evaluator', els.promptEvaluator);
    loadSkills();
  }

  /* === Status & Errors === */

  function updateStatus(stateName) {
    els.statusDot.className = 'status-dot ' + (stateName === 'loading' ? 'loading' : stateName === 'error' ? 'error' : '');
    var messages = { ready: 'Ready', loading: 'Processing...', error: 'Error' };
    els.footerStatus.textContent = messages[stateName] || 'Ready';
  }

  function showError(msg) {
    els.queryError.textContent = msg;
    els.queryError.classList.remove('hidden');
  }

  function hideError() {
    els.queryError.classList.add('hidden');
  }

  function setLoading(loading) {
    state.loading = loading;
    if (loading) {
      els.loadingBar.classList.remove('hidden');
      els.btnRun.disabled = true;
      els.btnRun.textContent = 'Analyzing...';
      els.queryInput.setAttribute('readonly', 'readonly');
      updateStatus('loading');
    } else {
      els.loadingBar.classList.add('hidden');
      els.btnRun.disabled = false;
      els.btnRun.textContent = 'Run Audit';
      els.queryInput.removeAttribute('readonly');
      updateStatus('ready');
    }
  }

  /* === Model Name === */

  function fetchModelName() {
    fetch('/api/settings')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        els.modelName.textContent = data.LLM_MODEL || 'Unknown';
      })
      .catch(function () {
        els.modelName.textContent = 'Unknown';
      });
  }

  /* === Files === */

  function loadFiles() {
    var folder = els.folderPath.value.trim();
    if (!folder) { showError('Please enter a working folder path.'); return; }
    hideError();
    state.folderPath = folder;

    fetch('/api/list-files', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: folder })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) { showError(data.error); return; }
      state.fileList = data.files || [];
      renderFileList();
    })
    .catch(function (err) { showError('Failed to load files: ' + err.message); });
  }

  function renderFileList() {
    if (state.fileList.length === 0) {
      els.fileList.innerHTML = '<div style="color:var(--text-muted);font-size:0.8rem;padding:8px;">No supported files found</div>';
      return;
    }
    var html = '';
    state.fileList.forEach(function (fname) {
      html += '<div class="file-item">';
      html += '<input type="checkbox" id="file-' + escapeHtml(fname) + '" value="' + escapeHtml(fname) + '">';
      html += '<label for="file-' + escapeHtml(fname) + '">' + escapeHtml(fname) + '</label>';
      html += '</div>';
    });
    els.fileList.innerHTML = html;

    document.querySelectorAll('#file-list input[type="checkbox"]').forEach(function (cb) {
      cb.addEventListener('change', function () {
        if (cb.checked) {
          if (state.selectedFiles.indexOf(cb.value) === -1) state.selectedFiles.push(cb.value);
        } else {
          state.selectedFiles = state.selectedFiles.filter(function (f) { return f !== cb.value; });
        }
      });
    });
  }

  /* === Query & Run === */

  function runQuery() {
    var query = els.queryInput.value.trim();
    if (!query) { showError('Please enter an audit query.'); return; }
    hideError();
    setLoading(true);
    els.resultsSection.classList.add('hidden');
    els.summaryDashboard.classList.add('hidden');
    els.resultsContent.textContent = '';
    els.miniConfidence.textContent = '\u2014';
    els.miniConfidence.className = 'mini-badge';

    var body = { query: query };
    if (state.folderPath && state.selectedFiles.length > 0) {
      body.folder_path = state.folderPath;
      body.selected_files = state.selectedFiles;
    }
    if (state.currentSessionId) {
      body.session_id = state.currentSessionId;
    }

    fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) { showError(data.error); setLoading(false); updateStatus('error'); return; }
      state.lastResult = data;
      if (data.session_id && !state.currentSessionId) {
        state.currentSessionId = data.session_id;
      }
      renderResults(data);
      renderSummaryDashboard(data);
      if (data.chain && data.chain.steps) {
        renderTimeline(data.chain.steps);
      }
      setLoading(false);
      updateStatus('ready');
      loadSessionList();
    })
    .catch(function (err) {
      showError('Query failed: ' + err.message);
      setLoading(false);
      updateStatus('error');
    });
  }

  function renderResults(data) {
    els.resultsMeta.textContent = 'Iterations: ' + data.total_iterations + ' | Early stopped: ' + (data.early_stopped ? 'Yes' : 'No');
    var html = renderMarkdown(data.final_output || '');
    els.resultsContent.innerHTML = html;
    els.resultsSection.classList.remove('hidden');
  }

  /* === Summary Dashboard === */

  function renderSummaryDashboard(data) {
    var chain = data.chain;
    var steps = chain ? chain.steps || [] : [];
    var confidence = null;

    for (var i = steps.length - 1; i >= 0; i--) {
      if (steps[i].role === 'evaluator_judgment') {
        try {
          var evalData = JSON.parse(steps[i].content);
          if (typeof evalData.confidence === 'number') {
            confidence = evalData.confidence;
          }
        } catch (e) {}
        break;
      }
    }

    if (confidence !== null) {
      els.confidenceValue.textContent = (confidence * 100).toFixed(0) + '%';
      if (confidence >= 0.85) {
        els.confidenceValue.className = 'metric-value text-success';
      } else if (confidence >= 0.6) {
        els.confidenceValue.className = 'metric-value text-warning';
      } else {
        els.confidenceValue.className = 'metric-value text-error';
      }
    } else {
      els.confidenceValue.textContent = '\u2014';
      els.confidenceValue.className = 'metric-value';
    }

    els.iterationsValue.textContent = data.total_iterations || '\u2014';

    var sufficient = data.early_stopped || (confidence !== null && confidence >= 0.85);
    els.verdictValue.textContent = sufficient ? 'Sufficient' : 'Needs Review';
    els.verdictValue.className = 'metric-value ' + (sufficient ? 'text-success' : 'text-warning');

    var fileCount = (data.referenced_files || (chain && chain.referenced_files) || []).length;
    els.filesValue.textContent = fileCount;

    els.summaryDashboard.classList.remove('hidden');
    els.summaryDashboard.classList.add('fade-in');
  }

  /* === Markdown === */

  function renderMarkdown(text) {
    if (!text) return '';
    var html = escapeHtml(text);
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function (_, lang, code) {
      return '<pre><code>' + code.replace(/\n$/, '') + '</code></pre>';
    });
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    var lines = html.split('\n');
    var inList = false;
    for (var i = 0; i < lines.length; i++) {
      var trimmed = lines[i].trim();
      if (trimmed.match(/^[\-\*]\s/)) {
        if (!inList) {
          lines[i] = '<ul><li>' + trimmed.replace(/^[\-\*]\s/, '') + '</li>';
          inList = true;
        } else {
          lines[i] = '<li>' + trimmed.replace(/^[\-\*]\s/, '') + '</li>';
        }
      } else if (inList && trimmed === '') {
        lines[i] = '</ul>';
        inList = false;
      } else if (inList) {
        lines[i] = '</ul>' + lines[i];
        inList = false;
      }
    }
    if (inList) lines.push('</ul>');
    html = lines.join('\n');
    html = html.replace(/\n\n/g, '<br><br>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* === Chain Timeline Renderer === */

  function renderTimeline(steps) {
    if (!steps || steps.length === 0) {
      els.chainViewer.innerHTML = '<div style="color:var(--text-muted);font-size:0.78rem;padding:12px;">No reasoning chain recorded.</div>';
      return;
    }

    var html = '';
    steps.forEach(function (step, index) {
      var role = step.role || 'unknown';
      var roleLabels = {
        user: 'User Query',
        llm_response: 'LLM Response',
        evaluator_judgment: 'Evaluator',
        harness_followup: 'Follow-Up',
        final_output: 'Final Output'
      };
      var label = roleLabels[role] || role;

      var confidenceBadge = '';
      if (role === 'evaluator_judgment') {
        try {
          var evalData = JSON.parse(step.content);
          if (typeof evalData.confidence === 'number') {
            var pct = (evalData.confidence * 100).toFixed(0) + '%';
            var badgeClass = evalData.confidence >= 0.85 ? 'high' : evalData.confidence >= 0.6 ? 'medium' : 'low';
            confidenceBadge = '<span class="confidence-badge ' + badgeClass + '">' + pct + '</span>';
          }
        } catch (e) {}
      }

      html += '<div class="timeline-step">';
      html += '<div class="timeline-dot ' + role + '"></div>';
      html += '<div class="timeline-card">';
      html += '<div class="timeline-card-header">';
      html += '<span class="step-role role-' + role + '">' + label + '</span>';
      html += confidenceBadge;
      html += '<span class="step-iter">Iteration ' + (step.iteration || '?') + '</span>';
      html += '</div>';
      html += '<div class="timeline-card-body">';
      html += '<div class="timeline-card-content">' + renderMarkdown(step.content || '') + '</div>';
      html += '</div>';
      html += '</div>';
      html += '</div>';
    });

    els.chainViewer.innerHTML = html;
    updateMiniConfidence(steps);
  }

  function updateMiniConfidence(steps) {
    var confidence = null;
    for (var i = steps.length - 1; i >= 0; i--) {
      if (steps[i].role === 'evaluator_judgment') {
        try {
          var evalData = JSON.parse(steps[i].content);
          if (typeof evalData.confidence === 'number') {
            confidence = evalData.confidence;
          }
        } catch (e) {}
        break;
      }
    }
    if (confidence !== null) {
      var pct = (confidence * 100).toFixed(0) + '%';
      var badgeClass = confidence >= 0.85 ? 'high' : confidence >= 0.6 ? 'medium' : 'low';
      els.miniConfidence.textContent = pct;
      els.miniConfidence.className = 'mini-badge confidence-badge ' + badgeClass;
    } else {
      els.miniConfidence.textContent = '\u2014';
      els.miniConfidence.className = 'mini-badge';
    }
  }

  /* === Export === */

  function exportMarkdown() {
    if (!state.lastResult || !state.lastResult.chain) {
      showError('No results to export. Run a query first.'); return;
    }
    var body = { chain_data: state.lastResult.chain };
    if (state.folderPath) { body.folder_path = state.folderPath; }
    fetch('/api/export', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) { showError('Export failed: ' + data.error); return; }
      hideError();
      els.exportSuccess.textContent = 'Exported to: ' + data.path;
      els.exportSuccess.classList.remove('hidden');
      setTimeout(function () { els.exportSuccess.classList.add('hidden'); }, 5000);
    })
    .catch(function (err) { showError('Export failed: ' + err.message); });
  }

  /* === Session History === */

  function loadSessionList() {
    fetch('/api/sessions?limit=50')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) return;
      renderSessionList(data.sessions || []);
    })
    .catch(function () {});
  }

  function renderSessionList(sessions) {
    if (sessions.length === 0) {
      els.sessionList.innerHTML = '<div style="color:var(--text-muted);font-size:0.8rem;padding:8px;">No sessions yet</div>';
      return;
    }
    var html = '';
    sessions.forEach(function (s) {
      var activeClass = s.id === state.currentSessionId ? ' active' : '';
      var date = (s.updated_at || s.created_at || '').substring(0, 16).replace('T', ' ');
      html += '<div class="session-item' + activeClass + '" data-id="' + s.id + '">';
      html += '<div class="session-title">' + escapeHtml(s.title) + '</div>';
      html += '<div class="session-meta">' + date + '</div>';
      html += '<button class="session-delete" data-id="' + s.id + '" title="Delete">&#10005;</button>';
      html += '</div>';
    });
    els.sessionList.innerHTML = html;

    document.querySelectorAll('.session-item').forEach(function (item) {
      item.addEventListener('click', function (e) {
        if (e.target.classList.contains('session-delete')) return;
        var sid = item.dataset.id;
        state.currentSessionId = sid;
        loadSessionDetail(sid);
        document.querySelectorAll('.session-item').forEach(function (el) {
          el.classList.toggle('active', el.dataset.id === sid);
        });
      });
    });

    document.querySelectorAll('.session-delete').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        deleteSession(btn.dataset.id);
      });
    });
  }

  function loadSessionDetail(sid) {
    fetch('/api/sessions/' + sid)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) return;
      state.currentSessionTitle = data.title || '';
      els.sessionBreadcrumb.textContent = truncate(state.currentSessionTitle, 40) || 'Session ' + sid.substring(0, 8);
      if (data.chain && data.chain.final_output) {
        renderResults(data.chain);
        renderSummaryDashboard(data.chain);
      }
      if (data.chain && data.chain.steps) {
        renderTimeline(data.chain.steps);
      }
      if (data.folder_path) {
        els.folderPath.value = data.folder_path;
        state.folderPath = data.folder_path;
        loadFiles();
      }
      if (data.chain && data.chain.final_output) {
        state.lastResult = {
          chain: data.chain,
          final_output: data.chain.final_output,
          total_iterations: data.chain.total_iterations,
          early_stopped: data.chain.early_stopped
        };
      }
    })
    .catch(function () {});
  }

  function truncate(str, maxLen) {
    if (!str) return '';
    return str.length > maxLen ? str.substring(0, maxLen) + '...' : str;
  }

  function deleteSession(sid) {
    fetch('/api/sessions/' + sid, { method: 'DELETE' })
    .then(function () {
      if (state.currentSessionId === sid) {
        state.currentSessionId = null;
        state.currentSessionTitle = '';
        els.sessionBreadcrumb.textContent = 'New Session';
      }
      loadSessionList();
    })
    .catch(function () {});
  }

  function clearAllHistory() {
    if (!confirm('Delete ALL session history? This cannot be undone.')) return;
    fetch('/api/sessions', { method: 'DELETE' })
    .then(function () {
      state.currentSessionId = null;
      state.currentSessionTitle = '';
      els.sessionBreadcrumb.textContent = 'New Session';
      loadSessionList();
    })
    .catch(function () {});
  }

  /* === Settings Editor === */

  function loadSettings() {
    fetch('/api/settings')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) return;
      renderSettings(data);
    })
    .catch(function () {});
  }

  function renderSettings(data) {
    var html = '';
    Object.keys(data).sort().forEach(function (key) {
      var val = data[key] || '';
      var isSecure = key.indexOf('API_KEY') !== -1 || key.indexOf('SECRET') !== -1;
      html += '<div class="env-row">';
      html += '<label title="' + key + '">' + key + '</label>';
      html += '<input type="' + (isSecure ? 'password' : 'text') + '" data-field="' + key + '" value="' + escapeHtml(val) + '">';
      html += '</div>';
    });
    els.envEditor.innerHTML = html;

    document.querySelectorAll('.env-row input').forEach(function (input) {
      input.addEventListener('input', function () {
        var field = input.dataset.field;
        var value = input.value;
        clearTimeout(saveTimers[field]);
        saveTimers[field] = setTimeout(function () {
          updateSetting(field, value);
        }, 600);
      });
    });
  }

  function updateSetting(field, value) {
    fetch('/api/settings/' + field, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: value })
    }).catch(function () {});
  }

  /* === Prompt Editor === */

  function loadPrompt(type, textarea) {
    fetch('/api/prompts/' + type)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) return;
      textarea.value = data.content || '';
    })
    .catch(function () {});
  }

  function savePrompt(type, content) {
    fetch('/api/prompts/' + type, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: content })
    }).catch(function () {});
  }

  /* === Skills === */

  function loadSkills() {
    fetch('/api/skills')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) return;
      renderSkills(data.skills || []);
    })
    .catch(function () {});
  }

  function renderSkills(skills) {
    if (skills.length === 0) {
      els.skillsList.innerHTML = '<div style="color:var(--text-muted);font-size:0.8rem;">No learned skills yet</div>';
      return;
    }
    var html = '';
    skills.forEach(function (skill) {
      var active = skill.is_active ? '' : ' inactive';
      html += '<div class="skill-card" data-id="' + skill.id + '">';
      html += '<div class="skill-text">' + escapeHtml(skill.skill_text) + '</div>';
      html += '<div class="skill-meta">';
      html += '<span>ID: ' + skill.id + '</span>';
      html += '<button class="skill-toggle' + active + '" data-id="' + skill.id + '" data-active="' + skill.is_active + '">' + (skill.is_active ? 'Active' : 'Inactive') + '</button>';
      html += '<button class="skill-delete" data-id="' + skill.id + '">Delete</button>';
      html += '</div></div>';
    });
    els.skillsList.innerHTML = html;

    document.querySelectorAll('.skill-toggle').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var newActive = btn.dataset.active === '1' ? 0 : 1;
        toggleSkill(btn.dataset.id, newActive);
      });
    });

    document.querySelectorAll('.skill-delete').forEach(function (btn) {
      btn.addEventListener('click', function () {
        deleteSkill(btn.dataset.id);
      });
    });
  }

  function toggleSkill(skillId, isActive) {
    fetch('/api/skills/' + skillId, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActive })
    })
    .then(function () { loadSkills(); })
    .catch(function () {});
  }

  function deleteSkill(skillId) {
    fetch('/api/skills/' + skillId, { method: 'DELETE' })
    .then(function () { loadSkills(); })
    .catch(function () {});
  }

  function triggerLearning() {
    els.btnLearnSkills.disabled = true;
    els.btnLearnSkills.textContent = 'Learning...';
    fetch('/api/skills/learn', { method: 'POST' })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      els.btnLearnSkills.disabled = false;
      els.btnLearnSkills.textContent = 'Learn from History';
      if (data.error) { showError(data.error); return; }
      loadSkills();
    })
    .catch(function (err) {
      els.btnLearnSkills.disabled = false;
      els.btnLearnSkills.textContent = 'Learn from History';
      showError('Learning failed: ' + err.message);
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();

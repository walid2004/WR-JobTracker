import React, { useState, useEffect, useRef } from 'react';
import {
  Briefcase,
  Search,
  RefreshCw,
  Plus,
  Mail,
  Calendar,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  Sparkles,
  ChevronRight,
  X,
  Trash2,
  Cpu,
  Layers,
  Send,
  Lock,
  Key,
  HelpCircle,
  Check,
  Power,
  Settings,
  ShieldCheck,
  Zap,
  Sliders,
  Gauge,
  Building2,
  TrendingUp,
  History,
  Timer,
  Sun,
  Moon,
  Cloud,
  Globe,
  Eye,
  EyeOff
} from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';

const CLOUD_PRESETS = [
  {
    id: 'github',
    name: 'GitHub Models',
    url: 'https://models.inference.ai.azure.com',
    model: 'gpt-4o-mini',
    models: ['gpt-4o-mini', 'gpt-4o', 'Mistral-large-2407', 'Meta-Llama-3.1-70B-Instruct', 'Phi-3.5-mini-instruct'],
    help: 'Use a GitHub Personal Access Token (PAT) with "Models" permissions.'
  },
  {
    id: 'openai',
    name: 'OpenAI (ChatGPT)',
    url: 'https://api.openai.com/v1',
    model: 'gpt-4o-mini',
    models: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    help: 'Enter your OpenAI API secret key (sk-...)'
  },
  {
    id: 'groq',
    name: 'Groq Cloud',
    url: 'https://api.groq.com/openai/v1',
    model: 'llama-3.1-70b-versatile',
    models: ['llama-3.1-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'],
    help: 'Enter your Groq API key (gsk_...)'
  },
  {
    id: 'mistral',
    name: 'Mistral AI',
    url: 'https://api.mistral.ai/v1',
    model: 'mistral-small-latest',
    models: ['mistral-small-latest', 'mistral-large-latest', 'codestral-latest'],
    help: 'Enter your Mistral API key'
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    url: 'https://openrouter.ai/api/v1',
    model: 'openai/gpt-4o-mini',
    models: ['openai/gpt-4o-mini', 'anthropic/claude-3.5-sonnet', 'meta-llama/llama-3.1-70b-instruct'],
    help: 'Enter your OpenRouter API key (sk-or-...)'
  }
];

const COLUMNS = [
  { id: 'APPLIED', title: 'Applied', statuses: ['APPLIED'] },
  { id: 'UNDER_REVIEW', title: 'Under Review', statuses: ['UNDER_REVIEW'] },
  { id: 'INTERVIEWS', title: 'Interviews & Assessments', statuses: ['INTERVIEW_INVITED', 'ASSESSMENT_INVITED', 'ACTION_REQUIRED'] },
  { id: 'OFFERS', title: 'Offers', statuses: ['OFFER_RECEIVED'] },
  { id: 'REJECTED', title: 'Rejected', statuses: ['REJECTED', 'ARCHIVED'] }
];

const PRESET_EMAILS = [
  {
    label: '1. BMW Application Received',
    sender: 'career@bmwgroup.com',
    subject: 'Confirmation: Application for Working Student Software Engineering (Ref #DE-89211)',
    body: 'Dear Applicant, Thank you for applying to the BMW Group. We have received your application for Working Student - Software Engineering (Ref #DE-89211). Our recruiting team will review your application.',
    threadId: 'thread_bmw_01'
  },
  {
    label: '2. BMW Offer Letter',
    sender: 'recruiting@bmwgroup.com',
    subject: 'Offer Letter: Working Student - Software Engineering (Ref #DE-89211)',
    body: 'Dear Candidate, Following your interviews, we are thrilled to offer you the position of Working Student - Software Engineering! Please review the attached contract.',
    threadId: 'thread_bmw_01'
  },
  {
    label: '3. Google Interview Invite',
    sender: 'talent@google.com',
    subject: 'Google Interview Invitation - Software Engineer',
    body: 'Hi! The team reviewed your background and would love to schedule a 45-minute technical screening interview. Please pick a slot by Friday: https://calendar.google.com/slots/swe',
    threadId: 'thread_google_01'
  }
];

function formatDate(dateStr) {
  if (!dateStr) return 'Recently';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return 'Recently';
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return 'Recently';
  }
}

function getAvatar(name) {
  if (!name || typeof name !== 'string') return 'WR';
  const clean = name.trim().replace(/[^a-zA-Z0-9]/g, '');
  return (clean.slice(0, 2) || 'WR').toUpperCase();
}

function AppLogo({ size = 20, className = "" }) {
  return (
    <svg
      width={size}
      height={(size * 121) / 135}
      viewBox="0 0 135 121"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ flexShrink: 0 }}
    >
      <path
        d="M88.5679 6.03929C176.568 70.8393 93.2345 49.0393 40.5679 30.0393L120.568 113.039L2.56787 70.0393"
        stroke="currentColor"
        strokeWidth="15"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CompanyLogo({ name, logoUrl, size = 40 }) {
  const [imgError, setImgError] = useState(false);

  if (!imgError && logoUrl) {
    return (
      <div className="company-avatar-box" style={{ width: size, height: size }}>
        <img
          src={logoUrl}
          alt={name}
          className="company-avatar-img"
          style={{ width: size * 0.7, height: size * 0.7 }}
          onError={() => setImgError(true)}
          loading="lazy"
        />
      </div>
    );
  }

  return (
    <div className="company-avatar-box" style={{ width: size, height: size }}>
      <span className="company-avatar-fallback" style={{ fontSize: size * 0.35 }}>
        {getAvatar(name)}
      </span>
    </div>
  );
}

export default function App() {
  const [applications, setApplications] = useState([]);
  const [stats, setStats] = useState({
    total_applications: 0,
    applied: 0,
    under_review: 0,
    interviews_assessments: 0,
    offers: 0,
    rejections: 0,
    action_needed: 0,
    response_rate_percent: 0
  });

  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('wr_theme') || 'light';
  });

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [aiProvider, setAiProvider] = useState('local'); // 'local' | 'custom_api'
  const [activeModel, setActiveModel] = useState('qwen3:8b');
  const [availableModels, setAvailableModels] = useState(['qwen3:8b']);
  const [customApiUrl, setCustomApiUrl] = useState('https://models.inference.ai.azure.com');
  const [customApiKey, setCustomApiKey] = useState('');
  const [customModelName, setCustomModelName] = useState('gpt-4o-mini');
  const [showApiKey, setShowApiKey] = useState(false);
  const [isTestingCustomApi, setIsTestingCustomApi] = useState(false);
  const [customApiTestResult, setCustomApiTestResult] = useState(null);
  const [scanDepth, setScanDepth] = useState(50);
  const [autoSyncInterval, setAutoSyncInterval] = useState(0);

  const [countdownSeconds, setCountdownSeconds] = useState(0);

  const [emailAccount, setEmailAccount] = useState(null);
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [isTestingConnection, setIsTestingConnection] = useState(false);

  const [syncProgress, setSyncProgress] = useState(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const syncPollRef = useRef(null);

  const searchInputRef = useRef(null);
  const [selectedApp, setSelectedApp] = useState(null);
  const [drawerTab, setDrawerTab] = useState('timeline'); // 'timeline' | 'insights'
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [notification, setNotification] = useState(null);
  const [lastExtractionResult, setLastExtractionResult] = useState(null);

  const [newCompany, setNewCompany] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [newRefId, setNewRefId] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [newStatus, setNewStatus] = useState('APPLIED');

  const [rawSender, setRawSender] = useState(PRESET_EMAILS[0].sender);
  const [rawSubject, setRawSubject] = useState(PRESET_EMAILS[0].subject);
  const [rawBody, setRawBody] = useState(PRESET_EMAILS[0].body);
  const [rawThreadId, setRawThreadId] = useState(PRESET_EMAILS[0].threadId);

  const [inputEmail, setInputEmail] = useState('');
  const [inputPassword, setInputPassword] = useState('');
  const [inputServer, setInputServer] = useState('imap.gmail.com');

  const showToast = (msg, type = 'info') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 5000);
  };

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const formatCountdown = (sec) => {
    if (!sec || sec <= 0 || isNaN(sec)) return '00:00';
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const fetchApplications = async () => {
    try {
      const res = await fetch(`${API_BASE}/applications`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setApplications(data);
        }
      }
    } catch (err) {
      console.error('Failed to fetch applications:', err);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const fetchEmailAccount = async () => {
    try {
      const res = await fetch(`${API_BASE}/email/account`);
      if (res.ok) {
        const data = await res.json();
        if (data.connected && data.account) {
          setEmailAccount(data.account);
          setInputEmail(data.account.email_address || '');
          setInputServer(data.account.imap_server || 'imap.gmail.com');
        } else {
          setEmailAccount(null);
        }
      }
    } catch (err) {
      console.error('Failed to fetch email account:', err);
    }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/settings`);
      if (res.ok) {
        const data = await res.json();
        if (data.ai_provider) setAiProvider(data.ai_provider);
        if (data.active_model) setActiveModel(data.active_model);
        if (data.available_models) setAvailableModels(data.available_models);
        if (data.custom_api_url) setCustomApiUrl(data.custom_api_url);
        if (data.custom_api_key !== undefined) setCustomApiKey(data.custom_api_key);
        if (data.custom_model_name) setCustomModelName(data.custom_model_name);
        if (data.scan_depth) setScanDepth(data.scan_depth);
        if (data.auto_sync_interval !== undefined) setAutoSyncInterval(data.auto_sync_interval);
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    }
  };

  const handleSaveSettings = async (partialUpdates = {}) => {
    try {
      const body = {
        ai_provider: aiProvider,
        active_model: activeModel,
        custom_api_url: customApiUrl,
        custom_api_key: customApiKey,
        custom_model_name: customModelName,
        scan_depth: scanDepth,
        auto_sync_interval: autoSyncInterval,
        ...partialUpdates
      };
      const res = await fetch(`${API_BASE}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (res.ok) {
        const data = await res.json();
        if (data.settings) {
          if (data.settings.ai_provider) setAiProvider(data.settings.ai_provider);
          if (data.settings.active_model) setActiveModel(data.settings.active_model);
          if (data.settings.custom_api_url) setCustomApiUrl(data.settings.custom_api_url);
          if (data.settings.custom_api_key !== undefined) setCustomApiKey(data.settings.custom_api_key);
          if (data.settings.custom_model_name) setCustomModelName(data.settings.custom_model_name);
          if (data.settings.scan_depth) setScanDepth(data.settings.scan_depth);
          if (data.settings.auto_sync_interval !== undefined) setAutoSyncInterval(data.settings.auto_sync_interval);
        }
        showToast('Settings saved successfully', 'info');
      }
    } catch (err) {
      showToast('Failed to save settings', 'error');
    }
  };

  const handleTestCustomApi = async () => {
    if (!customApiUrl || !customModelName) {
      showToast('Please enter both API Endpoint URL and Model Name', 'error');
      return;
    }
    setIsTestingCustomApi(true);
    setCustomApiTestResult(null);
    try {
      const res = await fetch(`${API_BASE}/models/test-custom-api`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_url: customApiUrl,
          api_key: customApiKey,
          model_name: customModelName
        })
      });
      const data = await res.json();
      setCustomApiTestResult(data);
      if (data.success) {
        showToast(`Connected to ${customModelName} in ${data.elapsed}s!`, 'success');
      } else {
        showToast(data.error || 'Connection test failed', 'error');
      }
    } catch (err) {
      setCustomApiTestResult({ success: false, error: 'Could not contact backend test service' });
      showToast('API test request failed', 'error');
    } finally {
      setIsTestingCustomApi(false);
    }
  };

  const handleSelectCloudPreset = (preset) => {
    setCustomApiUrl(preset.url);
    setCustomModelName(preset.model);
    setCustomApiTestResult(null);
  };

  const fetchAppDetails = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/applications/${id}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedApp(data);
      }
    } catch (err) {
      console.error('Failed to fetch application details:', err);
    }
  };

  const handleTriggerSync = async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    setSyncProgress({ is_syncing: true, current_step: `Initiating live inbox sync (Scan depth: ${scanDepth})...` });
    try {
      const res = await fetch(`${API_BASE}/sync-start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_emails: scanDepth })
      });
      if (!res.ok) {
        const err = await res.json();
        setIsSyncing(false);
        showToast(err.detail || 'Failed to start sync', 'error');
      }
    } catch (err) {
      setIsSyncing(false);
      showToast('Error communicating with sync engine', 'error');
    }
  };

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('wr_theme', theme);
  }, [theme]);

  useEffect(() => {
    if (autoSyncInterval > 0) {
      setCountdownSeconds(autoSyncInterval * 60);
    } else {
      setCountdownSeconds(0);
    }
  }, [autoSyncInterval]);

  useEffect(() => {
    if (autoSyncInterval <= 0) return;

    const timer = setInterval(() => {
      setCountdownSeconds((prev) => {
        if (prev <= 1) {
          if (!isSyncing && emailAccount) {
            handleTriggerSync();
          }
          return autoSyncInterval * 60;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [autoSyncInterval, isSyncing, emailAccount]);

  useEffect(() => {
    fetchApplications();
    fetchStats();
    fetchEmailAccount();
    fetchSettings();

    const handleKeyDown = (e) => {
      if (
        e.key === '/' &&
        document.activeElement !== searchInputRef.current &&
        !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)
      ) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (isSyncing) {
      syncPollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/sync-progress`);
          if (res.ok) {
            const data = await res.json();
            setSyncProgress(data);
            
            fetchApplications();
            fetchStats();

            if (!data.is_syncing) {
              setIsSyncing(false);
              clearInterval(syncPollRef.current);
              fetchEmailAccount();
              if (data.last_error) {
                showToast(`Sync Error: ${data.last_error}`, 'error');
              } else {
                showToast(data.current_step || 'Sync completed successfully!', 'success');
              }
            }
          }
        } catch (e) {
          console.error('Error polling sync progress:', e);
        }
      }, 1200);
    } else if (syncPollRef.current) {
      clearInterval(syncPollRef.current);
    }
    return () => {
      if (syncPollRef.current) clearInterval(syncPollRef.current);
    };
  }, [isSyncing]);

  const handleTestConnection = async () => {
    if (!inputEmail || !inputPassword) {
      setTestResult({ success: false, error: 'Please enter both your email address and 16-character App Password.' });
      return;
    }
    setIsTestingConnection(true);
    setTestResult(null);
    try {
      const res = await fetch(`${API_BASE}/email/test-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_address: inputEmail,
          password: inputPassword,
          imap_server: inputServer
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setTestResult({
          success: true,
          message: ` Connection Successful! Connected to ${data.email_address} on ${data.imap_server} (Found ${data.total_inbox_messages} emails in INBOX).`
        });
      } else {
        setTestResult({ success: false, error: data.detail || 'Connection failed.' });
      }
    } catch (err) {
      setTestResult({ success: false, error: 'Could not connect to backend.' });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleSaveAndConnect = async (e) => {
    e.preventDefault();
    if (!inputEmail || !inputPassword) {
      setTestResult({ success: false, error: 'Please enter both email and password.' });
      return;
    }
    setIsTestingConnection(true);
    try {
      const res = await fetch(`${API_BASE}/email/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_address: inputEmail,
          password: inputPassword,
          imap_server: inputServer
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setEmailAccount(data.account);
        setTestResult({ success: true, message: ' Account connected and saved successfully!' });
        showToast(`Connected to ${inputEmail}!`, 'success');
        setTimeout(() => setIsEmailModalOpen(false), 1200);
      } else {
        setTestResult({ success: false, error: data.detail || 'Connection failed.' });
      }
    } catch (err) {
      setTestResult({ success: false, error: 'Failed to save connection.' });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect this email inbox?')) return;
    try {
      await fetch(`${API_BASE}/email/disconnect`, { method: 'POST' });
      setEmailAccount(null);
      setInputPassword('');
      setTestResult(null);
      showToast('Email inbox disconnected.', 'info');
      setIsEmailModalOpen(false);
    } catch (err) {
      showToast('Failed to disconnect.', 'error');
    }
  };

  const handleManualCreate = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/applications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: newCompany,
          job_title: newTitle,
          job_reference_id: newRefId || null,
          location: newLocation || null,
          status: newStatus
        })
      });
      if (res.ok) {
        setIsAddModalOpen(false);
        setNewCompany('');
        setNewTitle('');
        setNewRefId('');
        setNewLocation('');
        await fetchApplications();
        await fetchStats();
        showToast('Application created successfully!', 'success');
      }
    } catch (err) {
      showToast('Error creating application.', 'error');
    }
  };

  const handleProcessCustomEmail = async (e) => {
    e.preventDefault();
    setIsSyncing(true);
    setLastExtractionResult(null);
    setSyncProgress({ is_syncing: true, current_step: ` Testing with ${activeModel}...` });
    try {
      const res = await fetch(`${API_BASE}/process-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sender: rawSender,
          subject: rawSubject,
          body: rawBody,
          email_thread_id: rawThreadId || null,
          received_at: new Date().toISOString()
        })
      });
      if (res.ok) {
        const result = await res.json();
        setLastExtractionResult(result);
        await fetchApplications();
        await fetchStats();
        if (result.matched_existing_application) {
          showToast(`Matched #${result.application_id} (${result.company_name})! Status -> ${result.status}`, 'success');
        } else {
          showToast(`Created card #${result.application_id} for ${result.company_name}!`, 'success');
        }
      } else {
        const errData = await res.json();
        showToast(errData.detail || 'Failed to extract email.', 'error');
      }
    } catch (err) {
      showToast('Extraction failed. Check backend.', 'error');
    } finally {
      setIsSyncing(false);
      setSyncProgress(null);
    }
  };

  const handleStatusChange = async (appId, newStage) => {
    try {
      const res = await fetch(`${API_BASE}/applications/${appId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStage })
      });
      if (res.ok) {
        await fetchApplications();
        await fetchStats();
        if (selectedApp && selectedApp.id === appId) {
          fetchAppDetails(appId);
        }
        showToast(`Moved to ${newStage}`, 'success');
      }
    } catch (err) {
      showToast('Failed to update status', 'error');
    }
  };

  const handleDeleteApp = async (appId) => {
    if (!window.confirm('Delete this application card?')) return;
    try {
      const res = await fetch(`${API_BASE}/applications/${appId}`, { method: 'DELETE' });
      if (res.ok) {
        setSelectedApp(null);
        await fetchApplications();
        await fetchStats();
        showToast('Application deleted.', 'info');
      }
    } catch (err) {
      showToast('Failed to delete application', 'error');
    }
  };

  const handleResetDb = async () => {
    if (!window.confirm('Reset all application data?')) return;
    try {
      await fetch(`${API_BASE}/reset-db`, { method: 'POST' });
      setSelectedApp(null);
      await fetchApplications();
      await fetchStats();
      showToast('Database reset.', 'info');
    } catch (err) {
      showToast('Failed to reset DB', 'error');
    }
  };

  const loadPreset = (preset) => {
    setRawSender(preset.sender);
    setRawSubject(preset.subject);
    setRawBody(preset.body);
    setRawThreadId(preset.threadId);
    setLastExtractionResult(null);
  };

  const filteredApps = (applications || []).filter((app) => {
    if (!app) return false;
    const q = (searchQuery || '').toLowerCase().trim();
    if (!q) return true;
    const comp = String(app.company_name || '').toLowerCase();
    const title = String(app.job_title || '').toLowerCase();
    const refId = String(app.job_reference_id || '').toLowerCase();
    return comp.includes(q) || title.includes(q) || refId.includes(q);
  });

  return (
    <div className="app-container">
      {}
      {notification && (
        <div style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          background: notification.type === 'error' ? 'var(--status-rejected-bg)' : 'var(--bg-surface)',
          color: notification.type === 'error' ? 'var(--status-rejected-text)' : 'var(--text-primary)',
          border: `1px solid ${notification.type === 'error' ? 'var(--status-rejected-border)' : 'var(--border-muted)'}`,
          padding: '8px 14px',
          borderRadius: 'var(--radius-sm)',
          fontSize: '0.8rem',
          fontWeight: 600,
          boxShadow: 'var(--shadow-md)',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          {notification.msg}
        </div>
      )}

      {}
      {isSyncing && syncProgress && (
        <div className="sync-banner">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <RefreshCw size={14} className="animate-spin" />
            <span>{syncProgress.current_step || 'Processing candidate emails with local model...'}</span>
          </div>
          {syncProgress.total_candidates > 0 && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.725rem', opacity: 0.9 }}>
              {syncProgress.emails_checked || 0} / {syncProgress.total_candidates} checked ({syncProgress.cards_updated || 0} updated)
            </span>
          )}
        </div>
      )}

      {}
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">
            <AppLogo size={18} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span className="brand-title">WR JobTracker</span>
            <span className="brand-badge">
              {aiProvider === 'custom_api' ? `Cloud: ${customModelName}` : (activeModel || 'AI').split(':')[0]}
            </span>
          </div>
        </div>

        <div className="nav-actions">
          {}
          {emailAccount ? (
            <div
              className="ai-status-pill"
              onClick={() => setIsEmailModalOpen(true)}
              title="Click to manage email inbox"
            >
              <span className="status-dot"></span>
              <span>{emailAccount.email_address}</span>
            </div>
          ) : (
            <button
              className="btn btn-secondary"
              onClick={() => { setTestResult(null); setIsEmailModalOpen(true); }}
              style={{ borderStyle: 'dashed' }}
            >
              <Mail size={14} />
              Connect Inbox
            </button>
          )}

          {}
          {emailAccount && (
            <button
              className="btn btn-primary"
              onClick={handleTriggerSync}
              disabled={isSyncing}
            >
              <RefreshCw size={13} className={isSyncing ? 'animate-spin' : ''} />
              {isSyncing ? 'Syncing...' : 'Sync Inbox'}
            </button>
          )}

          {}
          <button
            className="btn-icon"
            onClick={() => setIsSettingsOpen(true)}
            title="Settings & AI Studio (Appearance, Model, Depth, Auto-sync, Sandbox)"
          >
            <Settings size={16} />
          </button>

          {}
          <button
            className="btn btn-accent"
            onClick={() => setIsAddModalOpen(true)}
          >
            <Plus size={15} />
            New Application
          </button>
        </div>
      </header>

      {}
      <section className="stats-banner">
        <div className="stat-card">
          <div className="stat-info">
            <span className="stat-label">Total Applications</span>
            <span className="stat-value">{stats.total_applications}</span>
          </div>
          <span className="stat-tag">All Time</span>
        </div>

        <div className="stat-card">
          <div className="stat-info">
            <span className="stat-label">Interviews & Tests</span>
            <span className="stat-value">{stats.interviews_assessments}</span>
          </div>
          <span className="stat-tag" style={{ color: 'var(--status-interview-text)' }}>Active</span>
        </div>

        <div className="stat-card">
          <div className="stat-info">
            <span className="stat-label">Job Offers</span>
            <span className="stat-value">{stats.offers}</span>
          </div>
          <span className="stat-tag" style={{ color: 'var(--status-offer-text)' }}>Offered</span>
        </div>

        <div className="stat-card has-tooltip">
          <div className="stat-info">
            <span className="stat-label">Response Rate</span>
            <span className="stat-value">{stats.response_rate_percent}%</span>
          </div>
          <span className="stat-tag">Rate</span>

          <div className="tooltip-card">
            <strong>Response Rate Analysis</strong>
            Percentage of job applications that received direct feedback, assessment, or interview invitations beyond the initial receipt.
          </div>
        </div>
      </section>

      {}
      <div className="toolbar">
        <div className="search-input-wrapper">
          <Search size={14} className="search-icon" />
          <input
            ref={searchInputRef}
            type="text"
            className="search-input"
            placeholder="Search company, job role, or Reference ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <kbd className="search-kbd">/</kbd>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {autoSyncInterval > 0 ? (
            <div className="countdown-pill" title={`Auto-sync runs every ${autoSyncInterval} minutes`}>
              <Timer size={13} style={{ color: 'var(--status-offer-text)' }} className={isSyncing ? 'animate-spin' : ''} />
              <span>Next scan in: <strong>{isSyncing ? 'Scanning...' : formatCountdown(countdownSeconds)}</strong></span>
            </div>
          ) : (
            <div
              className="countdown-pill"
              onClick={() => setIsSettingsOpen(true)}
              style={{ cursor: 'pointer', opacity: 0.85 }}
              title="Click to enable automatic background scans"
            >
              <Timer size={13} style={{ color: 'var(--text-muted)' }} />
              <span>Auto-sync: <strong>Off</strong></span>
            </div>
          )}
        </div>
      </div>

      {}
      <main className="kanban-board">
        {COLUMNS.map((col) => {
          const colApps = filteredApps.filter((a) => a && col.statuses.includes(a.status));
          return (
            <div key={col.id} className="kanban-column">
              <div className="column-header">
                <div className="column-title-group">
                  <span className="column-title">{col.title}</span>
                </div>
                <span className="column-count">{colApps.length}</span>
              </div>

              <div className="column-cards-list">
                {colApps.map((app) => (
                  <div
                    key={app.id}
                    className="kanban-card"
                    onClick={() => { setDrawerTab('timeline'); fetchAppDetails(app.id); }}
                  >
                    <div className="card-top">
                      <div className="company-badge-group">
                        {}
                        <CompanyLogo name={app.company_name} logoUrl={app.logo_url} size={38} />
                        <div>
                          <div className="company-name">{app.company_name || 'Unknown Company'}</div>
                          <div className="job-title">{app.job_title || 'Position Applied'}</div>
                        </div>
                      </div>
                    </div>

                    {app.job_reference_id && (
                      <div>
                        <span className="ref-tag">#{String(app.job_reference_id)}</span>
                      </div>
                    )}

                    {app.action_required && app.status !== 'REJECTED' && (
                      <div className="action-alert">
                        <AlertCircle size={14} style={{ flexShrink: 0, marginTop: '1px' }} />
                        <span className="action-alert-text">{app.action_required}</span>
                      </div>
                    )}

                    <div className="card-footer">
                      <div className="email-pill">
                        <Mail size={12} />
                        <span>{app.email_count || 1} email{app.email_count !== 1 ? 's' : ''}</span>
                      </div>
                      <span>
                        {formatDate(app.updated_at)}
                      </span>
                    </div>
                  </div>
                ))}

                {colApps.length === 0 && (
                  <div style={{
                    padding: '2.5rem 1rem',
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                    fontSize: '0.8rem'
                  }}>
                    No applications
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </main>

      {}
      {selectedApp && (
        <div className="drawer-backdrop" onClick={() => setSelectedApp(null)}>
          <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <CompanyLogo name={selectedApp.company_name} logoUrl={selectedApp.logo_url} size={48} />
                <div>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>{selectedApp.company_name || 'Company Details'}</h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{selectedApp.job_title || 'Position'}</p>
                </div>
              </div>
              <button className="close-btn" onClick={() => setSelectedApp(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="drawer-body">
              {}
              <div className="drawer-tabs">
                <button
                  className={`drawer-tab ${drawerTab === 'timeline' ? 'active' : ''}`}
                  onClick={() => setDrawerTab('timeline')}
                >
                  Timeline &amp; Emails
                </button>
                <button
                  className={`drawer-tab ${drawerTab === 'insights' ? 'active' : ''}`}
                  onClick={() => setDrawerTab('insights')}
                >
                  Company Intelligence
                </button>
              </div>

              {}
              <div className="form-group">
                <label className="form-label">Application Status</label>
                <select
                  className="form-select"
                  value={selectedApp.status || 'APPLIED'}
                  onChange={(e) => handleStatusChange(selectedApp.id, e.target.value)}
                >
                  <option value="APPLIED">Applied</option>
                  <option value="UNDER_REVIEW">Under Review</option>
                  <option value="ASSESSMENT_INVITED">Online Assessment</option>
                  <option value="INTERVIEW_INVITED">Interview Invited</option>
                  <option value="OFFER_RECEIVED">Offer Received</option>
                  <option value="REJECTED">Rejected</option>
                  <option value="ARCHIVED">Archived</option>
                </select>
              </div>

              {}
              {selectedApp.action_required && (
                <div className="action-alert" style={{ fontSize: '0.85rem', padding: '12px 14px' }}>
                  <AlertCircle size={18} style={{ flexShrink: 0 }} />
                  <div>
                    <strong>Action Required: </strong>
                    {selectedApp.action_required}
                    {selectedApp.next_step_deadline && (
                      <div style={{ marginTop: '4px', fontSize: '0.75rem', opacity: 0.9 }}>
                        Deadline: {selectedApp.next_step_deadline}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {}
              {drawerTab === 'timeline' && (
                <div className="timeline-section">
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    Email Audit Trail ({selectedApp.timeline?.length || 0})
                  </div>
                  <div className="timeline-list">
                    {selectedApp.timeline?.map((event) => (
                      <div key={event.id} className="timeline-item">
                        <div className="timeline-dot"></div>
                        <div className="timeline-meta">
                          <span>{event.sender || 'Unknown Sender'}</span>
                          <span>{formatDate(event.received_at)}</span>
                        </div>
                        <div className="timeline-subject">{event.subject || 'No Subject'}</div>
                        <div className="timeline-summary">{event.summary || 'Email logged.'}</div>
                        
                        {event.email_deep_link && (
                          <div style={{ marginTop: '8px' }}>
                            <a
                              href={event.email_deep_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn btn-secondary"
                              style={{ padding: '5px 12px', fontSize: '0.75rem' }}
                            >
                              <ExternalLink size={12} />
                              Open in Gmail
                            </a>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {}
              {drawerTab === 'insights' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  {}
                  <div className="insights-grid">
                    <div className="insight-metric-box">
                      <span className="insight-metric-label">Total Applied</span>
                      <span className="insight-metric-val">{selectedApp.company_insights?.total_applications_to_company || 1} roles</span>
                    </div>

                    <div className="insight-metric-box">
                      <span className="insight-metric-label">Company Response Rate</span>
                      <span className="insight-metric-val" style={{ color: 'var(--accent-blue)' }}>
                        {selectedApp.company_insights?.company_response_rate_percent || 0}%
                      </span>
                    </div>

                    <div className="insight-metric-box">
                      <span className="insight-metric-label">Avg Turnaround</span>
                      <span className="insight-metric-val" style={{ fontSize: '1.05rem' }}>
                        {selectedApp.company_insights?.avg_turnaround_days ? `${selectedApp.company_insights.avg_turnaround_days} days` : 'Pending'}
                      </span>
                    </div>

                    <div className="insight-metric-box">
                      <span className="insight-metric-label">Active Roles</span>
                      <span className="insight-metric-val" style={{ color: 'var(--accent-emerald)' }}>
                        {selectedApp.company_insights?.active_roles_count || 1}
                      </span>
                    </div>
                  </div>

                  {}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Other Roles Applied at {selectedApp.company_name} ({selectedApp.company_insights?.other_applications?.length || 0})
                    </div>

                    {selectedApp.company_insights?.other_applications?.length > 0 ? (
                      <div className="past-roles-list">
                        {selectedApp.company_insights.other_applications.map((other) => (
                          <div
                            key={other.id}
                            className="past-role-item"
                            onClick={() => fetchAppDetails(other.id)}
                            title="Click to inspect this application"
                          >
                            <div>
                              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                                {other.job_title}
                              </div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                                Applied {formatDate(other.created_at)} • {other.email_count} emails
                              </div>
                            </div>
                            <span className="ref-tag">
                              {other.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '0.5rem 0' }}>
                        No other applications found for this company yet.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {}
              <div style={{ paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
                <button
                  className="btn btn-danger"
                  onClick={() => handleDeleteApp(selectedApp.id)}
                  style={{ width: '100%', justifyContent: 'center' }}
                >
                  <Trash2 size={14} />
                  Delete Application Card
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {}
      {isSettingsOpen && (
        <div className="modal-backdrop" onClick={() => setIsSettingsOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>Settings &amp; Model Configuration</h3>
              <button className="close-btn" onClick={() => setIsSettingsOpen(false)}>
                <X size={16} />
              </button>
            </div>

            {}
            <div className="form-group">
              <label className="form-label">
                Interface Appearance
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  className={`btn ${theme === 'light' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flex: 1, justifyContent: 'center' }}
                  onClick={() => setTheme('light')}
                >
                  Light Mode (Default)
                </button>
                <button
                  type="button"
                  className={`btn ${theme === 'dark' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flex: 1, justifyContent: 'center' }}
                  onClick={() => setTheme('dark')}
                >
                  Dark Mode
                </button>
              </div>
            </div>

            {}
            <div className="form-group">
              <label className="form-label">
                AI Engine &amp; Extraction Model
              </label>
              
              {}
              <div className="provider-toggle-group" style={{ marginBottom: '8px' }}>
                <button
                  type="button"
                  className={`provider-toggle-btn ${aiProvider === 'local' ? 'active' : ''}`}
                  onClick={() => {
                    setAiProvider('local');
                    handleSaveSettings({ ai_provider: 'local' });
                  }}
                >
                  <Cpu size={14} />
                  <span>Local GPU (Ollama)</span>
                </button>
                <button
                  type="button"
                  className={`provider-toggle-btn ${aiProvider === 'custom_api' ? 'active' : ''}`}
                  onClick={() => {
                    setAiProvider('custom_api');
                    handleSaveSettings({ ai_provider: 'custom_api' });
                  }}
                >
                  <Cloud size={14} />
                  <span>Cloud API / GitHub Models</span>
                </button>
              </div>

              {}
              {aiProvider === 'local' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <select
                    className="form-select"
                    value={activeModel}
                    onChange={(e) => {
                      const newModel = e.target.value;
                      setActiveModel(newModel);
                      handleSaveSettings({ active_model: newModel, ai_provider: 'local' });
                    }}
                  >
                    {availableModels.map((m) => (
                      <option key={m} value={m}>
                        {m} {m === 'qwen2.5:3b' ? '(Fastest ~0.6s)' : m === 'qwen3:8b' ? '(Deep ATS Parser)' : ''}
                      </option>
                    ))}
                  </select>
                  <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                    Running locally on your RTX 3070 GPU via local Ollama. Zero external network calls.
                  </span>
                </div>
              )}

              {}
              {aiProvider === 'custom_api' && (
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  background: 'var(--bg-subtle)',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)'
                }}>
                  {}
                  <div>
                    <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                      Quick Cloud Presets:
                    </span>
                    <div className="preset-chip-list">
                      {CLOUD_PRESETS.map((preset) => {
                        const isMatch = customApiUrl.includes(preset.id) || (preset.id === 'github' && customApiUrl.includes('azure'));
                        return (
                          <button
                            key={preset.id}
                            type="button"
                            className={`preset-chip ${isMatch ? 'active' : ''}`}
                            onClick={() => handleSelectCloudPreset(preset)}
                          >
                            {preset.name}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {}
                  <div className="form-group">
                    <label className="form-label" style={{ fontSize: '0.7rem' }}>
                      API Base URL / Endpoint
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="https://models.inference.ai.azure.com or https://api.openai.com/v1"
                      value={customApiUrl}
                      onChange={(e) => setCustomApiUrl(e.target.value)}
                    />
                  </div>

                  {}
                  <div className="form-group">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <label className="form-label" style={{ fontSize: '0.7rem' }}>
                        API Key / GitHub Token
                      </label>
                      <button
                        type="button"
                        onClick={() => setShowApiKey(!showApiKey)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--text-muted)',
                          fontSize: '0.675rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '3px'
                        }}
                      >
                        {showApiKey ? <EyeOff size={12} /> : <Eye size={12} />}
                        <span>{showApiKey ? 'Hide' : 'Show'}</span>
                      </button>
                    </div>
                    <input
                      type={showApiKey ? 'text' : 'password'}
                      className="form-input"
                      placeholder="ghp_... / sk-... / gsk_..."
                      value={customApiKey}
                      onChange={(e) => setCustomApiKey(e.target.value)}
                    />
                    <span style={{ fontSize: '0.675rem', color: 'var(--text-muted)' }}>
                      Stored securely in your local SQLite database on this machine.
                    </span>
                  </div>

                  {}
                  <div className="form-group">
                    <label className="form-label" style={{ fontSize: '0.7rem' }}>
                      Model Identifier
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. gpt-4o-mini, Mistral-large-2407, llama-3.1-70b-versatile"
                      value={customModelName}
                      onChange={(e) => setCustomModelName(e.target.value)}
                    />
                  </div>

                  {}
                  {customApiTestResult && (
                    <div style={{
                      padding: '8px 10px',
                      borderRadius: 'var(--radius-xs)',
                      fontSize: '0.725rem',
                      background: customApiTestResult.success ? 'var(--status-offer-bg)' : 'var(--status-rejected-bg)',
                      color: customApiTestResult.success ? 'var(--status-offer-text)' : 'var(--status-rejected-text)',
                      border: `1px solid ${customApiTestResult.success ? 'var(--status-offer-border)' : 'var(--status-rejected-border)'}`,
                      lineHeight: 1.35
                    }}>
                      {customApiTestResult.success ? (
                        <div>
                          <strong>Verified!</strong> {customApiTestResult.message}
                        </div>
                      ) : (
                        <div>
                          <strong>Error:</strong> {customApiTestResult.error}
                        </div>
                      )}
                    </div>
                  )}

                  {}
                  <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={handleTestCustomApi}
                      disabled={isTestingCustomApi}
                      style={{ flex: 1, justifyContent: 'center' }}
                    >
                      <Zap size={13} className={isTestingCustomApi ? 'animate-spin' : ''} />
                      {isTestingCustomApi ? 'Testing Handshake...' : 'Test Connection'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => handleSaveSettings({
                        ai_provider: 'custom_api',
                        custom_api_url: customApiUrl,
                        custom_api_key: customApiKey,
                        custom_model_name: customModelName
                      })}
                      style={{ flex: 1, justifyContent: 'center' }}
                    >
                      <Check size={13} />
                      Save &amp; Activate
                    </button>
                  </div>
                </div>
              )}
            </div>

            {}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label className="form-label">
                  Scan Depth (Emails to Check)
                </label>
                <span style={{ fontWeight: 700, fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}>{scanDepth} emails</span>
              </div>
              <input
                type="range"
                min="10"
                max="250"
                step="10"
                value={scanDepth}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  setScanDepth(val);
                  handleSaveSettings({ scan_depth: val });
                }}
                style={{ width: '100%', cursor: 'pointer' }}
              />
            </div>

            {}
            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Timer size={14} style={{ color: '#10b981' }} />
                Automatic Periodic Sync
              </label>
              <select
                className="form-select"
                value={autoSyncInterval}
                onChange={(e) => handleSaveSettings({ auto_sync_interval: parseInt(e.target.value, 10) })}
              >
                <option value={0}>Disabled (Manual Sync Only)</option>
                <option value={5}>Every 5 Minutes</option>
                <option value={15}>Every 15 Minutes</option>
                <option value={30}>Every 30 Minutes</option>
                <option value={60}>Every 1 Hour</option>
              </select>
            </div>

            {}
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-lg)',
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.85rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 800 }}> Test AI Parser Sandbox</span>
                <div style={{ display: 'flex', gap: '4px' }}>
                  {PRESET_EMAILS.map((p, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className="btn btn-secondary"
                      style={{ fontSize: '0.7rem', padding: '3px 8px' }}
                      onClick={() => loadPreset(p)}
                    >
                      Preset {idx + 1}
                    </button>
                  ))}
                </div>
              </div>

              <form onSubmit={handleProcessCustomEmail} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <input
                  type="text"
                  required
                  className="form-input"
                  placeholder="Sender"
                  value={rawSender}
                  onChange={(e) => setRawSender(e.target.value)}
                  style={{ fontSize: '0.8rem' }}
                />
                <input
                  type="text"
                  required
                  className="form-input"
                  placeholder="Subject"
                  value={rawSubject}
                  onChange={(e) => setRawSubject(e.target.value)}
                  style={{ fontSize: '0.8rem' }}
                />
                <textarea
                  rows={2}
                  required
                  className="form-textarea"
                  placeholder="Body content"
                  value={rawBody}
                  onChange={(e) => setRawBody(e.target.value)}
                  style={{ fontSize: '0.8rem' }}
                />

                {lastExtractionResult && (
                  <div style={{
                    background: 'var(--avatar-bg)',
                    border: '1px solid var(--border-hover)',
                    borderRadius: 'var(--radius-md)',
                    padding: '8px 10px',
                    fontSize: '0.75rem'
                  }}>
                    <div style={{ color: '#60a5fa', fontWeight: 700, marginBottom: '4px' }}>
                       Parsed Status: {lastExtractionResult.status} ({lastExtractionResult.company_name})
                    </div>
                    <pre style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', overflowX: 'auto' }}>
                      {JSON.stringify(lastExtractionResult.extraction, null, 2)}
                    </pre>
                  </div>
                )}

                <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-end', fontSize: '0.8rem' }} disabled={isSyncing}>
                  <Send size={12} />
                  {isSyncing ? 'Running...' : 'Run Parser'}
                </button>
              </form>
            </div>

            {}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
              <button
                type="button"
                className="btn btn-danger"
                onClick={handleResetDb}
                style={{ fontSize: '0.775rem' }}
              >
                Reset Database
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setIsSettingsOpen(false)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {}
      {isEmailModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsEmailModalOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Lock size={18} style={{ color: emailAccount ? '#10b981' : '#60a5fa' }} />
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800 }}>
                  {emailAccount ? 'Connected Email Account' : 'Connect Live Email Inbox'}
                </h3>
              </div>
              <button className="close-btn" onClick={() => setIsEmailModalOpen(false)}><X size={18} /></button>
            </div>

            {testResult && (
              <div style={{
                background: testResult.success ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                border: `1px solid ${testResult.success ? 'rgba(16, 185, 129, 0.4)' : 'rgba(244, 63, 94, 0.4)'}`,
                color: testResult.success ? '#10b981' : '#f43f5e',
                padding: '12px 14px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.85rem',
                lineHeight: 1.4,
                whiteSpace: 'pre-line'
              }}>
                <strong>{testResult.success ? 'Handshake Success:' : 'Connection Error:'}</strong>
                <p style={{ marginTop: '4px' }}>{testResult.success ? testResult.message : testResult.error}</p>
              </div>
            )}

            {emailAccount && (
              <div style={{
                background: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 14px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 800, color: '#10b981' }}>
                     Connected: {emailAccount.email_address}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Server: {emailAccount.imap_server} • Total Synced: {emailAccount.total_synced_cards} cards
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-danger"
                  style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                  onClick={handleDisconnect}
                >
                  <Power size={12} />
                  Disconnect
                </button>
              </div>
            )}

            <form onSubmit={handleSaveAndConnect} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div className="form-group">
                <label className="form-label">Email Provider</label>
                <select
                  className="form-select"
                  value={inputServer}
                  onChange={(e) => setInputServer(e.target.value)}
                >
                  <option value="imap.gmail.com">Gmail (imap.gmail.com)</option>
                  <option value="outlook.office365.com">Outlook / Office 365 (outlook.office365.com)</option>
                  <option value="imap.mail.yahoo.com">Yahoo Mail (imap.mail.yahoo.com)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Email Address *</label>
                <input
                  type="email"
                  required
                  className="form-input"
                  placeholder="your.name@gmail.com"
                  value={inputEmail}
                  onChange={(e) => setInputEmail(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">16-Character App Password *</label>
                <input
                  type="password"
                  required={!emailAccount}
                  className="form-input"
                  placeholder={emailAccount ? 'Enter new password to update...' : 'xxxx xxxx xxxx xxxx'}
                  value={inputPassword}
                  onChange={(e) => setInputPassword(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleTestConnection}
                  disabled={isTestingConnection}
                >
                  <Key size={14} />
                  {isTestingConnection ? 'Testing...' : 'Test Connection'}
                </button>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setIsEmailModalOpen(false)}>
                    Close
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={isTestingConnection}>
                    <Check size={14} />
                    Save &amp; Connect
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {}
      {isAddModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsAddModalOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 800 }}>Add Job Application Card</h3>
              <button className="close-btn" onClick={() => setIsAddModalOpen(false)}><X size={18} /></button>
            </div>

            <form onSubmit={handleManualCreate} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Company Name *</label>
                <input
                  type="text"
                  required
                  className="form-input"
                  placeholder="e.g. BMW Group, Google, Stripe"
                  value={newCompany}
                  onChange={(e) => setNewCompany(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Job Title *</label>
                <input
                  type="text"
                  required
                  className="form-input"
                  placeholder="e.g. Working Student - Software Engineer"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Requisition / Ref ID (Optional)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. DE-89211 or REQ-1049"
                  value={newRefId}
                  onChange={(e) => setNewRefId(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Initial Status</label>
                <select
                  className="form-select"
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                >
                  <option value="APPLIED">Applied</option>
                  <option value="UNDER_REVIEW">Under Review</option>
                  <option value="INTERVIEW_INVITED">Interview Invited</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsAddModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create Card
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

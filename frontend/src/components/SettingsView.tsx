import React, { useEffect, useState } from 'react';
import {
  Sliders,
  HardDrives,
  Key,
  Broadcast,
  QrCode,
  Check,
  Copy,
  Trash,
  Plus,
  WarningCircle,
  ShieldCheck,
  CheckCircle,
  Sparkle,
  Compass,
  FilmStrip,
  CircleNotch,
  Robot,
  Pause,
  Flask,
} from '@phosphor-icons/react';
import { api } from '../services/api';
import {
  ApiKeyCreateResponse,
  ApiKeyModel,
  AutomationSettings,
  AutomationSettingsUpdateRequest,
  ProfileModel,
  RuleModel,
  SettingsResponse,
  SettingsUpdateRequest,
  StorageStatusResponse,
  WebhookDeliveryModel,
  WebhookModel,
} from '../types';
import { StorageManagementCard } from './Storage/StorageManagementCard';

export interface SettingsViewProps {
  onSettingsChanged?: (updated: SettingsResponse) => void;
  initialTab?: 'retention' | 'automation' | 'features' | 'profiles' | 'rules' | 'keys' | 'webhooks' | 'integrations';
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  onSettingsChanged,
  initialTab = 'retention',
}) => {
  const [activeTab, setActiveTab] = useState<
    'retention' | 'automation' | 'features' | 'profiles' | 'rules' | 'keys' | 'webhooks' | 'integrations'
  >(initialTab);

  // Storage & Retention State
  const [settings, setSettings] = useState<SettingsResponse>({
    retention_enabled: false,
    retention_days: 7,
    allowed_retention_days: [7, 14, 21, 30],
  });
  const [retentionUpdating, setRetentionUpdating] = useState(false);
  const [retentionSuccess, setRetentionSuccess] = useState(false);

  // Storage & Volume Diagnostics State
  const [storageStatus, setStorageStatus] = useState<StorageStatusResponse | null>(null);
  const [storageLoading, setStorageLoading] = useState(false);

  // Media Discovery State
  const [discoveryEnabled, setDiscoveryEnabled] = useState(false);
  const [tmdbEnabled, setTmdbEnabled] = useState(false);
  const [tmdbApiKey, setTmdbApiKey] = useState('');
  const [prowlarrEnabled, setProwlarrEnabled] = useState(false);
  const [prowlarrUrl, setProwlarrUrl] = useState('');
  const [prowlarrApiKey, setProwlarrApiKey] = useState('');
  const [prowlarrTimeout, setProwlarrTimeout] = useState(15);
  const [prowlarrTesting, setProwlarrTesting] = useState(false);
  const [prowlarrTestResult, setProwlarrTestResult] = useState<{
    connected: boolean;
    version?: string | null;
    indexer_count: number;
    message: string;
  } | null>(null);
  const [discoverySaving, setDiscoverySaving] = useState(false);
  const [discoverySuccess, setDiscoverySuccess] = useState(false);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);

  // Profiles State
  const [profiles, setProfiles] = useState<ProfileModel[]>([]);
  const [newProfileOpen, setNewProfileOpen] = useState(false);
  const [newProfileName, setNewProfileName] = useState('');
  const [newProfileDesc, setNewProfileDesc] = useState('');
  const [newProfileRes, setNewProfileRes] = useState('best');
  const [newProfileCont, setNewProfileCont] = useState('mp4');
  const [newProfileAudio, setNewProfileAudio] = useState(false);

  // Rules State
  const [rules, setRules] = useState<RuleModel[]>([]);
  const [newRuleOpen, setNewRuleOpen] = useState(false);
  const [newRuleName, setNewRuleName] = useState('');
  const [newRuleType, setNewRuleType] = useState('domain');
  const [newRuleVal, setNewRuleVal] = useState('');
  const [newRuleProfile, setNewRuleProfile] = useState('recommended');

  // API Keys State
  const [keys, setKeys] = useState<ApiKeyModel[]>([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyResult, setNewKeyResult] = useState<ApiKeyCreateResponse | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  // Webhooks State
  const [webhooks, setWebhooks] = useState<WebhookModel[]>([]);
  const [deliveries, setDeliveries] = useState<WebhookDeliveryModel[]>([]);
  const [newWebhookUrl, setNewWebhookUrl] = useState('');
  const [newWebhookSecret, setNewWebhookSecret] = useState('');
  const [webhookMsg, setWebhookMsg] = useState<string | null>(null);

  // Integrations State
  const [copiedBookmarklet, setCopiedBookmarklet] = useState(false);

  // Automation Settings State (Phase 7A)
  const [autoSettings, setAutoSettings] = useState<AutomationSettings>({
    automation_enabled: false,
    automation_dry_run: true,
    automation_min_score: 0,
    automation_min_seeders: 1,
    automation_max_release_size_gb: 50.0,
    automation_min_free_space_gb: 20.0,
    automation_max_downloads_per_cycle: 5,
    automation_max_downloads_per_day: 20,
    automation_max_concurrent_downloads: 3,
    automation_cooldown_hours: 4,
    automation_max_total_size_per_cycle_gb: 50.0,
    automation_max_total_size_per_day_gb: 150.0,
    automation_require_compatible_release: true,
    automation_history_retention_days: 30,
    automation_excluded_words: ['cam', 'ts', 'telesync', 'hdcam'],
    automation_excluded_regex: null,
    automation_paused: false,
    automation_quality_upgrades_enabled: false,
  });
  const [autoExcludedWordsStr, setAutoExcludedWordsStr] = useState('cam, ts, telesync, hdcam');
  const [autoSaving, setAutoSaving] = useState(false);
  const [autoSuccess, setAutoSuccess] = useState(false);
  const [autoError, setAutoError] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
    loadProfiles();
    loadRules();
    loadKeys();
    loadWebhooks();
    loadAutomationSettings();
  }, []);

  const loadAutomationSettings = async () => {
    try {
      const data = await api.getAutomationSettings();
      setAutoSettings(data);
      setAutoExcludedWordsStr((data.automation_excluded_words || []).join(', '));
    } catch (err: any) {
      console.error('Failed to load automation settings', err);
    }
  };

  const handleSaveAutomationSettings = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setAutoSaving(true);
    setAutoSuccess(false);
    setAutoError(null);
    try {
      const excludedWords = autoExcludedWordsStr
        .split(',')
        .map((w) => w.trim().toLowerCase())
        .filter(Boolean);

      const payload: AutomationSettingsUpdateRequest = {
        ...autoSettings,
        automation_excluded_words: excludedWords,
        automation_excluded_regex: autoSettings.automation_excluded_regex?.trim() || null,
      };

      const updated = await api.updateAutomationSettings(payload);
      setAutoSettings(updated);
      setAutoExcludedWordsStr((updated.automation_excluded_words || []).join(', '));
      setAutoSuccess(true);
      setTimeout(() => setAutoSuccess(false), 3000);
    } catch (err: any) {
      setAutoError(err.message || 'Failed to update automation settings');
    } finally {
      setAutoSaving(false);
    }
  };

  const loadStorageStatus = async () => {
    setStorageLoading(true);
    try {
      const data = await api.getStorageStatus();
      setStorageStatus(data);
    } catch (err) {
      console.error('Failed to load storage status', err);
    } finally {
      setStorageLoading(false);
    }
  };

  const handleRecheckStorage = async () => {
    setStorageLoading(true);
    try {
      const data = await api.recheckStorage();
      setStorageStatus(data);
    } catch (err) {
      console.error('Failed to recheck storage', err);
    } finally {
      setStorageLoading(false);
    }
  };

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      setSettings(data);
      setDiscoveryEnabled(!!data.media_discovery_enabled);
      setTmdbEnabled(!!data.tmdb_enabled);
      setProwlarrEnabled(!!data.prowlarr_enabled);
      setProwlarrUrl(data.prowlarr_url || '');
      setProwlarrTimeout(data.prowlarr_timeout_seconds || 15);
      loadStorageStatus();
    } catch (err) {
      console.error('Failed to load settings', err);
    }
  };

  const handleTestProwlarr = async () => {
    setProwlarrTesting(true);
    setProwlarrTestResult(null);
    try {
      const res = await api.testProwlarr({
        url: prowlarrUrl.trim() || undefined,
        api_key: prowlarrApiKey.trim() || undefined,
      });
      setProwlarrTestResult(res);
    } catch (err: any) {
      setProwlarrTestResult({
        connected: false,
        indexer_count: 0,
        message: err.message || 'Connection test failed',
      });
    } finally {
      setProwlarrTesting(false);
    }
  };

  const handleSaveDiscoverySettings = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setDiscoverySaving(true);
    setDiscoverySuccess(false);
    setDiscoveryError(null);
    try {
      const payload: SettingsUpdateRequest = {
        media_discovery_enabled: discoveryEnabled,
        tmdb_enabled: tmdbEnabled,
        prowlarr_enabled: prowlarrEnabled,
        prowlarr_timeout_seconds: prowlarrTimeout,
      };
      if (tmdbApiKey.trim()) {
        payload.tmdb_api_key = tmdbApiKey.trim();
      }
      if (prowlarrUrl.trim()) {
        payload.prowlarr_url = prowlarrUrl.trim();
      }
      if (prowlarrApiKey.trim()) {
        payload.prowlarr_api_key = prowlarrApiKey.trim();
      }
      const updated = await api.updateSettings(payload);
      setSettings(updated);
      setDiscoveryEnabled(!!updated.media_discovery_enabled);
      setTmdbEnabled(!!updated.tmdb_enabled);
      setProwlarrEnabled(!!updated.prowlarr_enabled);
      setProwlarrUrl(updated.prowlarr_url || '');
      setProwlarrTimeout(updated.prowlarr_timeout_seconds || 15);
      setTmdbApiKey('');
      setProwlarrApiKey('');
      setDiscoverySuccess(true);
      if (onSettingsChanged) {
        onSettingsChanged(updated);
      }
      setTimeout(() => setDiscoverySuccess(false), 3000);
    } catch (err: any) {
      setDiscoveryError(err.message || 'Failed to update discovery settings');
    } finally {
      setDiscoverySaving(false);
    }
  };

  const loadProfiles = async () => {
    try {
      const p = await api.getProfiles();
      setProfiles(p);
    } catch (err) {
      console.error('Failed to load profiles', err);
    }
  };

  const loadRules = async () => {
    try {
      const r = await api.getRules();
      setRules(r);
    } catch (err) {
      console.error('Failed to load rules', err);
    }
  };

  const loadKeys = async () => {
    try {
      const k = await api.getKeys();
      setKeys(k);
    } catch (err) {
      console.error('Failed to load API keys', err);
    }
  };

  const loadWebhooks = async () => {
    try {
      const w = await api.getWebhooks();
      setWebhooks(w);
      const d = await api.getWebhookDeliveries();
      setDeliveries(d);
    } catch (err) {
      console.error('Failed to load webhooks', err);
    }
  };

  const handleUpdateRetention = async (enabled: boolean, days?: number) => {
    setRetentionUpdating(true);
    setRetentionSuccess(false);
    try {
      const updated = await api.updateSettings({
        retention_enabled: enabled,
        retention_days: days || settings.retention_days,
      });
      setSettings(updated);
      setRetentionSuccess(true);
      setTimeout(() => setRetentionSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to update retention', err);
    } finally {
      setRetentionUpdating(false);
    }
  };

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProfileName.trim()) return;
    try {
      await api.createProfile({
        name: newProfileName.trim(),
        description: newProfileDesc.trim() || undefined,
        config: {
          preset: 'custom',
          quality: newProfileRes,
          output_container: newProfileCont,
          audio_mode: newProfileAudio ? 'audio_only' : 'merge',
          audio_format: 'mp3',
          audio_quality: '0',
          video_codec: 'any',
          filename_template: '%(title).150B.%(ext)s',
          subtitles: false,
          embed_subtitles: false,
          auto_subtitles: false,
          subtitle_langs: 'en',
          embed_metadata: true,
          embed_thumbnail: true,
          write_chapters: false,
          retries: 10,
          timeout: 30,
          concurrent_fragments: 1,
        },
      });
      setNewProfileName('');
      setNewProfileDesc('');
      setNewProfileOpen(false);
      loadProfiles();
    } catch (err: any) {
      alert(err.message || 'Failed to create profile');
    }
  };

  const handleSetDefaultProfile = async (id: string) => {
    try {
      await api.setDefaultProfile(id);
      loadProfiles();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDeleteProfile = async (id: string) => {
    if (!confirm('Delete this custom profile?')) return;
    try {
      await api.deleteProfile(id);
      loadProfiles();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRuleName.trim() || !newRuleVal.trim()) return;
    try {
      await api.createRule({
        name: newRuleName.trim(),
        condition_type: newRuleType,
        condition_value: newRuleVal.trim(),
        profile_id: newRuleProfile,
      });
      setNewRuleName('');
      setNewRuleVal('');
      setNewRuleOpen(false);
      loadRules();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDeleteRule = async (id: string) => {
    if (!confirm('Delete this rule?')) return;
    try {
      await api.deleteRule(id);
      loadRules();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    try {
      const res = await api.createKey(newKeyName.trim());
      setNewKeyResult(res);
      setNewKeyName('');
      loadKeys();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleRevokeKey = async (id: string) => {
    if (!confirm('Revoke this API key? Applications using it will lose access immediately.')) return;
    try {
      await api.revokeKey(id);
      loadKeys();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDeleteKey = async (id: string) => {
    if (!confirm('Permanently delete this key record?')) return;
    try {
      await api.deleteKey(id);
      loadKeys();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleCreateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWebhookUrl.trim()) return;
    try {
      await api.createWebhook({
        url: newWebhookUrl.trim(),
        events: ['job.completed', 'job.failed', 'batch.completed'],
        signing_secret: newWebhookSecret.trim() || undefined,
      });
      setNewWebhookUrl('');
      setNewWebhookSecret('');
      loadWebhooks();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDeleteWebhook = async (id: string) => {
    if (!confirm('Delete this webhook?')) return;
    try {
      await api.deleteWebhook(id);
      loadWebhooks();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleTestWebhook = async (id: string) => {
    try {
      await api.testWebhook(id);
      setWebhookMsg('Test event dispatched. Check delivery logs below.');
      setTimeout(() => {
        setWebhookMsg(null);
        loadWebhooks();
      }, 3000);
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Bookmarklet code
  const currentOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8080';
  const bookmarkletCode = `javascript:(function(){const url=encodeURIComponent(window.location.href);window.open('${currentOrigin}/?url='+url,'_blank');})();`;

  const copyToClipboard = (text: string, setter: (val: boolean) => void) => {
    navigator.clipboard.writeText(text);
    setter(true);
    setTimeout(() => setter(false), 2000);
  };

  const settingsTabs = [
    { id: 'retention', label: 'Retention & Storage', icon: HardDrives },
    { id: 'automation', label: 'Auto-Downloads', icon: Robot },
    { id: 'features', label: 'Features & Discovery', icon: Sparkle },
    { id: 'profiles', label: 'Download Profiles', icon: Sliders },
    { id: 'rules', label: 'Automation Rules', icon: ShieldCheck },
    { id: 'keys', label: 'API Keys', icon: Key },
    { id: 'webhooks', label: 'Webhooks', icon: Broadcast },
    { id: 'integrations', label: 'Browser & QR', icon: QrCode },
  ] as const;

  return (
    <div className="w-full max-w-5xl mx-auto px-3 sm:px-6 py-6 space-y-6 min-w-0">
      {/* Header */}
      <div className="pb-4 border-b border-zinc-200 dark:border-zinc-800">
        <h1 className="text-xl sm:text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
          Platform <span className="text-purple-600 dark:text-purple-400">Settings</span>
        </h1>
        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
          Configure automated retention, custom profiles, rules, webhooks, and integrations
        </p>
      </div>

      {/* Mobile Tab Selector (< sm) */}
      <div className="sm:hidden">
        <label htmlFor="settings-tab-select" className="sr-only">
          Select Settings Section
        </label>
        <select
          id="settings-tab-select"
          value={activeTab}
          onChange={(e) => setActiveTab(e.target.value as any)}
          className="w-full p-3 text-xs font-bold bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-800 dark:text-zinc-200 focus:ring-2 focus:ring-purple-500 focus:outline-none shadow-xs"
        >
          {settingsTabs.map((tab) => (
            <option key={tab.id} value={tab.id}>
              {tab.label}
            </option>
          ))}
        </select>
      </div>

      {/* Desktop & Tablet Tabs Navigation (>= sm) */}
      <div className="hidden sm:flex items-center gap-1.5 p-1 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-x-auto">
        {settingsTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-bold rounded-xl transition whitespace-nowrap min-h-[40px] ${
                isActive
                  ? 'bg-purple-600 text-white shadow-purple-sm'
                  : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100'
              }`}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Storage & Retention */}
      {activeTab === 'retention' && (
        <div className="space-y-5 animate-fade-in">
          {/* User-Level Storage & Media Folders Card */}
          <StorageManagementCard
            storageStatus={storageStatus}
            storageLoading={storageLoading}
            onRefresh={handleRecheckStorage}
          />
          <div className="p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                  Automatic Deletion
                </h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                  Automatically clean up completed downloads after a fixed retention duration.
                </p>
              </div>

              {/* Toggle */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => handleUpdateRetention(!settings.retention_enabled)}
                  disabled={retentionUpdating}
                  className={`relative inline-flex h-6 w-12 items-center rounded-full transition-colors focus:outline-none ${
                    settings.retention_enabled ? 'bg-purple-600' : 'bg-zinc-300 dark:bg-zinc-700'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.retention_enabled ? 'translate-x-7' : 'translate-x-1'
                    }`}
                  />
                </button>
                <span className="text-xs font-mono font-bold text-zinc-800 dark:text-zinc-200">
                  {settings.retention_enabled ? 'ENABLED' : 'OFF (Default)'}{retentionSuccess ? ' • Saved!' : ''}
                </span>
              </div>
            </div>

            {/* Retention days picker */}
            {settings.retention_enabled && (
              <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800 space-y-3">
                <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Retention Window (7–30 Days)
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {settings.allowed_retention_days.map((days) => (
                    <button
                      key={days}
                      type="button"
                      onClick={() => handleUpdateRetention(true, days)}
                      className={`py-2 text-xs font-bold rounded-xl border transition ${
                        settings.retention_days === days
                          ? 'bg-purple-600 text-white border-purple-600 shadow-purple-sm'
                          : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:border-purple-300'
                      }`}
                    >
                      {days} Days
                    </button>
                  ))}
                </div>

                {/* Permanent deletion reminder */}
                <div className="p-3.5 bg-purple-50/50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800/60 rounded-xl text-xs text-purple-700 dark:text-purple-300 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold">
                    <CheckCircle size={16} weight="fill" />
                    <span>Automatic Cleanup Active</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">
                    Completed downloads older than {settings.retention_days} days will be permanently removed.
                    Files marked as <strong>Protected</strong> or <strong>Favorited</strong> in your Media Library are strictly exempt from automatic deletion.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab: Auto-Downloads (Phase 7A) */}
      {activeTab === 'automation' && (
        <form onSubmit={handleSaveAutomationSettings} className="space-y-6 animate-fade-in">
          {/* Status banner if changes saved */}
          {autoSuccess && (
            <div className="p-3.5 bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-800 rounded-2xl flex items-center gap-2 text-xs font-bold text-green-800 dark:text-green-200">
              <CheckCircle size={18} weight="fill" className="text-green-600 dark:text-green-400" />
              <span>Automation settings saved successfully.</span>
            </div>
          )}

          {autoError && (
            <div className="p-3.5 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-2xl flex items-center gap-2 text-xs font-bold text-red-800 dark:text-red-200">
              <WarningCircle size={18} weight="fill" className="text-red-600 dark:text-red-400" />
              <span>{autoError}</span>
            </div>
          )}

          {/* Master Switches Card */}
          <div className="p-5 sm:p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-xs space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Robot size={22} className="text-purple-600 dark:text-purple-400" weight="bold" />
                  <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                    Automatic Release Downloads
                  </h3>
                </div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-xl">
                  Allow ashoriN to automatically evaluate search releases and dispatch downloads for missing monitored movies and episodes with automation enabled.
                </p>
              </div>

              <label className="relative inline-flex items-center cursor-pointer shrink-0">
                <input
                  type="checkbox"
                  checked={autoSettings.automation_enabled}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_enabled: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-zinc-200 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
              </label>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-zinc-200 dark:border-zinc-800">
              {/* Dry Run Toggle */}
              <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700/60 flex items-center justify-between gap-3">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-zinc-800 dark:text-zinc-200">
                    <Flask size={16} className="text-amber-500" />
                    <span>Dry-Run Simulation Mode</span>
                  </div>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    Evaluate candidates and log audit decisions without starting real torrent downloads.
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                  <input
                    type="checkbox"
                    checked={autoSettings.automation_dry_run}
                    onChange={(e) => setAutoSettings({ ...autoSettings, automation_dry_run: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-zinc-200 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-amber-600"></div>
                </label>
              </div>

              {/* Emergency Pause Toggle */}
              <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700/60 flex items-center justify-between gap-3">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-zinc-800 dark:text-zinc-200">
                    <Pause size={16} className="text-rose-500" />
                    <span>Emergency Automation Pause</span>
                  </div>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    Immediately halts all automated downloads without disabling scheduled searches.
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                  <input
                    type="checkbox"
                    checked={autoSettings.automation_paused}
                    onChange={(e) => setAutoSettings({ ...autoSettings, automation_paused: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-zinc-200 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-rose-600"></div>
                </label>
              </div>

              {/* Automatic Quality Upgrades Toggle (Phase 7B) */}
              <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700/60 flex items-center justify-between gap-3 sm:col-span-2">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-zinc-800 dark:text-zinc-200">
                    <Sparkle size={16} className="text-indigo-500" />
                    <span>Automatic Quality Upgrades</span>
                  </div>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    Automatically search and queue better releases for downloaded media when the quality profile cutoff is not met. Existing media files remain completely untouched until replaced/imported in Phase 8.
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                  <input
                    type="checkbox"
                    checked={autoSettings.automation_quality_upgrades_enabled ?? false}
                    onChange={(e) => setAutoSettings({ ...autoSettings, automation_quality_upgrades_enabled: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-zinc-200 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Candidate Rules Card */}
          <div className="p-5 sm:p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <ShieldCheck size={18} className="text-purple-600 dark:text-purple-400" />
              Candidate Evaluation & Rejection Rules
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Strict requirements each release must pass before deterministic scoring and selection. Season packs for individual episodes are automatically rejected.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Min Score (0 - 1000)
                </label>
                <input
                  type="number"
                  min={0}
                  max={1000}
                  value={autoSettings.automation_min_score}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_min_score: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">Releases scoring below this threshold are rejected</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Min Seeders
                </label>
                <input
                  type="number"
                  min={0}
                  value={autoSettings.automation_min_seeders}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_min_seeders: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">Minimum active seeders required</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Max Release Size (GB)
                </label>
                <input
                  type="number"
                  step="0.5"
                  min={0.5}
                  value={autoSettings.automation_max_release_size_gb}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_max_release_size_gb: parseFloat(e.target.value) || 1 })}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">Upper limit for a single media release</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Excluded Words (comma-separated)
                </label>
                <input
                  type="text"
                  value={autoExcludedWordsStr}
                  onChange={(e) => setAutoExcludedWordsStr(e.target.value)}
                  placeholder="cam, ts, telesync, hdcam"
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">Releases containing any of these keywords are rejected</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Excluded Regex Pattern (Optional)
                </label>
                <input
                  type="text"
                  value={autoSettings.automation_excluded_regex || ''}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_excluded_regex: e.target.value })}
                  placeholder="(?i)\b(telesync|hdcam)\b"
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono"
                />
                <p className="text-[10px] text-zinc-400 mt-1">Optional custom regular expression for rejection</p>
              </div>
            </div>

            <div className="pt-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoSettings.automation_require_compatible_release}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_require_compatible_release: e.target.checked })}
                  className="rounded text-purple-600 focus:ring-purple-500"
                />
                <span className="text-xs font-bold text-zinc-800 dark:text-zinc-200">
                  Require Quality Profile Compatibility
                </span>
              </label>
              <p className="text-[10px] text-zinc-400 ml-6 mt-0.5">
                Reject releases that do not match the assigned Quality Profile's allowed qualities and protocols.
              </p>
            </div>
          </div>

          {/* Circuit Breakers Card */}
          <div className="p-5 sm:p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <HardDrives size={18} className="text-purple-600 dark:text-purple-400" />
              Safety Circuit Breakers & Budget Limits
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Defend system disk space, bandwidth, and torrent client concurrency. When any breaker trips, automated downloads immediately pause safely.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 pt-2">
              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Min Free Space Buffer (GB)
                </label>
                <input
                  type="number"
                  step="1"
                  min={1}
                  value={autoSettings.automation_min_free_space_gb}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_min_free_space_gb: parseFloat(e.target.value) || 1 })}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">Minimum free disk required before download</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Max Concurrent Torrents
                </label>
                <input
                  type="number"
                  min={1}
                  value={autoSettings.automation_max_concurrent_downloads}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_max_concurrent_downloads: parseInt(e.target.value) || 1 })}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">Active automated downloads limit</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Max Downloads / Cycle
                </label>
                <input
                  type="number"
                  min={1}
                  value={autoSettings.automation_max_downloads_per_cycle}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_max_downloads_per_cycle: parseInt(e.target.value) || 1 })}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">Per scheduled search cycle</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Max Downloads / Day
                </label>
                <input
                  type="number"
                  min={1}
                  value={autoSettings.automation_max_downloads_per_day}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_max_downloads_per_day: parseInt(e.target.value) || 1 })}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">24-hour rolling count limit</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 pt-2">
              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Max Cycle Size (GB)
                </label>
                <input
                  type="number"
                  step="1"
                  min={1}
                  value={autoSettings.automation_max_total_size_per_cycle_gb}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_max_total_size_per_cycle_gb: parseFloat(e.target.value) || 1 })}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">Total payload per cycle</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Max Daily Size (GB)
                </label>
                <input
                  type="number"
                  step="5"
                  min={5}
                  value={autoSettings.automation_max_total_size_per_day_gb}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_max_total_size_per_day_gb: parseFloat(e.target.value) || 5 })}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">24-hour total payload budget</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Target Cooldown (Hours)
                </label>
                <input
                  type="number"
                  step="0.5"
                  min={0.5}
                  value={autoSettings.automation_cooldown_hours}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_cooldown_hours: parseFloat(e.target.value) || 1 })}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">Wait before retrying the same item</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  History Retention (Days)
                </label>
                <input
                  type="number"
                  min={1}
                  value={autoSettings.automation_history_retention_days}
                  onChange={(e) => setAutoSettings({ ...autoSettings, automation_history_retention_days: parseInt(e.target.value) || 7 })}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100"
                />
                <p className="text-[10px] text-zinc-400 mt-1">Days to preserve audit log</p>
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={autoSaving}
              className="flex items-center gap-2 px-6 py-2.5 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-xs hover:shadow transition-all disabled:opacity-50 cursor-pointer"
            >
              {autoSaving ? <CircleNotch size={16} className="animate-spin" /> : <Check size={16} weight="bold" />}
              <span>Save Automation Settings</span>
            </button>
          </div>
        </form>
      )}

      {/* Tab: Features & Discovery */}
      {activeTab === 'features' && (
        <div className="space-y-6 animate-fade-in">
          {/* Status banner if changes saved */}
          {discoverySuccess && (
            <div className="p-3.5 bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-800 rounded-2xl flex items-center gap-2 text-xs font-bold text-green-800 dark:text-green-200">
              <CheckCircle size={18} weight="fill" className="text-green-600 dark:text-green-400" />
              <span>Discovery settings saved successfully.</span>
            </div>
          )}

          {discoveryError && (
            <div className="p-3.5 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-2xl flex items-center gap-2 text-xs font-bold text-red-800 dark:text-red-200">
              <WarningCircle size={18} weight="fill" className="text-red-600 dark:text-red-400" />
              <span>{discoveryError}</span>
            </div>
          )}

          {/* Media Discovery Card */}
          <div className="p-5 sm:p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-xs space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Compass size={20} className="text-purple-600 dark:text-purple-400" />
                  <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                    Media Discovery System
                  </h3>
                </div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-xl">
                  Enable the cinematic discovery catalog in the navigation bar to browse movies and TV series, view official backdrops and synopses, and browse seasons and episodes.
                </p>
              </div>

              <label className="relative inline-flex items-center cursor-pointer shrink-0">
                <input
                  type="checkbox"
                  checked={discoveryEnabled}
                  onChange={(e) => setDiscoveryEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-zinc-200 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
              </label>
            </div>

            <div className="border-t border-zinc-200 dark:border-zinc-800 pt-5 space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <FilmStrip size={18} className="text-purple-600 dark:text-purple-400" />
                    <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                      The Movie Database (TMDB) Integration
                    </h4>
                  </div>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    Connect to TMDB for high-resolution posters, backdrops, cast, genres, ratings, and episode data.
                  </p>
                </div>

                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                  <input
                    type="checkbox"
                    checked={tmdbEnabled}
                    onChange={(e) => setTmdbEnabled(e.target.checked)}
                    disabled={!discoveryEnabled}
                    className="sr-only peer disabled:opacity-50"
                  />
                  <div className="w-9 h-5 bg-zinc-200 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-purple-600"></div>
                </label>
              </div>

              {/* TMDB API Key Input */}
              <div className="space-y-2 pt-2">
                <div className="flex items-center justify-between">
                  <label htmlFor="tmdb-api-key" className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                    TMDB API Key (v3 auth or Read Access Token)
                  </label>
                  {settings.tmdb_api_key_configured ? (
                    <span className="text-[10px] font-bold text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-950/60 border border-green-200 dark:border-green-800 px-2 py-0.5 rounded-full flex items-center gap-1">
                      <CheckCircle size={12} weight="fill" />
                      Active: {settings.tmdb_api_key_masked}
                    </span>
                  ) : (
                    <span className="text-[10px] font-bold text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 px-2 py-0.5 rounded-full flex items-center gap-1">
                      <WarningCircle size={12} weight="fill" />
                      Not Configured
                    </span>
                  )}
                </div>

                <input
                  id="tmdb-api-key"
                  type="password"
                  value={tmdbApiKey}
                  onChange={(e) => setTmdbApiKey(e.target.value)}
                  placeholder={
                    settings.tmdb_api_key_configured
                      ? 'Leave blank to keep existing key, or enter new key...'
                      : 'Paste your TMDB API key here...'
                  }
                  disabled={!discoveryEnabled}
                  className="w-full px-3.5 py-2.5 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono disabled:opacity-50"
                />

                <p className="text-[11px] text-zinc-400 dark:text-zinc-500">
                  Don't have a key? Create a free account at{' '}
                  <a
                    href="https://www.themoviedb.org/settings/api"
                    target="_blank"
                    rel="noreferrer"
                    className="text-purple-600 dark:text-purple-400 underline hover:text-purple-500"
                  >
                    themoviedb.org
                  </a>{' '}
                  to generate your personal developer API key.
                </p>
              </div>

              {/* Prowlarr Section */}
              <div className="border-t border-zinc-200 dark:border-zinc-800 pt-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Broadcast size={18} className="text-purple-600 dark:text-purple-400" />
                      <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                        Prowlarr Indexer Integration
                      </h4>
                    </div>
                    <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                      Search across your configured torrent indexers and hand off releases directly to the torrent engine.
                    </p>
                  </div>

                  <label className="relative inline-flex items-center cursor-pointer shrink-0">
                    <input
                      type="checkbox"
                      aria-label="Prowlarr Indexer Integration"
                      checked={prowlarrEnabled}
                      onChange={(e) => setProwlarrEnabled(e.target.checked)}
                      disabled={!discoveryEnabled}
                      className="sr-only peer disabled:opacity-50"
                    />
                    <div className="w-9 h-5 bg-zinc-200 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-purple-600"></div>
                  </label>
                </div>

                {/* Prowlarr URL and Timeout */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                  <div className="sm:col-span-2 space-y-1">
                    <label htmlFor="prowlarr-url" className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                      Prowlarr Server URL
                    </label>
                    <input
                      id="prowlarr-url"
                      type="text"
                      value={prowlarrUrl}
                      onChange={(e) => setProwlarrUrl(e.target.value)}
                      placeholder="http://localhost:9696 or http://prowlarr:9696"
                      disabled={!discoveryEnabled || !prowlarrEnabled}
                      className="w-full px-3.5 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono disabled:opacity-50"
                    />
                  </div>

                  <div className="space-y-1">
                    <label htmlFor="prowlarr-timeout" className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                      Timeout (seconds)
                    </label>
                    <input
                      id="prowlarr-timeout"
                      type="number"
                      min={2}
                      max={120}
                      value={prowlarrTimeout}
                      onChange={(e) => setProwlarrTimeout(parseInt(e.target.value) || 15)}
                      disabled={!discoveryEnabled || !prowlarrEnabled}
                      className="w-full px-3.5 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono disabled:opacity-50"
                    />
                  </div>
                </div>

                {/* Prowlarr API Key */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label htmlFor="prowlarr-api-key" className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                      Prowlarr API Key
                    </label>
                    {settings.prowlarr_api_key_configured ? (
                      <span className="text-[10px] font-bold text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-950/60 border border-green-200 dark:border-green-800 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <CheckCircle size={12} weight="fill" />
                        Active: {settings.prowlarr_api_key_masked}
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <WarningCircle size={12} weight="fill" />
                        Not Configured
                      </span>
                    )}
                  </div>

                  <input
                    id="prowlarr-api-key"
                    type="password"
                    value={prowlarrApiKey}
                    onChange={(e) => setProwlarrApiKey(e.target.value)}
                    placeholder={
                      settings.prowlarr_api_key_configured
                        ? 'Leave blank to keep existing key, or enter new key...'
                        : 'Paste Prowlarr API key here...'
                    }
                    disabled={!discoveryEnabled || !prowlarrEnabled}
                    className="w-full px-3.5 py-2.5 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono disabled:opacity-50"
                  />

                  {/* Test Connection Button & Result */}
                  <div className="flex flex-wrap items-center gap-3 pt-1">
                    <button
                      type="button"
                      onClick={handleTestProwlarr}
                      disabled={prowlarrTesting || !discoveryEnabled || !prowlarrEnabled}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold text-zinc-700 dark:text-zinc-200 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition disabled:opacity-50 flex items-center gap-1.5"
                    >
                      {prowlarrTesting ? (
                        <>
                          <CircleNotch size={14} className="animate-spin" />
                          <span>Testing...</span>
                        </>
                      ) : (
                        <>
                          <Broadcast size={14} />
                          <span>Test Connection</span>
                        </>
                      )}
                    </button>

                    {prowlarrTestResult && (
                      <span
                        className={`text-xs font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1.5 ${
                          prowlarrTestResult.connected
                            ? 'text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-950/60 border border-green-200 dark:border-green-800'
                            : 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800'
                        }`}
                      >
                        {prowlarrTestResult.connected ? (
                          <CheckCircle size={14} weight="fill" />
                        ) : (
                          <WarningCircle size={14} weight="fill" />
                        )}
                        <span>{prowlarrTestResult.message}</span>
                        {prowlarrTestResult.connected && prowlarrTestResult.indexer_count > 0 && (
                          <span className="opacity-75">
                            ({prowlarrTestResult.indexer_count} indexer{prowlarrTestResult.indexer_count > 1 ? 's' : ''})
                          </span>
                        )}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Save Button */}
              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={handleSaveDiscoverySettings}
                  disabled={discoverySaving}
                  className="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 active:scale-98 transition disabled:opacity-50 shadow-purple-sm"
                >
                  {discoverySaving ? (
                    <>
                      <CircleNotch size={14} className="animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <>
                      <Check size={14} weight="bold" />
                      <span>Save Discovery Settings</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Download Profiles */}
      {activeTab === 'profiles' && (
        <div className="space-y-4 animate-fade-in">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                Download Profiles
              </h3>
              <p className="text-xs text-zinc-500">
                Reusable presets controlling video resolution, codecs, audio mode, and containers
              </p>
            </div>
            <button
              onClick={() => setNewProfileOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-purple transition"
            >
              <Plus size={14} weight="bold" />
              <span>New Profile</span>
            </button>
          </div>

          {/* New Profile Modal */}
          {newProfileOpen && (
            <form
              onSubmit={handleCreateProfile}
              className="p-5 bg-white dark:bg-zinc-900 border border-purple-300 dark:border-purple-800 rounded-2xl space-y-3 shadow-md"
            >
              <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100">Create Custom Profile</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  type="text"
                  placeholder="Profile Name (e.g. Anime 1080p, Podcast Audio)"
                  value={newProfileName}
                  onChange={(e) => setNewProfileName(e.target.value)}
                  className="px-3 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl"
                  required
                />
                <input
                  type="text"
                  placeholder="Description"
                  value={newProfileDesc}
                  onChange={(e) => setNewProfileDesc(e.target.value)}
                  className="px-3 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl"
                />
                <select
                  value={newProfileRes}
                  onChange={(e) => setNewProfileRes(e.target.value)}
                  className="px-3 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl"
                >
                  <option value="best">Resolution: Best (Auto)</option>
                  <option value="2160p">Resolution: 4K (2160p)</option>
                  <option value="1440p">Resolution: 1440p</option>
                  <option value="1080p">Resolution: 1080p</option>
                  <option value="720p">Resolution: 720p</option>
                  <option value="480p">Resolution: 480p</option>
                </select>
                <select
                  value={newProfileCont}
                  onChange={(e) => setNewProfileCont(e.target.value)}
                  className="px-3 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl"
                >
                  <option value="mp4">Container: MP4</option>
                  <option value="mkv">Container: MKV</option>
                  <option value="webm">Container: WEBM</option>
                  <option value="mp3">Container: MP3</option>
                </select>
              </div>
              <div className="flex items-center justify-between pt-2">
                <label className="flex items-center gap-2 text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  <input
                    type="checkbox"
                    checked={newProfileAudio}
                    onChange={(e) => setNewProfileAudio(e.target.checked)}
                    className="accent-purple-600 rounded"
                  />
                  <span>Extract Audio Only</span>
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setNewProfileOpen(false)}
                    className="px-3 py-1.5 text-xs text-zinc-500 hover:text-zinc-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 text-xs font-bold bg-purple-600 text-white rounded-xl shadow-purple"
                  >
                    Save Profile
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* Profiles Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {profiles.map((p) => (
              <div
                key={p.id}
                className="p-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                        {p.name}
                      </h4>
                      {p.is_default && (
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-purple-600 text-white shadow-purple-sm">
                          DEFAULT
                        </span>
                      )}
                      {p.badge && !p.is_default && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                          {p.badge}
                        </span>
                      )}
                    </div>
                    {p.is_builtin && (
                      <span className="text-[10px] font-mono text-zinc-400">Built-in</span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                    {p.description || 'Configured download profile'}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-zinc-100 dark:border-zinc-800 text-xs">
                  <span className="text-[11px] font-mono text-zinc-500">
                    {p.config?.quality?.toUpperCase() || 'BEST'} •{' '}
                    {p.config?.output_container?.toUpperCase() || 'MP4'}
                  </span>
                  <div className="flex items-center gap-2">
                    {!p.is_default && (
                      <button
                        onClick={() => handleSetDefaultProfile(p.id)}
                        className="px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:text-purple-600"
                      >
                        Set Default
                      </button>
                    )}
                    {!p.is_builtin && (
                      <button
                        onClick={() => handleDeleteProfile(p.id)}
                        className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
                      >
                        <Trash size={15} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Automation Rules */}
      {activeTab === 'rules' && (
        <div className="space-y-4 animate-fade-in">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                Automation Rules
              </h3>
              <p className="text-xs text-zinc-500">
                Automatically route URLs to specific profiles (e.g., soundcloud.com → Audio Only)
              </p>
            </div>
            <button
              onClick={() => setNewRuleOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-purple transition"
            >
              <Plus size={14} weight="bold" />
              <span>Add Rule</span>
            </button>
          </div>

          {/* New Rule Modal */}
          {newRuleOpen && (
            <form
              onSubmit={handleCreateRule}
              className="p-5 bg-white dark:bg-zinc-900 border border-purple-300 dark:border-purple-800 rounded-2xl space-y-3 shadow-md"
            >
              <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100">Create Automation Rule</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  type="text"
                  placeholder="Rule Name (e.g. SoundCloud to MP3)"
                  value={newRuleName}
                  onChange={(e) => setNewRuleName(e.target.value)}
                  className="px-3 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl"
                  required
                />
                <select
                  value={newRuleType}
                  onChange={(e) => setNewRuleType(e.target.value)}
                  className="px-3 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl"
                >
                  <option value="domain">Domain Match (e.g. soundcloud.com)</option>
                  <option value="extractor">Extractor Match (e.g. youtube, twitch)</option>
                  <option value="title_regex">Title Regex Pattern</option>
                  <option value="is_playlist">Playlist Detection</option>
                </select>
                <input
                  type="text"
                  placeholder="Condition Value (e.g. soundcloud.com)"
                  value={newRuleVal}
                  onChange={(e) => setNewRuleVal(e.target.value)}
                  className="px-3 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl"
                  required
                />
                <select
                  value={newRuleProfile}
                  onChange={(e) => setNewRuleProfile(e.target.value)}
                  className="px-3 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl"
                >
                  {profiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      Apply: {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setNewRuleOpen(false)}
                  className="px-3 py-1.5 text-xs text-zinc-500 hover:text-zinc-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-bold bg-purple-600 text-white rounded-xl shadow-purple"
                >
                  Save Rule
                </button>
              </div>
            </form>
          )}

          {rules.length === 0 ? (
            <div className="p-8 text-center text-xs text-zinc-500 border border-dashed border-zinc-200 dark:border-zinc-800 rounded-2xl">
              No automation rules created yet.
            </div>
          ) : (
            <div className="space-y-2">
              {rules.map((r) => (
                <div
                  key={r.id}
                  className="p-3.5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl flex items-center justify-between"
                >
                  <div>
                    <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                      {r.name}
                    </h4>
                    <p className="text-[11px] text-zinc-500 mt-0.5">
                      IF <strong>{r.condition_type}</strong> matches &apos;{r.condition_value}&apos; THEN apply profile <strong>{r.profile_id}</strong>
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteRule(r.id)}
                    className="p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded-lg"
                  >
                    <Trash size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: API Keys */}
      {activeTab === 'keys' && (
        <div className="space-y-4 animate-fade-in">
          <div className="p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-4">
            <div>
              <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                Generate Automation API Key
              </h3>
              <p className="text-xs text-zinc-500">
                Access the public <code className="font-mono text-purple-600">/api/v1/jobs</code> endpoint from external automation tools (n8n, curl, scripts).
              </p>
            </div>

            <form onSubmit={handleCreateKey} className="flex gap-2">
              <input
                type="text"
                placeholder="Key Description (e.g. n8n workflow, home server script)"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="flex-1 px-3.5 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl"
                required
              />
              <button
                type="submit"
                className="px-4 py-2 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-purple transition"
              >
                Generate Key
              </button>
            </form>

            {/* Newly Created Key Banner */}
            {newKeyResult && (
              <div className="p-4 bg-purple-50 dark:bg-purple-950/60 border border-purple-200 dark:border-purple-800/80 rounded-xl space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-bold text-purple-700 dark:text-purple-300">
                  <WarningCircle size={16} />
                  <span>Store this API key safely — it will never be displayed again!</span>
                </div>
                <div className="flex items-center gap-2 p-2.5 bg-white dark:bg-zinc-900 rounded-lg border border-purple-100 dark:border-purple-900 font-mono text-xs text-purple-600 dark:text-purple-400 select-all overflow-x-auto">
                  <span className="flex-1 truncate">{newKeyResult.api_key}</span>
                  <button
                    onClick={() => copyToClipboard(newKeyResult.api_key, setCopiedKey)}
                    className="p-1.5 rounded-md hover:bg-purple-50 dark:hover:bg-purple-950 transition text-purple-700 dark:text-purple-300"
                    title="Copy to clipboard"
                  >
                    {copiedKey ? <Check size={16} /> : <Copy size={16} />}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Registered Keys List */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-zinc-700 dark:text-zinc-300">Registered API Keys</h4>
            {keys.length === 0 ? (
              <p className="text-xs text-zinc-400 py-4 text-center">No API keys generated yet.</p>
            ) : (
              keys.map((k) => (
                <div
                  key={k.id}
                  className="p-3.5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-zinc-900 dark:text-zinc-100">{k.name}</span>
                      <span className="font-mono text-[11px] text-zinc-400">{k.key_prefix}</span>
                    </div>
                    <p className="text-[11px] text-zinc-500 mt-0.5">
                      Created {new Date(k.created_at * 1000).toLocaleDateString()}
                      {k.last_used_at ? ` • Last used ${new Date(k.last_used_at * 1000).toLocaleDateString()}` : ' • Never used'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {k.is_active ? (
                      <button
                        onClick={() => handleRevokeKey(k.id)}
                        className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:text-purple-600"
                      >
                        Revoke
                      </button>
                    ) : (
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-zinc-200 dark:bg-zinc-800 text-zinc-500">
                        REVOKED
                      </span>
                    )}
                    <button
                      onClick={() => handleDeleteKey(k.id)}
                      className="p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
                    >
                      <Trash size={16} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 5: Webhooks */}
      {activeTab === 'webhooks' && (
        <div className="space-y-4 animate-fade-in">
          <div className="p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-3">
            <div>
              <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                Register Webhook Endpoint
              </h3>
              <p className="text-xs text-zinc-500">
                Send real-time HTTP POST notifications on job completion, failure, and batch events.
              </p>
            </div>

            <form onSubmit={handleCreateWebhook} className="space-y-3">
              <input
                type="url"
                placeholder="Endpoint URL (e.g. https://n8n.example.com/webhook/media-done)"
                value={newWebhookUrl}
                onChange={(e) => setNewWebhookUrl(e.target.value)}
                className="w-full px-3.5 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl"
                required
              />
              <input
                type="text"
                placeholder="HMAC Signing Secret (optional)"
                value={newWebhookSecret}
                onChange={(e) => setNewWebhookSecret(e.target.value)}
                className="w-full px-3.5 py-2 text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-purple transition"
                >
                  Register Endpoint
                </button>
              </div>
            </form>
          </div>

          {webhookMsg && (
            <div className="p-3 bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800 text-xs text-purple-700 dark:text-purple-300 rounded-xl">
              {webhookMsg}
            </div>
          )}

          {/* Webhook Endpoints List */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-zinc-700 dark:text-zinc-300">Active Webhooks</h4>
            {webhooks.length === 0 ? (
              <p className="text-xs text-zinc-400 py-3 text-center">No webhooks registered.</p>
            ) : (
              webhooks.map((w) => (
                <div
                  key={w.id}
                  className="p-3.5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl flex items-center justify-between text-xs"
                >
                  <div className="min-w-0 pr-4">
                    <span className="font-mono font-bold text-zinc-900 dark:text-zinc-100 truncate block">
                      {w.url}
                    </span>
                    <p className="text-[11px] text-zinc-500 mt-0.5">
                      Events: {w.events.join(', ')} {w.signing_secret ? '• HMAC Signed' : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleTestWebhook(w.id)}
                      className="px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:text-purple-600"
                    >
                      Test Ping
                    </button>
                    <button
                      onClick={() => handleDeleteWebhook(w.id)}
                      className="p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
                    >
                      <Trash size={16} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Delivery Logs */}
          <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800 space-y-2">
            <h4 className="text-xs font-bold text-zinc-700 dark:text-zinc-300">Recent Deliveries</h4>
            {deliveries.length === 0 ? (
              <p className="text-xs text-zinc-400 py-2">No webhook deliveries recorded yet.</p>
            ) : (
              <div className="max-h-48 overflow-y-auto space-y-1.5">
                {deliveries.map((d) => (
                  <div
                    key={d.id}
                    className="p-2.5 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-xs flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          d.success ? 'bg-purple-500 shadow-purple-sm' : 'bg-zinc-500'
                        }`}
                      />
                      <span className="font-mono font-bold text-zinc-800 dark:text-zinc-200">
                        {d.event}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-zinc-500 text-[11px]">
                      <span>HTTP {d.status_code || 'N/A'}</span>
                      <span>{new Date(d.delivered_at * 1000).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 6: Integrations & QR Code */}
      {activeTab === 'integrations' && (
        <div className="space-y-5 animate-fade-in">
          {/* Bookmarklet Section */}
          <div className="p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              Browser Bookmarklet
            </h3>
            <p className="text-xs text-zinc-500 leading-relaxed">
              Drag this button to your browser bookmarks bar. When viewing any video or audio page, click it to instantly send the URL to ashoriN!
            </p>

            <div className="flex items-center gap-3 pt-2">
              <a
                href={bookmarkletCode}
                onClick={(e) => e.preventDefault()}
                className="cursor-move px-4 py-2 rounded-xl text-xs font-bold bg-purple-600 text-white shadow-purple select-none inline-block"
                title="Drag to your bookmarks bar"
              >
                ⚡ Download with ashoriN
              </a>

              <button
                onClick={() => copyToClipboard(bookmarkletCode, setCopiedBookmarklet)}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200"
              >
                {copiedBookmarklet ? <Check size={14} /> : <Copy size={14} />}
                <span>{copiedBookmarklet ? 'Copied JavaScript' : 'Copy Code'}</span>
              </button>
            </div>
          </div>

          {/* QR Code Section */}
          <div className="p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm flex flex-col sm:flex-row items-center gap-6">
            {/* Offline SVG QR representation */}
            <div className="p-3 bg-white rounded-2xl shadow-sm border border-zinc-200">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(
                  currentOrigin
                )}`}
                alt="ashoriN Mobile Access QR"
                className="w-36 h-36 rounded-lg"
                loading="lazy"
              />
            </div>

            <div className="space-y-2 text-center sm:text-left">
              <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                Connect Mobile Device
              </h3>
              <p className="text-xs text-zinc-500 leading-relaxed max-w-md">
                Scan this QR code with your phone or tablet camera to open ashoriN on your local network.
                Responsive layouts and mobile touch controls are automatically optimized.
              </p>
              <p className="text-xs font-mono text-purple-600 dark:text-purple-400 break-all">
                {currentOrigin}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

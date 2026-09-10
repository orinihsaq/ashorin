import React, { useState, useEffect } from 'react';
import {
  DownloadSimple,
  Sliders,
  CheckCircle,
  VideoCamera,
  MusicNotes,
  GearSix,
  ArrowCounterClockwise,
  SpeakerHigh,
  WifiHigh,
  Subtitles,
  Tag,
  ListNumbers,
  Sparkle,
  FilmStrip,
} from '@phosphor-icons/react';
import {
  AnalyzeResponse,
  DownloadConfig,
  PresetDefinition,
} from '../types';

interface DownloadConfigAreaProps {
  media: AnalyzeResponse;
  presets: PresetDefinition[];
  onStartDownload: (config: DownloadConfig) => void;
  isStarting: boolean;
}

const DEFAULT_CONFIG: DownloadConfig = {
  preset: 'recommended',
  quality: 'best',
  output_container: 'mp4',
  audio_mode: 'merge',
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
  playlist_mode: 'single',
};

export const DownloadConfigArea: React.FC<DownloadConfigAreaProps> = ({
  media,
  presets,
  onStartDownload,
  isStarting,
}) => {
  // Mode: 'recommended' | 'advanced'
  const [activeTab, setActiveTab] = useState<'recommended' | 'advanced'>('recommended');
  const [activeSection, setActiveSection] = useState<string>('general');

  // Working download configuration state
  const [config, setConfig] = useState<DownloadConfig>(DEFAULT_CONFIG);

  // Initialize config when presets load
  useEffect(() => {
    if (presets.length > 0) {
      const rec = presets.find((p) => p.id === 'recommended') || presets[0];
      setConfig({ ...rec.config });
    }
  }, [presets]);

  // Preset switch handler
  const handleApplyPreset = (presetId: string) => {
    const found = presets.find((p) => p.id === presetId);
    if (found) {
      setConfig({ ...found.config });
    } else {
      setConfig((prev) => ({ ...prev, preset: presetId }));
    }
  };

  const handleResetToPreset = () => {
    const found = presets.find((p) => p.id === config.preset) || presets[0];
    if (found) {
      setConfig({ ...found.config });
    } else {
      setConfig(DEFAULT_CONFIG);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStartDownload(config);
  };

  const isAudioOnly = config.audio_mode === 'audio_only';

  // Format pre-download summary string
  const summaryParts: string[] = [];
  summaryParts.push(
    `Preset: ${
      presets.find((p) => p.id === config.preset)?.name || config.preset.toUpperCase()
    }`
  );
  if (isAudioOnly) {
    summaryParts.push(`Audio: .${config.audio_format.toUpperCase()}`);
    summaryParts.push(`Quality: ${config.audio_quality === '0' ? 'Best VBR' : config.audio_quality}`);
  } else {
    summaryParts.push(`Resolution: ${config.quality.toUpperCase()}`);
    summaryParts.push(`Format: .${config.output_container.toUpperCase()}`);
    if (config.video_codec !== 'any') summaryParts.push(`Codec: ${config.video_codec.toUpperCase()}`);
  }
  if (config.embed_metadata) summaryParts.push('Metadata');
  if (config.embed_thumbnail) summaryParts.push('Cover Art');
  if (config.subtitles) summaryParts.push(`Subs: ${config.subtitle_langs || 'en'}`);
  if (config.write_chapters && !isAudioOnly) summaryParts.push('Chapters');

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/90 rounded-2xl p-5 shadow-sm space-y-5 transition-all"
    >
      {/* Header: Mode Selector Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-3">
        <div className="flex items-center gap-2">
          <Sliders size={18} className="text-brand-500" />
          <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider">
            Download Controls
          </h3>
        </div>

        {/* Tab switch */}
        <div className="flex items-center p-1 bg-zinc-100 dark:bg-zinc-950 rounded-xl border border-zinc-200/80 dark:border-zinc-800">
          <button
            type="button"
            onClick={() => setActiveTab('recommended')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'recommended'
                ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 shadow-xs ring-1 ring-zinc-200 dark:ring-zinc-700'
                : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200'
            }`}
          >
            <Sparkle size={14} className={activeTab === 'recommended' ? 'text-amber-500' : ''} />
            <span>Recommended</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('advanced')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'advanced'
                ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 shadow-xs ring-1 ring-zinc-200 dark:ring-zinc-700'
                : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200'
            }`}
          >
            <GearSix size={14} className={activeTab === 'advanced' ? 'text-brand-500' : ''} />
            <span>Advanced yt-dlp</span>
          </button>
        </div>
      </div>

      {/* Preset Pills Bar */}
      <div>
        <label className="block text-[11px] font-mono font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mb-2">
          Optimization Presets
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {presets.map((preset) => {
            const isSelected = config.preset === preset.id;
            return (
              <button
                key={preset.id}
                type="button"
                onClick={() => handleApplyPreset(preset.id)}
                className={`flex flex-col p-2.5 rounded-xl border text-left transition relative ${
                  isSelected
                    ? 'border-brand-500 bg-brand-50/50 dark:bg-brand-950/40 text-brand-950 dark:text-brand-100 ring-2 ring-brand-500/20'
                    : 'border-zinc-200 dark:border-zinc-800/80 bg-zinc-50/50 dark:bg-zinc-950/30 text-zinc-700 dark:text-zinc-300 hover:border-zinc-300 dark:hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1">
                  <span className="text-xs font-bold truncate">{preset.name}</span>
                  {preset.badge && (
                    <span
                      className={`text-[9px] font-mono font-extrabold uppercase px-1 py-0.2 rounded ${
                        isSelected
                          ? 'bg-brand-600 text-white'
                          : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400'
                      }`}
                    >
                      {preset.badge}
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-zinc-500 dark:text-zinc-400 line-clamp-2 leading-tight">
                  {preset.description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* RECOMMENDED MODE VIEW */}
      {activeTab === 'recommended' && (
        <div className="space-y-4 pt-1 animate-in fade-in duration-150">
          {/* Mode Switch: Video vs Audio Only */}
          <div className="flex items-center justify-between p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200/60 dark:border-zinc-800">
            <div>
              <p className="text-xs font-bold text-zinc-800 dark:text-zinc-200">Extraction Stream</p>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                {isAudioOnly ? 'Extracting standalone audio track' : 'Merging high-fidelity video & audio streams'}
              </p>
            </div>
            <div className="flex items-center gap-1 bg-zinc-200/80 dark:bg-zinc-800 p-1 rounded-lg">
              <button
                type="button"
                onClick={() => setConfig((prev) => ({ ...prev, audio_mode: 'merge' }))}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                  !isAudioOnly
                    ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                    : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100'
                }`}
              >
                <VideoCamera size={14} />
                <span>Video + Audio</span>
              </button>
              <button
                type="button"
                onClick={() => setConfig((prev) => ({ ...prev, audio_mode: 'audio_only', output_container: prev.audio_format }))}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                  isAudioOnly
                    ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                    : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100'
                }`}
              >
                <MusicNotes size={14} />
                <span>Audio Only</span>
              </button>
            </div>
          </div>

          {!isAudioOnly ? (
            /* Video Controls */
            <div className="space-y-3.5">
              {/* Quality Picker */}
              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-2">
                  Select Video Resolution
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {media.video_options.map((opt) => {
                    const isSelected = config.quality === opt.resolution;
                    return (
                      <button
                        key={opt.resolution}
                        type="button"
                        onClick={() =>
                          setConfig((prev) => ({
                            ...prev,
                            quality: opt.resolution,
                            preset: 'custom',
                          }))
                        }
                        className={`p-2.5 rounded-xl border text-left transition flex items-center justify-between ${
                          isSelected
                            ? 'border-brand-600 bg-brand-50/50 dark:bg-brand-950/30 text-brand-900 dark:text-brand-100 ring-2 ring-brand-500/20'
                            : 'border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 text-zinc-800 dark:text-zinc-200'
                        }`}
                      >
                        <div>
                          <p className="text-xs font-bold">{opt.label}</p>
                          <p className="text-[10px] text-zinc-500 dark:text-zinc-400 font-mono uppercase">
                            {opt.resolution} {opt.fps ? `• ${opt.fps}fps` : ''}
                          </p>
                        </div>
                        {isSelected && (
                          <CheckCircle
                            size={16}
                            weight="fill"
                            className="text-brand-600 dark:text-brand-400 shrink-0"
                          />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Video Container */}
              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-2">
                  Container Format
                </label>
                <div className="flex items-center gap-2">
                  {['mp4', 'mkv', 'webm'].map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setConfig((prev) => ({ ...prev, output_container: c }))}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold font-mono uppercase tracking-wider border transition ${
                        config.output_container === c
                          ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 border-zinc-900 dark:border-zinc-100 shadow-xs'
                          : 'border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                      }`}
                    >
                      .{c}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Audio Options */
            <div className="space-y-3.5">
              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-2">
                  Audio Format Transcode
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  {['mp3', 'm4a', 'flac', 'wav', 'opus'].map((fmt) => {
                    const isSelected = config.audio_format === fmt;
                    return (
                      <button
                        key={fmt}
                        type="button"
                        onClick={() =>
                          setConfig((prev) => ({
                            ...prev,
                            audio_format: fmt,
                            output_container: fmt,
                          }))
                        }
                        className={`p-2.5 rounded-xl border text-center transition ${
                          isSelected
                            ? 'border-brand-600 bg-brand-50/50 dark:bg-brand-950/30 text-brand-900 dark:text-brand-100 ring-2 ring-brand-500/20'
                            : 'border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 text-zinc-800 dark:text-zinc-200'
                        }`}
                      >
                        <span className="text-xs font-mono font-bold uppercase">.{fmt}</span>
                        <span className="block text-[10px] text-zinc-500 dark:text-zinc-400">
                          {fmt === 'flac' || fmt === 'wav' ? 'Lossless' : '320 kbps'}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Quick Subtitle and Metadata Chips */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-zinc-700 dark:text-zinc-300 select-none">
              <input
                type="checkbox"
                checked={config.embed_metadata}
                onChange={(e) => setConfig((prev) => ({ ...prev, embed_metadata: e.target.checked }))}
                className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500 dark:bg-zinc-800 border-zinc-300 dark:border-zinc-700"
              />
              <span>Embed Title & Artwork Tags</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-zinc-700 dark:text-zinc-300 select-none">
              <input
                type="checkbox"
                checked={config.subtitles}
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    subtitles: e.target.checked,
                    embed_subtitles: e.target.checked,
                  }))
                }
                className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500 dark:bg-zinc-800 border-zinc-300 dark:border-zinc-700"
              />
              <span>Extract Subtitles (EN)</span>
            </label>
          </div>
        </div>
      )}

      {/* ADVANCED YT-DLP MODE VIEW */}
      {activeTab === 'advanced' && (
        <div className="space-y-4 pt-1 animate-in fade-in duration-150">
          {/* Sub-navigation tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-zinc-100 dark:border-zinc-800/80 text-xs">
            {[
              { id: 'general', label: 'General & Output', icon: GearSix },
              { id: 'video', label: 'Video & Codec', icon: FilmStrip },
              { id: 'audio', label: 'Audio Engine', icon: SpeakerHigh },
              { id: 'network', label: 'Network & Retry', icon: WifiHigh },
              { id: 'subtitles', label: 'Subtitles', icon: Subtitles },
              { id: 'metadata', label: 'Tags & Chapters', icon: Tag },
              { id: 'playlist', label: 'Playlist Mode', icon: ListNumbers },
            ].map((sec) => {
              const Icon = sec.icon;
              const isSelected = activeSection === sec.id;
              return (
                <button
                  key={sec.id}
                  type="button"
                  onClick={() => setActiveSection(sec.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition ${
                    isSelected
                      ? 'bg-brand-50 dark:bg-brand-950/60 text-brand-600 dark:text-brand-400 font-semibold border border-brand-200 dark:border-brand-800'
                      : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200'
                  }`}
                >
                  <Icon size={14} />
                  <span>{sec.label}</span>
                </button>
              );
            })}
          </div>

          {/* Section: General */}
          {activeSection === 'general' && (
            <div className="space-y-3.5">
              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Custom Output Filename Template
                </label>
                <input
                  type="text"
                  value={config.filename_template}
                  onChange={(e) =>
                    setConfig((prev) => ({
                      ...prev,
                      filename_template: e.target.value,
                      preset: 'custom',
                    }))
                  }
                  className="w-full px-3 py-2 text-xs font-mono rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  placeholder="%(title).150B.%(ext)s"
                />
                <div className="flex flex-wrap gap-1.5 mt-2 text-[10px] text-zinc-500 font-mono">
                  <span>Tokens:</span>
                  {['%(title)s', '%(uploader)s', '%(resolution)s', '%(id)s', '%(ext)s'].map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() =>
                        setConfig((prev) => ({
                          ...prev,
                          filename_template: prev.filename_template.replace('.%(ext)s', ` - ${t}.%(ext)s`),
                          preset: 'custom',
                        }))
                      }
                      className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300"
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Output Container
                </label>
                <select
                  value={config.output_container}
                  onChange={(e) =>
                    setConfig((prev) => ({
                      ...prev,
                      output_container: e.target.value,
                      preset: 'custom',
                    }))
                  }
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                >
                  <option value="mp4">MP4 (MPEG-4 Part 14 - Universal)</option>
                  <option value="mkv">MKV (Matroska - Maximum Features)</option>
                  <option value="webm">WebM (VP9 / AV1 web native)</option>
                  <option value="mp3">MP3 (MPEG-1 Audio Layer III)</option>
                  <option value="m4a">M4A (AAC Audio Container)</option>
                  <option value="flac">FLAC (Free Lossless Audio)</option>
                  <option value="wav">WAV (Waveform Audio Lossless)</option>
                  <option value="opus">OPUS (Ogg Opus Audio)</option>
                </select>
              </div>
            </div>
          )}

          {/* Section: Video */}
          {activeSection === 'video' && (
            <div className="space-y-3.5">
              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Video Codec Preference
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { id: 'any', label: 'Any / Default' },
                    { id: 'h264', label: 'H.264 / AVC (Most Compatible)' },
                    { id: 'vp9', label: 'VP9 (Google/YouTube native)' },
                    { id: 'av1', label: 'AV1 (Next-gen efficient)' },
                  ].map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => setConfig((prev) => ({ ...prev, video_codec: c.id, preset: 'custom' }))}
                      className={`p-2.5 rounded-xl border text-left text-xs transition ${
                        config.video_codec === c.id
                          ? 'border-brand-600 bg-brand-50/50 dark:bg-brand-950/30 text-brand-900 dark:text-brand-100 font-bold'
                          : 'border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300'
                      }`}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Max Resolution Ceiling
                </label>
                <select
                  value={config.quality}
                  onChange={(e) => setConfig((prev) => ({ ...prev, quality: e.target.value, preset: 'custom' }))}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                >
                  <option value="best">Best Available (Unlimited 4K/8K)</option>
                  <option value="2160p">2160p (4K UHD)</option>
                  <option value="1440p">1440p (QHD)</option>
                  <option value="1080p">1080p (Full HD)</option>
                  <option value="720p">720p (HD)</option>
                  <option value="480p">480p (SD)</option>
                  <option value="360p">360p (Data Saver)</option>
                </select>
              </div>
            </div>
          )}

          {/* Section: Audio */}
          {activeSection === 'audio' && (
            <div className="space-y-3.5">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-xs font-bold text-zinc-700 dark:text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.audio_mode === 'audio_only'}
                    onChange={(e) =>
                      setConfig((prev) => ({
                        ...prev,
                        audio_mode: e.target.checked ? 'audio_only' : 'merge',
                        output_container: e.target.checked ? prev.audio_format : 'mp4',
                        preset: 'custom',
                      }))
                    }
                    className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500"
                  />
                  <span>Extract Pure Audio Track (Discard Video)</span>
                </label>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                    Audio Format Transcode
                  </label>
                  <select
                    value={config.audio_format}
                    onChange={(e) =>
                      setConfig((prev) => ({
                        ...prev,
                        audio_format: e.target.value,
                        output_container: prev.audio_mode === 'audio_only' ? e.target.value : prev.output_container,
                        preset: 'custom',
                      }))
                    }
                    className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800"
                  >
                    <option value="mp3">MP3</option>
                    <option value="m4a">M4A / AAC</option>
                    <option value="wav">WAV</option>
                    <option value="flac">FLAC</option>
                    <option value="opus">OPUS</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                    Audio Quality Target
                  </label>
                  <select
                    value={config.audio_quality}
                    onChange={(e) => setConfig((prev) => ({ ...prev, audio_quality: e.target.value, preset: 'custom' }))}
                    className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800"
                  >
                    <option value="0">0 (Best VBR Transcoding)</option>
                    <option value="320k">320 kbps (CBR High-Fidelity)</option>
                    <option value="256k">256 kbps (CBR Standard)</option>
                    <option value="192k">192 kbps (CBR)</option>
                    <option value="128k">128 kbps (Compact)</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Section: Network */}
          {activeSection === 'network' && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Network Retries (1-100)
                </label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={config.retries}
                  onChange={(e) =>
                    setConfig((prev) => ({
                      ...prev,
                      retries: parseInt(e.target.value) || 10,
                      preset: 'custom',
                    }))
                  }
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Socket Timeout (Seconds)
                </label>
                <input
                  type="number"
                  min={5}
                  max={3600}
                  value={config.timeout}
                  onChange={(e) =>
                    setConfig((prev) => ({
                      ...prev,
                      timeout: parseInt(e.target.value) || 30,
                      preset: 'custom',
                    }))
                  }
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Concurrent Fragments (1-16)
                </label>
                <input
                  type="number"
                  min={1}
                  max={16}
                  value={config.concurrent_fragments}
                  onChange={(e) =>
                    setConfig((prev) => ({
                      ...prev,
                      concurrent_fragments: parseInt(e.target.value) || 1,
                      preset: 'custom',
                    }))
                  }
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 font-mono"
                />
              </div>
            </div>
          )}

          {/* Section: Subtitles */}
          {activeSection === 'subtitles' && (
            <div className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <label className="flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.subtitles}
                    onChange={(e) => setConfig((prev) => ({ ...prev, subtitles: e.target.checked, preset: 'custom' }))}
                    className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500"
                  />
                  <span>Download Subtitles</span>
                </label>

                <label className="flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.embed_subtitles}
                    onChange={(e) =>
                      setConfig((prev) => ({ ...prev, embed_subtitles: e.target.checked, preset: 'custom' }))
                    }
                    className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500"
                  />
                  <span>Embed Subtitles in Video</span>
                </label>

                <label className="flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.auto_subtitles}
                    onChange={(e) =>
                      setConfig((prev) => ({ ...prev, auto_subtitles: e.target.checked, preset: 'custom' }))
                    }
                    className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500"
                  />
                  <span>Include Auto-Generated</span>
                </label>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                  Language Filter (Comma separated, e.g. en,es,fr or all)
                </label>
                <input
                  type="text"
                  value={config.subtitle_langs}
                  onChange={(e) => setConfig((prev) => ({ ...prev, subtitle_langs: e.target.value, preset: 'custom' }))}
                  className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 font-mono"
                  placeholder="en,all"
                />
              </div>
            </div>
          )}

          {/* Section: Metadata & Chapters */}
          {activeSection === 'metadata' && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <label className="flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.embed_metadata}
                  onChange={(e) => setConfig((prev) => ({ ...prev, embed_metadata: e.target.checked, preset: 'custom' }))}
                  className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500"
                />
                <span>Embed Atomic Metadata</span>
              </label>

              <label className="flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.embed_thumbnail}
                  onChange={(e) =>
                    setConfig((prev) => ({ ...prev, embed_thumbnail: e.target.checked, preset: 'custom' }))
                  }
                  className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500"
                />
                <span>Embed Thumbnail Art</span>
              </label>

              <label className="flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.write_chapters}
                  onChange={(e) =>
                    setConfig((prev) => ({ ...prev, write_chapters: e.target.checked, preset: 'custom' }))
                  }
                  className="w-4 h-4 rounded text-brand-600 focus:ring-brand-500"
                />
                <span>Embed Media Chapters</span>
              </label>
            </div>
          )}

          {/* Section: Playlist */}
          {activeSection === 'playlist' && (
            <div className="space-y-3">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 cursor-pointer">
                  <input
                    type="radio"
                    name="playlist_mode"
                    checked={config.playlist_mode === 'single'}
                    onChange={() => setConfig((prev) => ({ ...prev, playlist_mode: 'single', preset: 'custom' }))}
                    className="text-brand-600"
                  />
                  <span>Single Media Item (Stop at 1)</span>
                </label>

                <label className="flex items-center gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 cursor-pointer">
                  <input
                    type="radio"
                    name="playlist_mode"
                    checked={config.playlist_mode === 'playlist'}
                    onChange={() => setConfig((prev) => ({ ...prev, playlist_mode: 'playlist', preset: 'custom' }))}
                    className="text-brand-600"
                  />
                  <span>Download Entire Playlist</span>
                </label>
              </div>

              {config.playlist_mode === 'playlist' && (
                <div>
                  <label className="block text-xs font-bold text-zinc-700 dark:text-zinc-300 mb-1">
                    Playlist Items Filter (e.g. 1-10 or 1,3,5)
                  </label>
                  <input
                    type="text"
                    value={config.playlist_items || ''}
                    onChange={(e) =>
                      setConfig((prev) => ({ ...prev, playlist_items: e.target.value, preset: 'custom' }))
                    }
                    className="w-full px-3 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 font-mono"
                    placeholder="1-20"
                  />
                </div>
              )}
            </div>
          )}

          {/* Reset advanced settings */}
          <div className="flex justify-end pt-2">
            <button
              type="button"
              onClick={handleResetToPreset}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
            >
              <ArrowCounterClockwise size={13} />
              <span>Reset to Defaults</span>
            </button>
          </div>
        </div>
      )}

      {/* Pre-Download Configuration Summary Bar */}
      <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/70 border border-zinc-200/70 dark:border-zinc-800 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex flex-wrap items-center gap-1.5 text-zinc-600 dark:text-zinc-300 font-mono text-[11px]">
          <span className="font-sans font-bold text-zinc-400 uppercase tracking-wider text-[10px]">
            Target Config:
          </span>
          {summaryParts.map((part, idx) => (
            <React.Fragment key={idx}>
              <span className="px-1.5 py-0.5 rounded bg-zinc-200/80 dark:bg-zinc-800/90 text-zinc-800 dark:text-zinc-200">
                {part}
              </span>
              {idx < summaryParts.length - 1 && <span className="text-zinc-400">•</span>}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Execute Download CTA */}
      <div className="pt-1">
        <button
          type="submit"
          disabled={isStarting}
          className="w-full flex items-center justify-center gap-2.5 px-6 py-4 rounded-xl text-sm font-bold text-white bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 active:scale-[0.99] disabled:opacity-50 transition shadow-md shadow-brand-500/25"
        >
          <DownloadSimple size={20} weight="bold" />
          <span>{isStarting ? 'Queueing Extraction Job...' : 'Start Extraction Download'}</span>
        </button>
      </div>
    </form>
  );
};

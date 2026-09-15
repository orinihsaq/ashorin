import json
from pathlib import Path
import sqlite3
import time
from app.utils.logger import logger


MIGRATIONS = [
    # Migration 1: Initial schema for Media Automation Platform
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        title TEXT,
        thumbnail TEXT,
        status TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'NORMAL',
        queue_order INTEGER DEFAULT 0,
        progress REAL DEFAULT 0.0,
        speed TEXT,
        eta TEXT,
        current_stage TEXT,
        downloaded_bytes INTEGER DEFAULT 0,
        total_bytes INTEGER,
        retry_count INTEGER DEFAULT 0,
        max_retries INTEGER DEFAULT 3,
        next_retry_at REAL,
        scheduled_for REAL,
        schedule_type TEXT DEFAULT 'once',
        bandwidth_limit INTEGER DEFAULT 0,
        config_json TEXT,
        profile_id TEXT,
        output_filename TEXT,
        output_path TEXT,
        output_filesize INTEGER,
        error_message TEXT,
        error_details TEXT,
        is_playlist INTEGER DEFAULT 0,
        playlist_title TEXT,
        total_items INTEGER DEFAULT 0,
        completed_items INTEGER DEFAULT 0,
        failed_items INTEGER DEFAULT 0,
        skipped_items INTEGER DEFAULT 0,
        current_item_index INTEGER DEFAULT 0,
        current_item_title TEXT,
        created_at REAL NOT NULL,
        started_at REAL,
        completed_at REAL,
        user_id TEXT DEFAULT 'default'
    );
    CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
    CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority);
    CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);

    CREATE TABLE IF NOT EXISTS media_library (
        id TEXT PRIMARY KEY,
        job_id TEXT,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        relative_path TEXT NOT NULL,
        source_url TEXT NOT NULL,
        extractor TEXT,
        media_id TEXT,
        uploader TEXT,
        playlist_name TEXT,
        duration INTEGER,
        duration_string TEXT,
        resolution TEXT,
        container TEXT,
        filesize INTEGER,
        thumbnail_url TEXT,
        is_favorite INTEGER DEFAULT 0,
        is_protected INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        downloaded_at REAL NOT NULL,
        user_id TEXT DEFAULT 'default'
    );
    CREATE INDEX IF NOT EXISTS idx_media_created ON media_library(created_at);
    CREATE INDEX IF NOT EXISTS idx_media_title ON media_library(title);
    CREATE INDEX IF NOT EXISTS idx_media_source ON media_library(source_url);
    CREATE INDEX IF NOT EXISTS idx_media_fav ON media_library(is_favorite);
    CREATE INDEX IF NOT EXISTS idx_media_prot ON media_library(is_protected);

    CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        badge TEXT,
        is_builtin INTEGER DEFAULT 0,
        is_default INTEGER DEFAULT 0,
        config_json TEXT NOT NULL,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS rules (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        condition_type TEXT NOT NULL,
        condition_value TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        priority INTEGER DEFAULT 0,
        is_enabled INTEGER DEFAULT 1,
        created_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS api_keys (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL,
        key_prefix TEXT NOT NULL,
        created_at REAL NOT NULL,
        last_used_at REAL,
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS webhooks (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        events_json TEXT NOT NULL,
        signing_secret TEXT,
        is_enabled INTEGER DEFAULT 1,
        created_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS webhook_deliveries (
        id TEXT PRIMARY KEY,
        webhook_id TEXT NOT NULL,
        event TEXT NOT NULL,
        payload_summary TEXT,
        status_code INTEGER,
        success INTEGER DEFAULT 0,
        attempt_count INTEGER DEFAULT 1,
        error_message TEXT,
        delivered_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_deliveries_webhook ON webhook_deliveries(webhook_id);

    CREATE TABLE IF NOT EXISTS tags (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        color TEXT DEFAULT '#9333ea'
    );

    CREATE TABLE IF NOT EXISTS media_tags (
        media_id TEXT NOT NULL,
        tag_id TEXT NOT NULL,
        PRIMARY KEY (media_id, tag_id)
    );
    """,
    # Migration 2: Smart Collections, Watchers, Recipes, Quality Upgrades, and Media Health
    """
    CREATE TABLE IF NOT EXISTS watchers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        source_url TEXT NOT NULL,
        source_type TEXT DEFAULT 'playlist',
        schedule TEXT DEFAULT 'every_6_hours',
        interval_seconds INTEGER DEFAULT 21600,
        status TEXT DEFAULT 'ACTIVE',
        profile_id TEXT DEFAULT 'recommended',
        recipe_id TEXT,
        target_quality TEXT DEFAULT '1080p',
        minimum_quality TEXT DEFAULT '720p',
        upgrade_policy TEXT DEFAULT 'ask',
        duplicate_policy TEXT DEFAULT 'skip',
        destination_rule TEXT,
        download_new INTEGER DEFAULT 1,
        notify_new INTEGER DEFAULT 1,
        notify_completed INTEGER DEFAULT 1,
        notify_failed INTEGER DEFAULT 1,
        items_tracked INTEGER DEFAULT 0,
        items_downloaded INTEGER DEFAULT 0,
        last_checked REAL,
        next_check REAL,
        last_sync_result TEXT,
        consecutive_failures INTEGER DEFAULT 0,
        last_error TEXT,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_watchers_status ON watchers(status);
    CREATE INDEX IF NOT EXISTS idx_watchers_next_check ON watchers(next_check);
    CREATE INDEX IF NOT EXISTS idx_watchers_source_url ON watchers(source_url);

    CREATE TABLE IF NOT EXISTS watcher_runs (
        id TEXT PRIMARY KEY,
        watcher_id TEXT NOT NULL,
        started_at REAL NOT NULL,
        completed_at REAL,
        status TEXT NOT NULL,
        items_seen INTEGER DEFAULT 0,
        new_items INTEGER DEFAULT 0,
        duplicates INTEGER DEFAULT 0,
        upgrades INTEGER DEFAULT 0,
        queued INTEGER DEFAULT 0,
        failed INTEGER DEFAULT 0,
        details_json TEXT,
        error TEXT,
        FOREIGN KEY (watcher_id) REFERENCES watchers(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_watcher_runs_watcher ON watcher_runs(watcher_id);
    CREATE INDEX IF NOT EXISTS idx_watcher_runs_started ON watcher_runs(started_at);

    CREATE TABLE IF NOT EXISTS recipes (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        profile_id TEXT NOT NULL,
        storage_folder TEXT,
        duplicate_policy TEXT DEFAULT 'skip',
        target_quality TEXT DEFAULT 'best',
        minimum_quality TEXT DEFAULT '720p',
        upgrade_policy TEXT DEFAULT 'ask',
        retention_days INTEGER DEFAULT 0,
        notify_events_json TEXT,
        is_builtin INTEGER DEFAULT 0,
        is_default INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS quality_targets (
        id TEXT PRIMARY KEY,
        media_id TEXT NOT NULL,
        current_height INTEGER,
        current_fps INTEGER,
        current_filesize INTEGER,
        target_quality TEXT NOT NULL,
        minimum_quality TEXT NOT NULL,
        upgrade_policy TEXT DEFAULT 'ask',
        upgrade_available INTEGER DEFAULT 0,
        upgrade_height INTEGER,
        upgrade_filesize INTEGER,
        upgrade_source_url TEXT,
        status TEXT DEFAULT 'PENDING',
        updated_at REAL NOT NULL,
        FOREIGN KEY (media_id) REFERENCES media_library(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_quality_media ON quality_targets(media_id);
    CREATE INDEX IF NOT EXISTS idx_quality_upgrade_avail ON quality_targets(upgrade_available);

    CREATE TABLE IF NOT EXISTS health_scans (
        id TEXT PRIMARY KEY,
        started_at REAL NOT NULL,
        completed_at REAL,
        status TEXT NOT NULL,
        files_scanned INTEGER DEFAULT 0,
        issues_found INTEGER DEFAULT 0,
        issues_repaired INTEGER DEFAULT 0,
        storage_recoverable_bytes INTEGER DEFAULT 0,
        summary_json TEXT
    );

    CREATE TABLE IF NOT EXISTS health_issues (
        id TEXT PRIMARY KEY,
        scan_id TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        severity TEXT DEFAULT 'warning',
        media_id TEXT,
        file_path TEXT,
        title TEXT,
        description TEXT NOT NULL,
        details_json TEXT,
        recommended_action TEXT NOT NULL,
        recoverable_bytes INTEGER DEFAULT 0,
        is_resolved INTEGER DEFAULT 0,
        resolved_at REAL,
        resolution_action TEXT,
        created_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_health_issues_scan ON health_issues(scan_id);
    CREATE INDEX IF NOT EXISTS idx_health_issues_resolved ON health_issues(is_resolved);
    CREATE INDEX IF NOT EXISTS idx_health_issues_type ON health_issues(issue_type);
    """,

    # Migration 2: BitTorrent support
    """
    ALTER TABLE jobs ADD COLUMN provider TEXT DEFAULT 'ytdlp';
    ALTER TABLE jobs ADD COLUMN info_hash TEXT;

    CREATE TABLE IF NOT EXISTS torrents (
        id TEXT PRIMARY KEY,
        job_id TEXT,
        info_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        magnet_uri TEXT,
        torrent_file_path TEXT,
        total_size INTEGER DEFAULT 0,
        downloaded_size INTEGER DEFAULT 0,
        uploaded_size INTEGER DEFAULT 0,
        ratio REAL DEFAULT 0.0,
        status TEXT NOT NULL,
        seeding_mode TEXT DEFAULT 'stop',
        seeding_until REAL,
        download_dir TEXT NOT NULL,
        piece_count INTEGER DEFAULT 0,
        piece_length INTEGER DEFAULT 0,
        trackers_json TEXT,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_torrents_info_hash ON torrents(info_hash);
    CREATE INDEX IF NOT EXISTS idx_torrents_status ON torrents(status);

    CREATE TABLE IF NOT EXISTS torrent_files (
        id TEXT PRIMARY KEY,
        torrent_id TEXT NOT NULL,
        file_index INTEGER NOT NULL,
        path TEXT NOT NULL,
        size INTEGER NOT NULL,
        selected INTEGER NOT NULL DEFAULT 1,
        priority TEXT NOT NULL DEFAULT 'normal',
        downloaded_bytes INTEGER DEFAULT 0,
        is_completed INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        FOREIGN KEY (torrent_id) REFERENCES torrents(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_torrent_files_torrent ON torrent_files(torrent_id);

    ALTER TABLE media_library ADD COLUMN source_provider TEXT DEFAULT 'ytdlp';
    ALTER TABLE media_library ADD COLUMN torrent_id TEXT;
    CREATE INDEX IF NOT EXISTS idx_media_provider ON media_library(source_provider);
    """,
    # Migration 3: Magnet input_type column
    """
    ALTER TABLE jobs ADD COLUMN input_type TEXT DEFAULT 'url';
    """,

    # Migration 4: Media Discovery Foundation & TMDB Cache
    """
    CREATE TABLE IF NOT EXISTS discovered_movies (
        id TEXT PRIMARY KEY,
        tmdb_id INTEGER NOT NULL UNIQUE,
        title TEXT NOT NULL,
        original_title TEXT,
        release_date TEXT,
        year INTEGER,
        overview TEXT,
        poster_path TEXT,
        backdrop_path TEXT,
        genres_json TEXT,
        runtime INTEGER,
        vote_average REAL DEFAULT 0.0,
        vote_count INTEGER DEFAULT 0,
        popularity REAL DEFAULT 0.0,
        status TEXT,
        tagline TEXT,
        raw_json TEXT,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_discovered_movies_tmdb_id ON discovered_movies(tmdb_id);
    CREATE INDEX IF NOT EXISTS idx_discovered_movies_title ON discovered_movies(title);
    CREATE INDEX IF NOT EXISTS idx_discovered_movies_year ON discovered_movies(year);

    CREATE TABLE IF NOT EXISTS discovered_series (
        id TEXT PRIMARY KEY,
        tmdb_id INTEGER NOT NULL UNIQUE,
        name TEXT NOT NULL,
        original_name TEXT,
        first_air_date TEXT,
        year INTEGER,
        overview TEXT,
        poster_path TEXT,
        backdrop_path TEXT,
        genres_json TEXT,
        number_of_seasons INTEGER DEFAULT 0,
        number_of_episodes INTEGER DEFAULT 0,
        vote_average REAL DEFAULT 0.0,
        vote_count INTEGER DEFAULT 0,
        popularity REAL DEFAULT 0.0,
        status TEXT,
        tagline TEXT,
        raw_json TEXT,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_discovered_series_tmdb_id ON discovered_series(tmdb_id);
    CREATE INDEX IF NOT EXISTS idx_discovered_series_name ON discovered_series(name);
    CREATE INDEX IF NOT EXISTS idx_discovered_series_year ON discovered_series(year);

    CREATE TABLE IF NOT EXISTS discovery_cache (
        cache_key TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        data_json TEXT NOT NULL,
        expires_at REAL NOT NULL,
        created_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_discovery_cache_expires ON discovery_cache(expires_at);
    CREATE INDEX IF NOT EXISTS idx_discovery_cache_cat ON discovery_cache(category);
    """,

    # Migration 6: Movie Manager, Quality Profiles, and Root Folders
    """
    CREATE TABLE IF NOT EXISTS root_folders (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        path TEXT NOT NULL UNIQUE,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_root_folders_path ON root_folders(path);

    CREATE TABLE IF NOT EXISTS quality_profiles (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        allowed_resolutions_json TEXT NOT NULL,
        min_resolution TEXT,
        max_resolution TEXT,
        preferred_resolution TEXT,
        preferred_source TEXT,
        preferred_codec TEXT,
        min_size_bytes INTEGER DEFAULT 0,
        max_size_bytes INTEGER DEFAULT 0,
        preferred_audio TEXT,
        cutoff_quality TEXT,
        is_builtin INTEGER DEFAULT 0,
        is_default INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS movies (
        id TEXT PRIMARY KEY,
        tmdb_id INTEGER NOT NULL UNIQUE,
        title TEXT NOT NULL,
        original_title TEXT,
        year INTEGER,
        overview TEXT,
        poster_path TEXT,
        backdrop_path TEXT,
        runtime INTEGER,
        genres_json TEXT,
        release_date TEXT,
        root_folder_id TEXT NOT NULL,
        quality_profile_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'WANTED',
        current_media_path TEXT,
        current_file_size INTEGER,
        current_resolution TEXT,
        current_codec TEXT,
        current_source TEXT,
        monitored INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        FOREIGN KEY (root_folder_id) REFERENCES root_folders(id) ON DELETE RESTRICT,
        FOREIGN KEY (quality_profile_id) REFERENCES quality_profiles(id) ON DELETE RESTRICT
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_movies_tmdb_id ON movies(tmdb_id);
    CREATE INDEX IF NOT EXISTS idx_movies_status ON movies(status);
    CREATE INDEX IF NOT EXISTS idx_movies_profile ON movies(quality_profile_id);
    CREATE INDEX IF NOT EXISTS idx_movies_folder ON movies(root_folder_id);
    CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);

    ALTER TABLE jobs ADD COLUMN movie_id TEXT;
    CREATE INDEX IF NOT EXISTS idx_jobs_movie_id ON jobs(movie_id);
    """,
    # 7. Series Manager + Seasons + Episodes (Phase 4)
    """
    CREATE TABLE IF NOT EXISTS series (
        id TEXT PRIMARY KEY,
        tmdb_id INTEGER NOT NULL UNIQUE,
        name TEXT NOT NULL,
        original_name TEXT,
        year INTEGER,
        overview TEXT,
        poster_path TEXT,
        backdrop_path TEXT,
        first_air_date TEXT,
        genres_json TEXT,
        status TEXT,
        root_folder_id TEXT NOT NULL,
        quality_profile_id TEXT NOT NULL,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        FOREIGN KEY (root_folder_id) REFERENCES root_folders(id) ON DELETE RESTRICT,
        FOREIGN KEY (quality_profile_id) REFERENCES quality_profiles(id) ON DELETE RESTRICT
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_series_tmdb_id ON series(tmdb_id);
    CREATE INDEX IF NOT EXISTS idx_series_profile ON series(quality_profile_id);
    CREATE INDEX IF NOT EXISTS idx_series_folder ON series(root_folder_id);
    CREATE INDEX IF NOT EXISTS idx_series_name ON series(name);

    CREATE TABLE IF NOT EXISTS seasons (
        id TEXT PRIMARY KEY,
        series_id TEXT NOT NULL,
        tmdb_id INTEGER,
        season_number INTEGER NOT NULL,
        name TEXT NOT NULL,
        overview TEXT,
        poster_path TEXT,
        air_date TEXT,
        episode_count INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
        UNIQUE (series_id, season_number)
    );
    CREATE INDEX IF NOT EXISTS idx_seasons_series_id ON seasons(series_id);
    CREATE INDEX IF NOT EXISTS idx_seasons_number ON seasons(series_id, season_number);

    CREATE TABLE IF NOT EXISTS episodes (
        id TEXT PRIMARY KEY,
        series_id TEXT NOT NULL,
        season_id TEXT NOT NULL,
        tmdb_id INTEGER,
        season_number INTEGER NOT NULL,
        episode_number INTEGER NOT NULL,
        name TEXT NOT NULL,
        overview TEXT,
        still_path TEXT,
        air_date TEXT,
        runtime INTEGER,
        status TEXT NOT NULL DEFAULT 'WANTED',
        current_media_path TEXT,
        current_file_size INTEGER,
        current_resolution TEXT,
        current_codec TEXT,
        current_source TEXT,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
        FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE CASCADE,
        UNIQUE (series_id, season_number, episode_number)
    );
    CREATE INDEX IF NOT EXISTS idx_episodes_series ON episodes(series_id);
    CREATE INDEX IF NOT EXISTS idx_episodes_season ON episodes(season_id);
    CREATE INDEX IF NOT EXISTS idx_episodes_status ON episodes(status);
    CREATE INDEX IF NOT EXISTS idx_episodes_lookup ON episodes(series_id, season_number, episode_number);

    ALTER TABLE jobs ADD COLUMN episode_id TEXT;
    CREATE INDEX IF NOT EXISTS idx_jobs_episode_id ON jobs(episode_id);
    """,
    # 8. Automatic Monitoring + Scheduled Missing-Media Searching (Phase 6)
    """
    ALTER TABLE series ADD COLUMN monitored INTEGER DEFAULT 1;

    CREATE TABLE IF NOT EXISTS monitoring_search_history (
        id TEXT PRIMARY KEY,
        target_type TEXT NOT NULL,
        target_id TEXT NOT NULL,
        title TEXT NOT NULL,
        trigger TEXT NOT NULL,
        status TEXT NOT NULL,
        result_count INTEGER DEFAULT 0,
        best_score INTEGER,
        duration_ms INTEGER,
        error_code TEXT,
        error_message TEXT,
        started_at REAL NOT NULL,
        completed_at REAL NOT NULL,
        created_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_msh_target ON monitoring_search_history(target_type, target_id);
    CREATE INDEX IF NOT EXISTS idx_msh_created ON monitoring_search_history(created_at);
    CREATE INDEX IF NOT EXISTS idx_msh_status ON monitoring_search_history(status);
    CREATE INDEX IF NOT EXISTS idx_msh_trigger ON monitoring_search_history(trigger);
    """,
    # 9. Automatic Release Selection + Safe Automatic Missing-Media Downloads (Phase 7A)
    """
    ALTER TABLE movies ADD COLUMN automation_enabled INTEGER DEFAULT 0;
    ALTER TABLE series ADD COLUMN automation_enabled INTEGER DEFAULT 0;

    CREATE TABLE IF NOT EXISTS automation_history (
        id TEXT PRIMARY KEY,
        target_type TEXT NOT NULL,
        target_id TEXT NOT NULL,
        title TEXT NOT NULL,
        trigger TEXT NOT NULL,
        action TEXT NOT NULL,
        status TEXT NOT NULL,
        selected_release_title TEXT,
        selected_release_indexer TEXT,
        selected_release_size INTEGER,
        selected_release_seeders INTEGER,
        selected_release_score INTEGER,
        selected_info_hash TEXT,
        score_reasons_json TEXT,
        rejection_reason TEXT,
        job_id TEXT,
        dry_run INTEGER DEFAULT 0,
        evaluations_json TEXT,
        error_code TEXT,
        error_message TEXT,
        started_at REAL,
        completed_at REAL,
        created_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_automation_history_target ON automation_history(target_type, target_id);
    CREATE INDEX IF NOT EXISTS idx_automation_history_created ON automation_history(created_at);
    CREATE INDEX IF NOT EXISTS idx_automation_history_status ON automation_history(status);
    CREATE INDEX IF NOT EXISTS idx_automation_history_trigger ON automation_history(trigger);
    CREATE INDEX IF NOT EXISTS idx_automation_history_action ON automation_history(action);
    """,
    # 10. Explicit Opt-In: Default automation_enabled to 0 for movies and series (Phase 7A.1)
    """
    UPDATE movies SET automation_enabled = 0 WHERE automation_enabled IS NULL OR automation_enabled = 1;
    UPDATE series SET automation_enabled = 0 WHERE automation_enabled IS NULL OR automation_enabled = 1;
    """,
    # 11. Quality Upgrades metadata on jobs (Phase 7B)
    """
    ALTER TABLE jobs ADD COLUMN job_type TEXT DEFAULT 'NORMAL';
    ALTER TABLE jobs ADD COLUMN is_upgrade INTEGER DEFAULT 0;
    ALTER TABLE jobs ADD COLUMN previous_quality TEXT;
    ALTER TABLE jobs ADD COLUMN upgrade_reason TEXT;
    """,
    # 12. Import Engine & Verification (Phase 8A)
    """
    CREATE TABLE IF NOT EXISTS import_candidates (
        id TEXT PRIMARY KEY,
        job_id TEXT,
        source_path TEXT NOT NULL,
        source_relative_path TEXT NOT NULL,
        source_root TEXT NOT NULL,
        file_size_bytes INTEGER NOT NULL,
        source_mtime REAL NOT NULL,
        media_type TEXT NOT NULL DEFAULT 'video',
        movie_id TEXT,
        series_id TEXT,
        season_id TEXT,
        episode_id TEXT,
        match_type TEXT NOT NULL DEFAULT 'UNKNOWN',
        match_confidence INTEGER NOT NULL DEFAULT 0,
        verification_status TEXT NOT NULL DEFAULT 'DISCOVERED',
        candidate_status TEXT NOT NULL DEFAULT 'UNMATCHED',
        duplicate_status TEXT NOT NULL DEFAULT 'NONE',
        quality_classification TEXT NOT NULL DEFAULT 'UNKNOWN',
        current_library_path TEXT,
        media_info_json TEXT,
        match_reasons_json TEXT,
        validation_errors_json TEXT,
        source_metadata_json TEXT,
        fingerprint TEXT,
        rejection_reason TEXT,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        verified_at REAL,
        reviewed_at REAL,
        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
        FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE SET NULL,
        FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET NULL,
        FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_import_candidates_job_id ON import_candidates(job_id);
    CREATE INDEX IF NOT EXISTS idx_import_candidates_status ON import_candidates(candidate_status);
    CREATE INDEX IF NOT EXISTS idx_import_candidates_verification ON import_candidates(verification_status);
    CREATE INDEX IF NOT EXISTS idx_import_candidates_movie_id ON import_candidates(movie_id);
    CREATE INDEX IF NOT EXISTS idx_import_candidates_episode_id ON import_candidates(episode_id);
    CREATE INDEX IF NOT EXISTS idx_import_candidates_fingerprint ON import_candidates(fingerprint);
    CREATE INDEX IF NOT EXISTS idx_import_candidates_source ON import_candidates(source_path);
    CREATE INDEX IF NOT EXISTS idx_import_candidates_created_at ON import_candidates(created_at);

    CREATE TABLE IF NOT EXISTS import_history (
        id TEXT PRIMARY KEY,
        candidate_id TEXT,
        job_id TEXT,
        action TEXT NOT NULL,
        status TEXT NOT NULL,
        target_type TEXT,
        target_id TEXT,
        title TEXT,
        details_json TEXT,
        error_code TEXT,
        error_message TEXT,
        created_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_import_history_candidate ON import_history(candidate_id);
    CREATE INDEX IF NOT EXISTS idx_import_history_job ON import_history(job_id);
    CREATE INDEX IF NOT EXISTS idx_import_history_created ON import_history(created_at);
    """,
    # 13. Naming & Organization Engine (Phase 8B)
    """
    ALTER TABLE import_candidates ADD COLUMN destination_path TEXT;
    ALTER TABLE import_candidates ADD COLUMN organization_operation_id TEXT;

    CREATE TABLE IF NOT EXISTS import_organization_operations (
        id TEXT PRIMARY KEY,
        candidate_id TEXT NOT NULL,
        source_path TEXT NOT NULL,
        destination_path TEXT NOT NULL,
        operation_type TEXT NOT NULL DEFAULT 'MOVE',
        status TEXT NOT NULL DEFAULT 'PREVIEWED',
        source_size_before INTEGER,
        source_fingerprint_before TEXT,
        destination_size_after INTEGER,
        destination_fingerprint_after TEXT,
        conflict_status TEXT NOT NULL DEFAULT 'DESTINATION_AVAILABLE',
        error_code TEXT,
        error_message TEXT,
        details_json TEXT,
        created_at REAL NOT NULL,
        started_at REAL,
        completed_at REAL,
        FOREIGN KEY (candidate_id) REFERENCES import_candidates(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_org_ops_candidate ON import_organization_operations(candidate_id);
    CREATE INDEX IF NOT EXISTS idx_org_ops_status ON import_organization_operations(status);
    CREATE INDEX IF NOT EXISTS idx_org_ops_created ON import_organization_operations(created_at);
    CREATE INDEX IF NOT EXISTS idx_org_ops_dest ON import_organization_operations(destination_path);
    """,
    # 14. Quality Upgrade Replacement Engine (Phase 8C)
    """
    CREATE TABLE IF NOT EXISTS quality_upgrade_replacements (
        id TEXT PRIMARY KEY,
        candidate_id TEXT NOT NULL,
        movie_id TEXT,
        series_id TEXT,
        episode_id TEXT,
        existing_library_path TEXT NOT NULL,
        candidate_source_path TEXT NOT NULL,
        destination_path TEXT NOT NULL,
        staging_path TEXT,
        old_media_backup_path TEXT,
        archive_path TEXT,
        old_media_fingerprint TEXT NOT NULL,
        old_media_size INTEGER NOT NULL,
        old_media_mtime REAL NOT NULL,
        old_media_quality_json TEXT,
        new_media_fingerprint TEXT,
        new_media_size INTEGER,
        new_media_mtime REAL,
        new_media_quality_json TEXT,
        quality_score_before REAL,
        quality_score_after REAL,
        upgrade_reason TEXT,
        replacement_policy TEXT NOT NULL DEFAULT 'ARCHIVE',
        status TEXT NOT NULL DEFAULT 'PREVIEWED',
        rollback_status TEXT,
        error_code TEXT,
        error_message TEXT,
        details_json TEXT,
        created_at REAL NOT NULL,
        approved_at REAL,
        started_at REAL,
        staging_completed_at REAL,
        replacement_committed_at REAL,
        completed_at REAL,
        archived_at REAL,
        deleted_at REAL,
        FOREIGN KEY (candidate_id) REFERENCES import_candidates(id)
    );
    CREATE INDEX IF NOT EXISTS idx_qur_candidate ON quality_upgrade_replacements(candidate_id);
    CREATE INDEX IF NOT EXISTS idx_qur_movie ON quality_upgrade_replacements(movie_id);
    CREATE INDEX IF NOT EXISTS idx_qur_episode ON quality_upgrade_replacements(episode_id);
    CREATE INDEX IF NOT EXISTS idx_qur_status ON quality_upgrade_replacements(status);
    CREATE INDEX IF NOT EXISTS idx_qur_created ON quality_upgrade_replacements(created_at);
    CREATE INDEX IF NOT EXISTS idx_qur_existing_path ON quality_upgrade_replacements(existing_library_path);
    """,
]


def seed_default_profiles(conn: sqlite3.Connection) -> None:
    """Seeds standard built-in profiles if not already existing."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM profiles WHERE is_builtin = 1")
    count = cursor.fetchone()[0]
    if count > 0:
        return

    now = time.time()
    builtins = [
        (
            "recommended",
            "Recommended",
            "Balanced quality and format compatibility (1080p MP4 + metadata).",
            "Default",
            1,
            1,
            json.dumps({
                "preset": "recommended",
                "quality": "best",
                "output_container": "mp4",
                "audio_mode": "merge",
                "audio_format": "mp3",
                "audio_quality": "0",
                "video_codec": "any",
                "filename_template": "%(title).150B.%(ext)s",
                "subtitles": False,
                "embed_subtitles": False,
                "auto_subtitles": False,
                "subtitle_langs": "en",
                "embed_metadata": True,
                "embed_thumbnail": True,
                "write_chapters": False,
                "retries": 10,
                "timeout": 30,
                "concurrent_fragments": 1,
            }),
            now,
            now,
        ),
        (
            "best_quality",
            "Best Quality",
            "Maximum available video & audio stream preservation up to 4K/8K.",
            "Max Res",
            1,
            0,
            json.dumps({
                "preset": "best_quality",
                "quality": "best",
                "output_container": "mkv",
                "audio_mode": "merge",
                "audio_format": "mp3",
                "audio_quality": "0",
                "video_codec": "any",
                "filename_template": "%(title).150B.%(ext)s",
                "subtitles": True,
                "embed_subtitles": True,
                "auto_subtitles": False,
                "subtitle_langs": "en",
                "embed_metadata": True,
                "embed_thumbnail": True,
                "write_chapters": True,
                "retries": 15,
                "timeout": 60,
                "concurrent_fragments": 2,
            }),
            now,
            now,
        ),
        (
            "audio_only",
            "Audio Only",
            "Extract audio tracks as high-fidelity MP3 (320kbps) with embedded cover art.",
            "MP3 320k",
            1,
            0,
            json.dumps({
                "preset": "audio_only",
                "quality": "best",
                "output_container": "mp3",
                "audio_mode": "audio_only",
                "audio_format": "mp3",
                "audio_quality": "0",
                "video_codec": "any",
                "filename_template": "%(title).150B.%(ext)s",
                "subtitles": False,
                "embed_subtitles": False,
                "auto_subtitles": False,
                "subtitle_langs": "en",
                "embed_metadata": True,
                "embed_thumbnail": True,
                "write_chapters": False,
                "retries": 10,
                "timeout": 30,
                "concurrent_fragments": 1,
            }),
            now,
            now,
        ),
        (
            "small_file",
            "Small File",
            "Data-saving 720p H.264 profile optimized for mobile sharing & archiving.",
            "Compact",
            1,
            0,
            json.dumps({
                "preset": "small_file",
                "quality": "720p",
                "output_container": "mp4",
                "audio_mode": "merge",
                "audio_format": "mp3",
                "audio_quality": "128k",
                "video_codec": "h264",
                "filename_template": "%(title).100B.%(ext)s",
                "subtitles": False,
                "embed_subtitles": False,
                "auto_subtitles": False,
                "subtitle_langs": "en",
                "embed_metadata": True,
                "embed_thumbnail": False,
                "write_chapters": False,
                "retries": 5,
                "timeout": 20,
                "concurrent_fragments": 1,
            }),
            now,
            now,
        ),
        (
            "archive",
            "Archive Mode",
            "Complete preservation with subtitles, thumbnail, chapters, and metadata.",
            "Lossless",
            1,
            0,
            json.dumps({
                "preset": "archive",
                "quality": "best",
                "output_container": "mkv",
                "audio_mode": "merge",
                "audio_format": "mp3",
                "audio_quality": "0",
                "video_codec": "any",
                "filename_template": "%(upload_date>%Y-%m-%d)s - %(title).120B [%(id)s].%(ext)s",
                "subtitles": True,
                "embed_subtitles": True,
                "auto_subtitles": True,
                "subtitle_langs": "all",
                "embed_metadata": True,
                "embed_thumbnail": True,
                "write_chapters": True,
                "retries": 20,
                "timeout": 60,
                "concurrent_fragments": 2,
            }),
            now,
            now,
        ),
    ]

    cursor.executemany(
        """
        INSERT OR IGNORE INTO profiles (id, name, description, badge, is_builtin, is_default, config_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        builtins,
    )
    logger.info("Seeded 5 standard built-in profiles into SQLite.")


def run_migrations(conn: sqlite3.Connection) -> None:
    """Applies all pending database migrations in sequential order."""
    cursor = conn.cursor()
    # Check current migration level
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at REAL NOT NULL
        )
        """
    )
    conn.commit()

    cursor.execute("SELECT version FROM schema_migrations")
    applied_versions = {row[0] for row in cursor.fetchall()}

    for version, sql_script in enumerate(MIGRATIONS, start=1):
        if version not in applied_versions:
            logger.info(f"Applying database migration version {version}...")
            cursor.executescript(sql_script)
            cursor.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", (version, time.time()))
            conn.commit()
            logger.info(f"Migration version {version} applied successfully.")

    seed_default_profiles(conn)
    seed_default_recipes(conn)
    seed_default_quality_profiles(conn)
    seed_default_root_folders(conn)
    conn.commit()


def seed_default_recipes(conn: sqlite3.Connection) -> None:
    """Seeds standard built-in recipes if not already existing."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM recipes WHERE is_builtin = 1")
    count = cursor.fetchone()[0]
    if count > 0:
        return

    now = time.time()
    builtins = [
        (
            "video_archive",
            "Video Archive",
            "Complete video preservation with subtitles, chapters, and metadata in dedicated creator folders.",
            "archive",
            "Archive/{creator}/{title}",
            "skip",
            "best",
            "1080p",
            "ask",
            0,
            json.dumps(["job.completed", "job.failed"]),
            1,
            1,
            now,
            now,
        ),
        (
            "music",
            "Music",
            "High-fidelity 320kbps MP3 audio extraction organized by artist and collection.",
            "audio_only",
            "Music/{uploader}/{title}",
            "skip",
            "best",
            "audio_only",
            "never",
            0,
            json.dumps(["job.completed", "job.failed"]),
            1,
            0,
            now,
            now,
        ),
        (
            "mobile_video",
            "Mobile Video",
            "Compact 720p H.264 MP4 videos optimized for mobile storage and bandwidth.",
            "small_file",
            "Mobile/{title}",
            "skip",
            "720p",
            "480p",
            "ask",
            0,
            json.dumps(["job.completed"]),
            1,
            0,
            now,
            now,
        ),
        (
            "podcast",
            "Podcast",
            "Audio spoken-word preservation with embedded cover art and metadata.",
            "audio_only",
            "Podcasts/{creator}/{title}",
            "skip",
            "best",
            "audio_only",
            "never",
            0,
            json.dumps(["job.completed"]),
            1,
            0,
            now,
            now,
        ),
    ]

    cursor.executemany(
        """
        INSERT OR IGNORE INTO recipes (
            id, name, description, profile_id, storage_folder, duplicate_policy,
            target_quality, minimum_quality, upgrade_policy, retention_days,
            notify_events_json, is_builtin, is_default, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        builtins,
    )
    logger.info("Seeded 4 standard built-in recipes into SQLite.")


def seed_default_quality_profiles(conn: sqlite3.Connection) -> None:
    """Seeds standard built-in quality profiles for movie management if not already existing."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM quality_profiles WHERE is_builtin = 1")
    count = cursor.fetchone()[0]
    if count > 0:
        return

    now = time.time()
    builtins = [
        (
            "profile-recommended",
            "Recommended",
            "Balanced high quality preferring 1080p WEB-DL with wide player compatibility.",
            json.dumps(["720p", "1080p", "2160p"]),
            "720p",
            "2160p",
            "1080p",
            "WEB-DL",
            "H.264",
            0,
            0,
            None,
            "1080p",
            1,
            1,
            now,
            now,
        ),
        (
            "profile-1080p",
            "1080p Standard",
            "Strict 1080p High Definition video preferring WEB-DL / BluRay.",
            json.dumps(["1080p"]),
            "1080p",
            "1080p",
            "1080p",
            "WEB-DL",
            "H.264",
            0,
            0,
            None,
            "1080p",
            1,
            0,
            now,
            now,
        ),
        (
            "profile-2160p",
            "2160p 4K UHD",
            "Ultra-High Definition 4K HDR and Remux releases with fallback to 1080p.",
            json.dumps(["1080p", "2160p"]),
            "1080p",
            "2160p",
            "2160p",
            "Remux",
            "HEVC",
            0,
            0,
            None,
            "2160p",
            1,
            0,
            now,
            now,
        ),
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO quality_profiles (
            id, name, description, allowed_resolutions_json, min_resolution, max_resolution,
            preferred_resolution, preferred_source, preferred_codec, min_size_bytes, max_size_bytes,
            preferred_audio, cutoff_quality, is_builtin, is_default, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        builtins,
    )
    logger.info("Seeded 3 standard built-in quality profiles into SQLite.")


def seed_default_root_folders(conn: sqlite3.Connection) -> None:
    """Seeds default root folders for movies and series if they do not exist."""
    from app.config import settings
    cursor = conn.cursor()
    now = time.time()

    cursor.execute("SELECT COUNT(*) FROM root_folders WHERE id = 'default-movies-folder'")
    if cursor.fetchone()[0] == 0:
        data_media = Path("/data/media/movies") if Path("/data").exists() else settings.download_path / "movies"
        try:
            data_media.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        cursor.execute(
            """
            INSERT OR IGNORE INTO root_folders (id, name, path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("default-movies-folder", "Default Movies", str(data_media.resolve()), now, now),
        )

    cursor.execute("SELECT COUNT(*) FROM root_folders WHERE id = 'default-series-folder'")
    if cursor.fetchone()[0] == 0:
        data_series = Path("/data/media/series") if Path("/data").exists() else settings.download_path / "series"
        try:
            data_series.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        cursor.execute(
            """
            INSERT OR IGNORE INTO root_folders (id, name, path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("default-series-folder", "Default TV Series", str(data_series.resolve()), now, now),
        )


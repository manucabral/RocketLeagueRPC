(() => {
  const POLL_INTERVAL_MS = 1000
  const DEBOUNCE_MS = 220
  const MAX_DEBUG_LOGS = 250
  const DEFAULT_WAIT_MS = 120
  const STATS_API_WARNING = `Before launching Rocket League, edit:

<Install Dir>\\TAGame\\Config\\DefaultStatsAPI.ini

Use at least:

PacketSendRate=30 (any value > 0 enables the exporter)
Port=49123
Restart the game after changing the file.`

  const FEATURE_GROUPS = {
    match: ['arena_name', 'current_score', 'timer', 'game_mode', 'match_status'],
    player: ['player_name', 'player_score', 'goals', 'assists', 'shots'],
  }

  const FEATURE_LABELS = {
    arena_name: 'Arena',
    current_score: 'Score',
    timer: 'Timer',
    game_mode: 'Mode',
    match_status: 'Status',
    player_name: 'Player',
    player_score: 'Points',
    goals: 'Goals',
    assists: 'Assists',
    shots: 'Shots',
  }

  const LOGO_OPTIONS = [
    { value: 'rocket', label: 'Rocket', src: './assets/default-logo.webp' },
    { value: 'rocket2', label: 'Rocket 2', src: './assets/rpc-logo.webp' },
  ]

  const LOGO_SRC_BY_VALUE = Object.fromEntries(LOGO_OPTIONS.map((option) => [option.value, option.src]))
  const PLATFORM_IMAGE_SRC = {
    epic: './assets/epic.png',
    steam: './assets/steam.png',
  }

  const DEFAULT_CONFIG = {
    arena_name: true,
    current_score: true,
    timer: true,
    game_mode: true,
    match_status: true,
    player_name: true,
    player_score: true,
    goals: true,
    assists: true,
    shots: true,
    large_image: 'rocket',
  }

  const mockState = {
    requested: false,
    connected: false,
    listening: false,
    connect_attempts: 0,
    max_connect_tries: 5,
    in_match: false,
    live_match_view: {
      arena: 'Rocket League',
      mode: 'Awaiting live match data',
      time: '0:00',
      team_score: 0,
      opponent_score: 0,
      player_score: 0,
      player_goals: 0,
      player_assists: 0,
      player_shots: 0,
      status: 'Waiting',
      elapsed_seconds: 0,
    },
    presence_config: { ...DEFAULT_CONFIG },
    discord: { connected: false, client_id: null, last_error: null, reconnecting: false },
    log_level: 'INFO',
    debug_logs: ['[mock] window.pywebview not detected; using mock API'],
    last_update_state: null,
  }

  const mockPresets = new Map()
  const mockStatsApi = {
    found: false,
    enabled: false,
    path: null,
    packet_send_rate: null,
    port: null,
    warning: STATS_API_WARNING,
  }

  let state = {}
  let config = { ...DEFAULT_CONFIG }
  let presets = []
  let statsApi = null
  let activePreset = ''
  let syncStatus = 'synced'
  let busyTracker = false
  let busyDiscord = false
  let busyStatsApi = false
  let runningDebug = false
  let debounceTimer = null
  let pollTimer = null

  const el = {
    appName: document.getElementById('app-name'),
    appVersion: document.getElementById('app-version'),
    trackerStatus: document.getElementById('tracker-status'),
    trackerToggle: document.getElementById('tracker-toggle'),
    statsApiDot: document.getElementById('_stats-api-dot'),
    statsApiStatus: document.getElementById('stats-api-status'),
    statsApiToggle: document.getElementById('stats-api-toggle'),
    statsApiWarning: document.getElementById('stats-api-warning'),
    discordStatus: document.getElementById('discord-status'),
    discordToggle: document.getElementById('discord-toggle'),
    discordDebug: document.getElementById('discord-debug'),
    rpcTitle: document.getElementById('rpc-title'),
    rpcLargeImage: document.getElementById('rpc-large-image'),
    rpcSmallImage: document.getElementById('rpc-small-image'),
    rpcState: document.getElementById('rpc-state'),
    rpcDetails: document.getElementById('rpc-details'),
    rpcTime: document.getElementById('rpc-time'),
    matchArena: document.getElementById('match-arena'),
    previewArena: document.getElementById('preview-arena'),
    matchMode: document.getElementById('match-mode'),
    previewMode: document.getElementById('preview-mode'),
    scoreOrange: document.getElementById('score-orange'),
    scoreBlue: document.getElementById('score-blue'),
    matchTimer: document.getElementById('match-timer'),
    matchBadge: document.getElementById('match-badge'),
    previewBadge: document.getElementById('preview-badge'),
    features: document.getElementById('features'),
    syncStatus: document.getElementById('sync-status'),
    presetName: document.getElementById('preset-name'),
    presetSave: document.getElementById('preset-save'),
    presetOverwrite: document.getElementById('preset-overwrite'),
    presetSelect: document.getElementById('preset-select'),
    presetLoad: document.getElementById('preset-load'),
    presetDelete: document.getElementById('preset-delete'),
    presetStatus: document.getElementById('preset-status'),
    liveView: document.getElementById('live-view'),
    rawUpdate: document.getElementById('raw-update'),
    statsStatus: document.getElementById('stats-status'),
    debugLogs: document.getElementById('debug-logs'),
    logLevelSelect: document.getElementById('log-level-select'),
    logLevelStatus: document.getElementById('log-level-status'),
  }

  function hasBridge() {
    return !!(window.pywebview && window.pywebview.api)
  }

  function wait(ms = DEFAULT_WAIT_MS) {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  async function apiCall(method, ...args) {
    if (hasBridge()) {
      return window.pywebview.api[method](...args)
    }

    switch (method) {
      case 'get_app_info':
        return { name: 'Rocket League RPC', version: '0.0.2', dev_mode: true }
      case 'get_live_state':
        return JSON.parse(JSON.stringify(mockState))
      case 'connect_tracker':
        await wait()
        mockState.requested = true
        mockState.connected = true
        mockState.listening = true
        return JSON.parse(JSON.stringify(mockState))
      case 'disconnect_tracker':
        await wait()
        mockState.requested = false
        mockState.connected = false
        mockState.listening = false
        mockState.in_match = false
        return JSON.parse(JSON.stringify(mockState))
      case 'connect_discord_rpc':
        await wait()
        mockState.discord.connected = true
        mockState.discord.last_error = null
        return JSON.parse(JSON.stringify(mockState))
      case 'disconnect_discord_rpc':
        await wait()
        mockState.discord.connected = false
        return JSON.parse(JSON.stringify(mockState))
      case 'debug_discord_ipc':
        await wait(250)
        mockState.discord.connected = true
        mockState.discord.last_error = null
        mockState.debug_logs = [...(mockState.debug_logs || []), '[mock] IPC debug completed'].slice(-MAX_DEBUG_LOGS)
        return JSON.parse(JSON.stringify(mockState))
      case 'get_stats_api_status':
        return JSON.parse(JSON.stringify(mockStatsApi))
      case 'set_stats_api_enabled':
        await wait()
        if (!mockStatsApi.found) return JSON.parse(JSON.stringify(mockStatsApi))
        mockStatsApi.enabled = !!args[0]
        mockStatsApi.packet_send_rate = mockStatsApi.enabled ? 1 : 0
        mockStatsApi.port = 49123
        return JSON.parse(JSON.stringify(mockStatsApi))
      case 'get_log_level':
        return mockState.log_level || 'INFO'
      case 'set_log_level':
        await wait()
        mockState.log_level = String(args[0] || 'INFO').toUpperCase()
        mockState.debug_logs = [
          ...(mockState.debug_logs || []),
          `[mock] log level changed to ${mockState.log_level}`,
        ].slice(-MAX_DEBUG_LOGS)
        return JSON.parse(JSON.stringify(mockState))
      case 'get_presence_config':
        return { ...(mockState.presence_config || DEFAULT_CONFIG) }
      case 'set_presence_config':
        mockState.presence_config = { ...args[0] }
        return JSON.parse(JSON.stringify(mockState))
      case 'list_presence_presets':
        return [...mockPresets.keys()]
      case 'save_presence_preset': {
        const [name, cfg, overwrite] = args
        const clean = String(name || '').trim()
        if (!clean) throw new Error('Preset name is required')
        if (!overwrite && mockPresets.has(clean)) throw new Error('Preset already exists')
        mockPresets.set(clean, { ...cfg })
        return { name: clean, config: { ...cfg } }
      }
      case 'load_presence_preset': {
        const preset = mockPresets.get(args[0])
        if (!preset) throw new Error('Preset not found')
        mockState.presence_config = { ...preset }
        return JSON.parse(JSON.stringify(mockState))
      }
      case 'delete_presence_preset':
        mockPresets.delete(args[0])
        return { deleted: args[0] }
      case 'log_message':
        return { status: 'ok' }
      default:
        throw new Error(`Unsupported mock call: ${method}`)
    }
  }

  function trackerText(currentState) {
    const connected = !!(currentState.connected && currentState.listening)
    const requested = !!currentState.requested
    if (connected) return 'Tracker Online'
    if (requested) {
      return `Connecting... (${currentState.connect_attempts || 0}/${currentState.max_connect_tries || 5})`
    }
    return 'Tracker Offline'
  }

  function discordText(currentState) {
    const discord = currentState.discord || {}
    if (discord.connected) return 'Discord Online'
    if (discord.last_error) return 'Discord Error'
    return 'Discord Offline'
  }

  function statsApiText(currentStatsApi) {
    if (!currentStatsApi) return 'Unknown'
    if (!currentStatsApi.found) return 'Config not found'
    return currentStatsApi.enabled ? 'Enabled' : 'Disabled'
  }

  function fallbackPresence(currentState) {
    const live = currentState.live_match_view || {}
    return {
      details: 'Rocket League',
      state: currentState.in_match ? (live.arena || 'In Match') : 'Waiting',
      large_image: config.large_image || 'rocket',
      small_image: live.player_platform || null,
      small_text: null,
      start_time: null,
      end_time: null,
    }
  }

  function assetSrcForLargeImage(value) {
    return LOGO_SRC_BY_VALUE[value || 'rocket'] || LOGO_SRC_BY_VALUE.rocket
  }

  function assetSrcForSmallImage(value) {
    const key = String(value || '').toLowerCase()
    return PLATFORM_IMAGE_SRC[key] || PLATFORM_IMAGE_SRC.steam
  }

  function previewDetails(currentState) {
    const inMatch = !!currentState.in_match
    const live = currentState.live_match_view || {}
    if (!inMatch) return 'Ready for the next match.'
    const bits = []
    if (live.mode) bits.push(live.mode)
    if (typeof live.team_score === 'number' && typeof live.opponent_score === 'number') {
      bits.push(`${live.team_score}-${live.opponent_score}`)
    }
    if (live.status) bits.push(live.status)
    return bits.length ? bits.join(' | ') : 'Playing'
  }

  function renderFeatures() {
    el.features.innerHTML = ''

    const buildGroup = (title, keys, accentColor) => {
      const wrapper = document.createElement('div')
      wrapper.className = 'feature-group'
      wrapper.style.borderTop = `2px solid ${accentColor}`

      const legend = document.createElement('div')
      legend.textContent = title
      legend.className = 'feature-group-title'
      legend.style.color = accentColor
      wrapper.appendChild(legend)

      const list = document.createElement('div')
      list.className = 'feature-list'

      keys.forEach((key) => {
        const label = document.createElement('label')
        label.className = config[key] ? 'feature-option is-active' : 'feature-option'

        const checkbox = document.createElement('input')
        checkbox.type = 'checkbox'
        checkbox.checked = !!config[key]
        checkbox.addEventListener('change', () => onToggleFeature(key))

        label.appendChild(checkbox)
        label.append(FEATURE_LABELS[key])
        list.appendChild(label)
      })

      wrapper.appendChild(list)
      return wrapper
    }

    const buildLogoGroup = () => {
      const wrapper = document.createElement('div')
      wrapper.className = 'logo-group'
      wrapper.style.borderTop = '2px solid #00E5FF'

      const legend = document.createElement('div')
      legend.textContent = 'RPC Logo'
      legend.className = 'feature-group-title'
      legend.style.color = '#00E5FF'
      wrapper.appendChild(legend)

      const list = document.createElement('div')
      list.className = 'logo-options'

      LOGO_OPTIONS.forEach((option) => {
        const selected = (config.large_image || 'rocket') === option.value
        const label = document.createElement('label')
        label.className = selected ? 'logo-option is-active' : 'logo-option'

        const radio = document.createElement('input')
        radio.type = 'radio'
        radio.name = 'large-image'
        radio.value = option.value
        radio.checked = selected
        radio.addEventListener('change', () => onSelectLargeImage(option.value))

        const img = document.createElement('img')
        img.src = option.src
        img.alt = `${option.label} RPC logo`

        const text = document.createElement('span')
        text.textContent = option.label

        label.appendChild(radio)
        label.appendChild(img)
        label.appendChild(text)
        list.appendChild(label)
      })

      wrapper.appendChild(list)
      return wrapper
    }

    el.features.appendChild(buildGroup('Match Info', FEATURE_GROUPS.match, '#1B8FFF'))
    el.features.appendChild(buildGroup('Player Stats', FEATURE_GROUPS.player, '#FF6B00'))
    el.features.appendChild(buildLogoGroup())
  }

  function renderPresets() {
    el.presetSelect.innerHTML = ''
    const emptyOpt = document.createElement('option')
    emptyOpt.value = ''
    emptyOpt.textContent = 'No presets'
    el.presetSelect.appendChild(emptyOpt)

    presets.forEach((name) => {
      const option = document.createElement('option')
      option.value = name
      option.textContent = name
      el.presetSelect.appendChild(option)
    })

    el.presetSelect.value = activePreset
  }

  function render() {
    const currentState = state || {}
    const discord = currentState.discord || {}
    const live = currentState.live_match_view || {}

    const trackerStatusText = trackerText(currentState)
    const discordStatusText = discordText(currentState)
    const statsApiStatusText = statsApiText(statsApi)

    el.trackerStatus.textContent = trackerStatusText
    el.discordStatus.textContent = discordStatusText
    el.statsApiStatus.textContent = statsApiStatusText

    const connectedTracker = !!(currentState.connected && currentState.listening)
    const requestedTracker = !!currentState.requested
    el.trackerToggle.textContent = connectedTracker ? 'Disconnect Tracker' : requestedTracker ? 'Connecting...' : 'Connect Tracker'
    el.trackerToggle.disabled = busyTracker || (requestedTracker && !connectedTracker)
    el.trackerToggle.className = connectedTracker ? 'button button-orange' : 'button button-primary'

    el.statsApiToggle.textContent = busyStatsApi
      ? 'Applying...'
      : statsApi && statsApi.found
        ? statsApi.enabled ? 'Disable StatsAPI' : 'Enable StatsAPI'
        : 'StatsAPI Help'
    el.statsApiToggle.disabled = busyStatsApi || !statsApi || !statsApi.found
    el.statsApiToggle.className = statsApi && statsApi.found && statsApi.enabled ? 'button button-orange' : 'button button-primary'
    el.statsApiDot.className = (
      !statsApi ? 'dot-wait' :
      !statsApi.found ? 'dot-wait' :
      statsApi.enabled ? 'dot-on' : 'dot-off'
    )
    if (statsApi && !statsApi.found && statsApi.warning) {
      el.statsApiWarning.textContent = statsApi.warning
      el.statsApiWarning.classList.remove('hidden')
    } else {
      el.statsApiWarning.textContent = ''
      el.statsApiWarning.classList.add('hidden')
    }

    el.discordToggle.textContent = discord.connected ? 'Disconnect RPC' : 'Connect Discord RPC'
    el.discordToggle.disabled = busyDiscord || runningDebug
    el.discordToggle.className = discord.connected ? 'button button-orange' : 'button button-primary'
    el.discordDebug.textContent = runningDebug ? 'Debugging...' : 'Debug IPC'
    el.discordDebug.disabled = runningDebug

    const presence = discord.last_presence || fallbackPresence(currentState)
    el.rpcTitle.textContent = 'Rocket League'
    el.rpcState.textContent = presence.details || 'Rocket League'
    el.rpcDetails.textContent = presence.state || 'Waiting'
    el.rpcTime.textContent = presence.start_time || presence.end_time ? 'Timer active' : 'No timer'
    el.rpcLargeImage.src = assetSrcForLargeImage(presence.large_image)
    el.rpcSmallImage.src = assetSrcForSmallImage(presence.small_image)

    el.matchArena.textContent = live.arena || 'Rocket League'
    el.matchMode.textContent = live.mode || 'Awaiting live match data'
    el.scoreOrange.textContent = String(live.team_score || 0)
    el.scoreBlue.textContent = String(live.opponent_score || 0)
    el.matchTimer.textContent = live.time || '0:00'
    el.matchBadge.textContent = live.status || 'Waiting'
    el.previewArena.textContent = presence.details || 'Rocket League'
    el.previewMode.textContent = presence.state || 'Waiting'
    el.previewBadge.textContent = presence.small_text || presence.small_image || 'No small asset'

    el.syncStatus.textContent =
      syncStatus === 'pending' ? 'Pending...' :
      syncStatus === 'applying' ? 'Applying...' :
      syncStatus === 'error' ? 'Error syncing features' : 'Synced'

    const logLevel = currentState.log_level || 'INFO'
    el.logLevelSelect.value = logLevel
    el.logLevelStatus.textContent = `Current level: ${logLevel}`

    el.liveView.textContent = JSON.stringify(currentState, null, 2)
    el.rawUpdate.textContent = JSON.stringify(currentState.last_update_state || {}, null, 2)
    el.statsStatus.textContent = JSON.stringify({
      tracker: trackerStatusText,
      discord: discordStatusText,
      in_match: !!currentState.in_match,
      connect_attempts: currentState.connect_attempts || 0,
      max_connect_tries: currentState.max_connect_tries || 5,
    }, null, 2)
    el.debugLogs.textContent = (currentState.debug_logs || []).join('\n')

    renderFeatures()
    renderPresets()
  }

  async function refreshAll() {
    const [nextState, nextConfig, nextPresets, nextStatsApi] = await Promise.all([
      apiCall('get_live_state'),
      apiCall('get_presence_config'),
      apiCall('list_presence_presets'),
      apiCall('get_stats_api_status'),
    ])

    state = nextState || {}
    config = nextConfig || { ...DEFAULT_CONFIG }
    presets = nextPresets || []
    statsApi = nextStatsApi || null
    el.presetStatus.textContent = presets.length ? `${presets.length} preset(s) available` : 'No presets saved'
    render()
  }

  function scheduleConfigApply(next) {
    config = next
    syncStatus = 'pending'
    render()

    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }

    debounceTimer = setTimeout(async () => {
      try {
        syncStatus = 'applying'
        render()
        const updated = await apiCall('set_presence_config', next)
        state = updated || {}
        syncStatus = 'synced'
      } catch (err) {
        syncStatus = 'error'
        console.warn('set_presence_config failed:', err)
      }
      render()
    }, DEBOUNCE_MS)
  }

  function onToggleFeature(key) {
    scheduleConfigApply({ ...config, [key]: !config[key] })
  }

  function onSelectLargeImage(value) {
    scheduleConfigApply({ ...config, large_image: value })
  }

  async function toggleTracker() {
    const prevState = state
    try {
      busyTracker = true
      render()
      const connected = !!(state.connected && state.listening)
      const updated = connected
        ? await apiCall('disconnect_tracker')
        : await apiCall('connect_tracker')
      state = updated || prevState
    } catch (err) {
      console.warn('toggleTracker failed:', err)
      state = prevState
    } finally {
      busyTracker = false
      render()
    }
  }

  async function toggleStatsApi() {
    if (!statsApi || !statsApi.found) return
    const previous = statsApi
    try {
      busyStatsApi = true
      render()
      statsApi = await apiCall('set_stats_api_enabled', !statsApi.enabled)
    } catch (err) {
      console.warn('toggleStatsApi failed:', err)
      statsApi = previous
    } finally {
      busyStatsApi = false
      render()
    }
  }

  async function toggleDiscord() {
    const prevState = state
    try {
      busyDiscord = true
      render()
      const connected = !!(state.discord && state.discord.connected)
      const updated = connected
        ? await apiCall('disconnect_discord_rpc')
        : await apiCall('connect_discord_rpc')
      state = updated || prevState
    } catch (err) {
      console.warn('toggleDiscord failed:', err)
      state = prevState
    } finally {
      busyDiscord = false
      render()
    }
  }

  async function debugDiscord() {
    const prevState = state
    try {
      runningDebug = true
      render()
      const updated = await apiCall('debug_discord_ipc')
      state = updated || prevState
    } catch (err) {
      console.warn('debugDiscord failed:', err)
      state = prevState
    } finally {
      runningDebug = false
      render()
    }
  }

  async function savePreset(overwrite) {
    const name = (el.presetName.value || '').trim()
    if (!name) {
      el.presetStatus.textContent = 'Preset name is required'
      return
    }

    try {
      await apiCall('save_presence_preset', name, config, overwrite)
      presets = await apiCall('list_presence_presets')
      activePreset = name
      el.presetStatus.textContent = overwrite ? 'Preset overwritten' : 'Preset saved'
    } catch (err) {
      console.warn('savePreset failed:', err)
      el.presetStatus.textContent = err instanceof Error ? err.message : 'Could not save preset'
    }
    render()
  }

  async function loadPreset() {
    const selected = el.presetSelect.value
    if (!selected) return

    try {
      state = await apiCall('load_presence_preset', selected)
      config = await apiCall('get_presence_config')
      syncStatus = 'synced'
      activePreset = selected
      el.presetStatus.textContent = 'Preset loaded'
    } catch (err) {
      console.warn('loadPreset failed:', err)
      el.presetStatus.textContent = 'Could not load preset'
    }
    render()
  }

  async function deletePreset() {
    const selected = el.presetSelect.value
    if (!selected) return

    try {
      await apiCall('delete_presence_preset', selected)
      presets = await apiCall('list_presence_presets')
      activePreset = ''
      el.presetStatus.textContent = 'Preset deleted'
    } catch (err) {
      console.warn('deletePreset failed:', err)
      el.presetStatus.textContent = 'Could not delete preset'
    }
    render()
  }

  async function setLogLevel() {
    const nextLevel = el.logLevelSelect.value
    el.logLevelSelect.disabled = true
    el.logLevelStatus.textContent = `Applying ${nextLevel}...`
    try {
      state = await apiCall('set_log_level', nextLevel)
    } catch (err) {
      console.warn('setLogLevel failed:', err)
      el.logLevelStatus.textContent = 'Could not update log level'
    } finally {
      el.logLevelSelect.disabled = false
    }
    render()
  }

  async function bootstrap() {
    const info = await apiCall('get_app_info')
    el.appName.textContent = info.name
    el.appVersion.textContent = `v${info.version}`
    await apiCall('log_message', 'Vanilla frontend ready')
    await refreshAll()
  }

  function wireEvents() {
    el.trackerToggle.addEventListener('click', () => { void toggleTracker() })
    el.statsApiToggle.addEventListener('click', () => { void toggleStatsApi() })
    el.discordToggle.addEventListener('click', () => { void toggleDiscord() })
    el.discordDebug.addEventListener('click', () => { void debugDiscord() })

    el.presetSelect.addEventListener('change', () => { activePreset = el.presetSelect.value })
    el.presetSave.addEventListener('click', () => { void savePreset(false) })
    el.presetOverwrite.addEventListener('click', () => { void savePreset(true) })
    el.presetLoad.addEventListener('click', () => { void loadPreset() })
    el.presetDelete.addEventListener('click', () => { void deletePreset() })
    el.logLevelSelect.addEventListener('change', () => { void setLogLevel() })
  }

  async function start() {
    wireEvents()
    await bootstrap()

    window.addEventListener('pywebviewready', () => { void bootstrap() }, { once: true })

    function shouldPoll() {
      return document.visibilityState === 'visible'
    }

    async function pollOnce() {
      if (!shouldPoll()) return
      try {
        state = await apiCall('get_live_state')
        render()
      } catch (_err) {
        // keep polling even on intermittent errors
      }
    }

    function startPolling() {
      if (pollTimer !== null || !shouldPoll()) return
      pollTimer = setInterval(() => { void pollOnce() }, POLL_INTERVAL_MS)
    }

    function stopPolling() {
      if (pollTimer === null) return
      clearInterval(pollTimer)
      pollTimer = null
    }

    function refreshPolling() {
      if (shouldPoll()) {
        startPolling()
        void pollOnce()
      } else {
        stopPolling()
      }
    }

    document.addEventListener('visibilitychange', refreshPolling)
    window.addEventListener('focus', refreshPolling)
    window.addEventListener('blur', refreshPolling)
    window.addEventListener('beforeunload', () => {
      stopPolling()
      document.removeEventListener('visibilitychange', refreshPolling)
      window.removeEventListener('focus', refreshPolling)
      window.removeEventListener('blur', refreshPolling)
    }, { once: true })

    refreshPolling()
  }

  void start()
})()

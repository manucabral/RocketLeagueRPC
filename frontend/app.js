(() => {
  const POLL_INTERVAL_MS = 1000
  const DEBOUNCE_MS = 220
  const MAX_DEBUG_LOGS = 250
  const DEFAULT_WAIT_MS = 120

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
    debug_logs: ['[mock] window.pywebview not detected; using mock API'],
    last_update_state: null,
  }

  const mockPresets = new Map()

  let state = {}
  let config = { ...DEFAULT_CONFIG }
  let presets = []
  let activePreset = ''
  let syncStatus = 'synced'
  let busyTracker = false
  let busyDiscord = false
  let runningDebug = false
  let debounceTimer = null
  let pollTimer = null

  const el = {
    appName: document.getElementById('app-name'),
    appVersion: document.getElementById('app-version'),
    trackerStatus: document.getElementById('tracker-status'),
    trackerToggle: document.getElementById('tracker-toggle'),
    discordStatus: document.getElementById('discord-status'),
    discordToggle: document.getElementById('discord-toggle'),
    discordDebug: document.getElementById('discord-debug'),
    rpcTitle: document.getElementById('rpc-title'),
    rpcState: document.getElementById('rpc-state'),
    rpcDetails: document.getElementById('rpc-details'),
    rpcTime: document.getElementById('rpc-time'),
    matchArena: document.getElementById('match-arena'),
    matchMode: document.getElementById('match-mode'),
    scoreOrange: document.getElementById('score-orange'),
    scoreBlue: document.getElementById('score-blue'),
    matchTimer: document.getElementById('match-timer'),
    matchBadge: document.getElementById('match-badge'),
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
        return { name: 'Rocket League RPC', version: '0.0.0', dev_mode: true }
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
      wrapper.style.cssText = `background:#0d0d1a; border:1px solid #1a1a2e; border-top:2px solid ${accentColor}; padding:12px;`

      const legend = document.createElement('div')
      legend.textContent = title
      legend.style.cssText = `font-family:'Orbitron',sans-serif; font-size:0.65rem; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:${accentColor}; margin-bottom:10px;`
      wrapper.appendChild(legend)

      const list = document.createElement('div')
      list.style.cssText = 'display:flex; flex-direction:column; gap:8px;'

      keys.forEach((key) => {
        const label = document.createElement('label')
        label.style.cssText = 'display:flex; align-items:center; gap:8px; cursor:pointer; color:#94a3b8; font-size:0.85rem; font-weight:600; letter-spacing:0.04em; transition:color 0.15s;'
        label.onmouseenter = () => { label.style.color = '#e2e8f0' }
        label.onmouseleave = () => { label.style.color = config[key] ? '#e2e8f0' : '#94a3b8' }

        const checkbox = document.createElement('input')
        checkbox.type = 'checkbox'
        checkbox.checked = !!config[key]
        checkbox.style.cssText = `accent-color:${accentColor}; width:14px; height:14px; cursor:pointer; flex-shrink:0;`
        checkbox.addEventListener('change', () => onToggleFeature(key))

        if (config[key]) label.style.color = '#e2e8f0'

        label.appendChild(checkbox)
        label.append(FEATURE_LABELS[key])
        list.appendChild(label)
      })

      wrapper.appendChild(list)
      return wrapper
    }

    el.features.appendChild(buildGroup('Match Info', FEATURE_GROUPS.match, '#1B8FFF'))
    el.features.appendChild(buildGroup('Player Stats', FEATURE_GROUPS.player, '#FF6B00'))
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

    el.trackerStatus.textContent = trackerStatusText
    el.discordStatus.textContent = discordStatusText

    const connectedTracker = !!(currentState.connected && currentState.listening)
    const requestedTracker = !!currentState.requested
    el.trackerToggle.textContent = connectedTracker ? 'Disconnect Tracker' : requestedTracker ? 'Connecting...' : 'Connect Tracker'
    el.trackerToggle.disabled = busyTracker || (requestedTracker && !connectedTracker)
    el.trackerToggle.className = (connectedTracker ? 'btn-orange' : 'btn-blue') + ' px-4 py-2 text-sm cursor-pointer'

    el.discordToggle.textContent = discord.connected ? 'Disconnect RPC' : 'Connect Discord RPC'
    el.discordToggle.disabled = busyDiscord || runningDebug
    el.discordToggle.className = (discord.connected ? 'btn-orange' : 'btn-blue') + ' px-4 py-2 text-sm cursor-pointer'
    el.discordDebug.textContent = runningDebug ? 'Debugging...' : 'Debug IPC'
    el.discordDebug.disabled = runningDebug

    el.rpcTitle.textContent = 'Rocket League'
    el.rpcState.textContent = currentState.in_match ? (live.arena || 'In Match') : 'Waiting'
    el.rpcDetails.textContent = previewDetails(currentState)
    el.rpcTime.textContent = currentState.in_match ? `${live.elapsed_seconds || 0}s elapsed` : '00:00 elapsed'

    el.matchArena.textContent = live.arena || 'Rocket League'
    el.matchMode.textContent = live.mode || 'Awaiting live match data'
    el.scoreOrange.textContent = String(live.team_score || 0)
    el.scoreBlue.textContent = String(live.opponent_score || 0)
    el.matchTimer.textContent = live.time || '0:00'
    el.matchBadge.textContent = live.status || 'Waiting'

    el.syncStatus.textContent =
      syncStatus === 'pending' ? 'Pending...' :
      syncStatus === 'applying' ? 'Applying...' :
      syncStatus === 'error' ? 'Error syncing features' : 'Synced'

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
    const [nextState, nextConfig, nextPresets] = await Promise.all([
      apiCall('get_live_state'),
      apiCall('get_presence_config'),
      apiCall('list_presence_presets'),
    ])

    state = nextState || {}
    config = nextConfig || { ...DEFAULT_CONFIG }
    presets = nextPresets || []
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

  async function bootstrap() {
    const info = await apiCall('get_app_info')
    el.appName.textContent = info.name
    el.appVersion.textContent = `v${info.version}`
    await apiCall('log_message', 'Vanilla frontend ready')
    await refreshAll()
  }

  function wireEvents() {
    el.trackerToggle.addEventListener('click', () => { void toggleTracker() })
    el.discordToggle.addEventListener('click', () => { void toggleDiscord() })
    el.discordDebug.addEventListener('click', () => { void debugDiscord() })

    el.presetSelect.addEventListener('change', () => { activePreset = el.presetSelect.value })
    el.presetSave.addEventListener('click', () => { void savePreset(false) })
    el.presetOverwrite.addEventListener('click', () => { void savePreset(true) })
    el.presetLoad.addEventListener('click', () => { void loadPreset() })
    el.presetDelete.addEventListener('click', () => { void deletePreset() })
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

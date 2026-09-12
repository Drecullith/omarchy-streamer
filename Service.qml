import QtQuick
import Quickshell
import Quickshell.Io

Item {
  id: root

  property var shell: null
  readonly property string helperPath: Qt.resolvedUrl("bin/streamerctl").toString().replace(/^file:\/\//, "")

  property bool active: false
  property bool privacy: false
  property bool obsInstalled: false
  property bool obsRunning: false
  property bool pipewireReady: false
  property bool wpctlInstalled: false
  property bool pythonReady: false

  property bool obsWebSocketReady: false
  property var streaming: null
  property var recording: null
  property var replayBuffer: null
  property string currentScene: ""
  property string obsWebSocketError: ""

  property bool audioReady: false
  property var audioSources: []
  property string selectedSourceName: ""
  property var selectedSourceId: null
  property bool selectedSourcePresent: false
  property var micMuted: null
  property var micVolumePercent: null
  property string audioError: ""

  property bool safetyReady: false
  property string workspaceName: ""
  property bool streamSafeActive: false
  property bool sensitiveActive: false
  property string sensitiveRule: ""
  property string activeWindowClass: ""
  property string safetyError: ""

  property bool collaborationReady: false
  property bool collaborationActive: false
  property string collaborationProvider: ""
  property string collaborationProviderLabel: ""
  property bool collaborationClipboardReady: false
  property bool collaborationBrowserReady: false
  property bool collaborationInviteReady: false
  property bool collaborationProgramUrlReady: false
  property bool collaborationManagedSlotsReady: false
  property int collaborationSlotCount: 0
  property string collaborationObsSceneName: ""
  property string collaborationError: ""

  property bool onboardingReady: false
  property bool onboardingComplete: false
  property int onboardingTourVersion: 0
  property string onboardingError: ""
  property bool onboardingSummoned: false

  property string dndState: "unknown"
  property bool dndManaged: false
  property string lastAction: ""
  property string lastError: ""

  function snapshot() {
    return {
      version: 7,
      active: root.active,
      privacy: root.privacy,
      obsInstalled: root.obsInstalled,
      obsRunning: root.obsRunning,
      pipewireReady: root.pipewireReady,
      wpctlInstalled: root.wpctlInstalled,
      pythonReady: root.pythonReady,
      obsWebSocketReady: root.obsWebSocketReady,
      streaming: root.streaming,
      recording: root.recording,
      replayBuffer: root.replayBuffer,
      currentScene: root.currentScene,
      obsWebSocketError: root.obsWebSocketError,
      audioReady: root.audioReady,
      audioSources: root.audioSources,
      selectedSourceName: root.selectedSourceName,
      selectedSourceId: root.selectedSourceId,
      selectedSourcePresent: root.selectedSourcePresent,
      micMuted: root.micMuted,
      micVolumePercent: root.micVolumePercent,
      audioError: root.audioError,
      safetyReady: root.safetyReady,
      workspaceName: root.workspaceName,
      streamSafeActive: root.streamSafeActive,
      sensitiveActive: root.sensitiveActive,
      sensitiveRule: root.sensitiveRule,
      activeWindowClass: root.activeWindowClass,
      safetyError: root.safetyError,
      collaborationReady: root.collaborationReady,
      collaborationActive: root.collaborationActive,
      collaborationProvider: root.collaborationProvider,
      collaborationProviderLabel: root.collaborationProviderLabel,
      collaborationClipboardReady: root.collaborationClipboardReady,
      collaborationBrowserReady: root.collaborationBrowserReady,
      collaborationInviteReady: root.collaborationInviteReady,
      collaborationProgramUrlReady: root.collaborationProgramUrlReady,
      collaborationManagedSlotsReady: root.collaborationManagedSlotsReady,
      collaborationSlotCount: root.collaborationSlotCount,
      collaborationObsSceneName: root.collaborationObsSceneName,
      collaborationError: root.collaborationError,
      onboardingReady: root.onboardingReady,
      onboardingComplete: root.onboardingComplete,
      onboardingTourVersion: root.onboardingTourVersion,
      onboardingError: root.onboardingError,
      dndState: root.dndState,
      dndManaged: root.dndManaged,
      lastAction: root.lastAction,
      lastError: root.lastError
    }
  }

  function applyStatus(raw) {
    try {
      var state = JSON.parse(String(raw || "{}"))
      var obs = state.obsWebSocket || {}
      var audio = state.audio || {}
      var safety = state.safety || {}
      var collab = state.collaboration || {}
      var onboarding = state.onboarding || {}

      root.active = !!state.active
      root.privacy = !!state.privacy
      root.obsInstalled = !!state.obsInstalled
      root.obsRunning = !!state.obsRunning
      root.pipewireReady = !!state.pipewireReady
      root.wpctlInstalled = !!state.wpctlInstalled
      root.pythonReady = !!state.pythonReady

      root.obsWebSocketReady = !!obs.connected
      root.streaming = obs.streaming === null || obs.streaming === undefined ? null : !!obs.streaming
      root.recording = obs.recording === null || obs.recording === undefined ? null : !!obs.recording
      root.replayBuffer = obs.replayBuffer === null || obs.replayBuffer === undefined ? null : !!obs.replayBuffer
      root.currentScene = String(obs.currentScene || "")
      root.obsWebSocketError = String(obs.error || "")

      root.audioReady = !!audio.ready
      root.audioSources = Array.isArray(audio.sources) ? audio.sources : []
      root.selectedSourceName = String(audio.selectedSourceName || "")
      root.selectedSourceId = audio.selectedSourceId === undefined ? null : audio.selectedSourceId
      root.selectedSourcePresent = !!audio.selectedPresent
      root.micMuted = audio.muted === null || audio.muted === undefined ? null : !!audio.muted
      root.micVolumePercent = audio.volumePercent === null || audio.volumePercent === undefined ? null : Number(audio.volumePercent)
      root.audioError = String(audio.error || "")

      root.safetyReady = !!safety.ready
      root.workspaceName = String(safety.workspaceName || "")
      root.streamSafeActive = !!safety.streamSafeActive
      root.sensitiveActive = !!safety.sensitiveActive
      root.sensitiveRule = String(safety.sensitiveRule || "")
      root.activeWindowClass = String(safety.activeWindowClass || "")
      root.safetyError = String(safety.error || "")

      root.collaborationReady = !!collab.ready
      root.collaborationActive = !!collab.active
      root.collaborationProvider = String(collab.provider || "")
      root.collaborationProviderLabel = String(collab.providerLabel || "")
      root.collaborationClipboardReady = !!collab.clipboardReady
      root.collaborationBrowserReady = !!collab.browserReady
      root.collaborationInviteReady = !!collab.inviteReady
      root.collaborationProgramUrlReady = !!collab.programUrlReady
      root.collaborationManagedSlotsReady = !!collab.managedSlotsReady
      root.collaborationSlotCount = Number(collab.slotCount || 0)
      root.collaborationObsSceneName = String(collab.obsSceneName || "")
      root.collaborationError = String(collab.error || "")

      root.onboardingReady = !!onboarding.ready
      root.onboardingComplete = !!onboarding.completed
      root.onboardingTourVersion = Number(onboarding.tourVersion || 0)
      root.onboardingError = String(onboarding.error || "")
      if (root.onboardingReady && !root.onboardingComplete && !root.onboardingSummoned && !onboardingTimer.running)
        onboardingTimer.start()

      root.dndState = String(state.dndState || "unknown")
      root.dndManaged = !!state.dndManaged
      root.lastError = ""
    } catch (e) {
      root.lastError = "status-parse-failed"
    }
  }

  function refreshStatus() {
    if (statusProc.running) return
    statusProc.running = true
  }

  function queueAction(name, arg) {
    var actionName = String(name || "")
    if (actionName === "") return "invalid-action"
    var argv = ["bash", root.helperPath, "action", actionName]
    if (arg !== undefined && arg !== null && String(arg) !== "") argv.push(String(arg))
    root.lastAction = actionName
    root.lastError = ""
    Quickshell.execDetached(argv)
    delayedRefresh.restart()
    return "queued"
  }

  function handleAction(name, arg) {
    switch (String(name || "")) {
      case "mode.enable":
      case "mode.disable":
      case "mode.toggle":
      case "privacy.enable":
      case "privacy.disable":
      case "obs.launch":
      case "health.refresh":
      case "stream.start":
      case "stream.stop":
      case "record.start":
      case "record.stop":
      case "replay.start":
      case "replay.stop":
      case "clip.save":
      case "scene.set":
      case "mic.select":
      case "mic.next":
      case "mic.mute":
      case "mic.unmute":
      case "mic.toggle":
      case "mic.volume":
      case "workspace.enter":
      case "workspace.exit":
      case "window.check":
      case "safety.refresh":
      case "emergency.end-live":
      case "emergency.stop-all":
      case "collab.create":
      case "collab.rotate":
      case "collab.reset":
      case "collab.open-director":
      case "collab.copy-invite":
      case "collab.copy-program":
      case "collab.slot-rotate":
      case "collab.copy-slot-invite":
      case "collab.copy-slot-source":
      case "collab.obs-add-program":
      case "collab.obs-add-slot":
      case "onboarding.open":
      case "onboarding.complete":
      case "onboarding.reset":
        return root.queueAction(name, arg)
      default:
        return "unknown-action"
    }
  }

  Process {
    id: statusProc
    command: ["bash", root.helperPath, "status"]
    running: false
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.applyStatus(text) }
  }

  Timer { id: delayedRefresh; interval: 500; repeat: false; onTriggered: root.refreshStatus() }
  Timer {
    id: onboardingTimer
    interval: 1500
    repeat: false
    onTriggered: {
      if (!root.onboardingComplete && !root.onboardingSummoned) {
        root.onboardingSummoned = true
        Quickshell.execDetached(["bash", root.helperPath, "action", "onboarding.open", "first-run"])
      }
    }
  }
  Timer { interval: 3000; repeat: true; running: true; triggeredOnStart: false; onTriggered: root.refreshStatus() }

  IpcHandler {
    target: "io.github.drecullith.streamer"
    function ping(): string { return "ok" }
    function status(): string { return JSON.stringify(root.snapshot()) }
    function refresh(): string { root.refreshStatus(); return "queued" }
    function action(name: string, arg: string): string { return root.handleAction(name, arg) }
    function enable(): string { return root.handleAction("mode.enable", "") }
    function disable(): string { return root.handleAction("mode.disable", "") }
    function toggle(): string { return root.handleAction("mode.toggle", "") }
  }

  Component.onCompleted: root.refreshStatus()
}

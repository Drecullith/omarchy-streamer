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
  property string dndState: "unknown"
  property bool dndManaged: false
  property string lastAction: ""
  property string lastError: ""
  property string statusBuffer: ""

  function snapshot() {
    return {
      version: 2,
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
      root.dndState = String(state.dndState || "unknown")
      root.dndManaged = !!state.dndManaged
      root.lastError = ""
    } catch (e) {
      root.lastError = "status-parse-failed"
    }
  }

  function refreshStatus() {
    if (statusProc.running) return
    root.statusBuffer = ""
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
      case "mic.mute":
      case "mic.unmute":
        return root.queueAction(name, arg)
      default:
        return "unknown-action"
    }
  }

  Process {
    id: statusProc
    command: ["bash", root.helperPath, "status"]
    running: false
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.applyStatus(text)
    }
  }

  Timer {
    id: delayedRefresh
    interval: 500
    repeat: false
    onTriggered: root.refreshStatus()
  }

  Timer {
    interval: 3000
    repeat: true
    running: true
    triggeredOnStart: false
    onTriggered: root.refreshStatus()
  }

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

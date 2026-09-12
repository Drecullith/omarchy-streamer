import QtQuick
import QtQuick.Controls as QQC
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "io.github.drecullith.streamer"

  readonly property string helperPath: Qt.resolvedUrl("bin/streamerctl").toString().replace(/^file:\/\//, "")

  property bool popupOpen: false
  property bool active: false
  property bool privacy: false
  property bool obsInstalled: false
  property bool obsRunning: false
  property bool obsWebSocketReady: false
  property bool pipewireReady: false
  property var streaming: null
  property var recording: null
  property var replayBuffer: null
  property string currentScene: ""
  property string obsWebSocketError: ""

  property bool audioReady: false
  property var audioSources: []
  property string selectedSourceName: ""
  property bool selectedSourcePresent: false
  property var micMuted: null
  property var micVolumePercent: null
  property string audioError: ""

  property bool safetyReady: false
  property string workspaceName: ""
  property bool streamSafeActive: false
  property bool sensitiveActive: false
  property string activeWindowClass: ""
  property string safetyError: ""

  property bool collaborationReady: false
  property bool collaborationActive: false
  property string collaborationProviderLabel: ""
  property bool collaborationClipboardReady: false
  property bool collaborationBrowserReady: false
  property bool collaborationInviteReady: false
  property bool collaborationProgramUrlReady: false
  property bool collaborationManagedSlotsReady: false
  property bool collaborationGuestControlReady: false
  property int collaborationSlotCount: 0
  property var collaborationGuests: []
  property string collaborationObsSceneName: ""
  property string collaborationError: ""
  property int selectedGuestSlot: 1

  property string dndState: "unknown"
  property string actionMessage: ""

  readonly property bool live: root.streaming === true
  readonly property bool rec: root.recording === true
  readonly property bool replaying: root.replayBuffer === true
  readonly property bool captureActive: root.live || root.rec
  readonly property bool privacyWarning: root.captureActive && !root.privacy
  readonly property bool micWarning: root.selectedSourceName !== "" && !root.selectedSourcePresent
  readonly property bool safetyWarning: root.captureActive && root.sensitiveActive
  readonly property string barLabel: root.live ? "LIVE" : (root.rec ? "REC" : (root.active ? "STREAM" : "Stream"))
  readonly property var selectedGuestState: root.guestStateFor(root.selectedGuestSlot)

  implicitWidth: statusRow.implicitWidth + Style.space(14)
  implicitHeight: barSize

  function guestStateFor(slotNumber) {
    for (var i = 0; i < root.collaborationGuests.length; i++) {
      var guest = root.collaborationGuests[i]
      if (Number(guest.slot || 0) === Number(slotNumber)) return guest
    }
    return { slot: Number(slotNumber), online: null, micEnabled: null, stale: true, error: "" }
  }

  function applyStatus(raw) {
    try {
      var state = JSON.parse(String(raw || "{}"))
      var obs = state.obsWebSocket || {}
      var audio = state.audio || {}
      var safety = state.safety || {}
      var collab = state.collaboration || {}

      root.active = !!state.active
      root.privacy = !!state.privacy
      root.obsInstalled = !!state.obsInstalled
      root.obsRunning = !!state.obsRunning
      root.obsWebSocketReady = !!obs.connected
      root.pipewireReady = !!state.pipewireReady
      root.streaming = obs.streaming === null || obs.streaming === undefined ? null : !!obs.streaming
      root.recording = obs.recording === null || obs.recording === undefined ? null : !!obs.recording
      root.replayBuffer = obs.replayBuffer === null || obs.replayBuffer === undefined ? null : !!obs.replayBuffer
      root.currentScene = String(obs.currentScene || "")
      root.obsWebSocketError = String(obs.error || "")

      root.audioReady = !!audio.ready
      root.audioSources = Array.isArray(audio.sources) ? audio.sources : []
      root.selectedSourceName = String(audio.selectedSourceName || "")
      root.selectedSourcePresent = !!audio.selectedPresent
      root.micMuted = audio.muted === null || audio.muted === undefined ? null : !!audio.muted
      root.micVolumePercent = audio.volumePercent === null || audio.volumePercent === undefined ? null : Number(audio.volumePercent)
      root.audioError = String(audio.error || "")

      root.safetyReady = !!safety.ready
      root.workspaceName = String(safety.workspaceName || "")
      root.streamSafeActive = !!safety.streamSafeActive
      root.sensitiveActive = !!safety.sensitiveActive
      root.activeWindowClass = String(safety.activeWindowClass || "")
      root.safetyError = String(safety.error || "")

      root.collaborationReady = !!collab.ready
      root.collaborationActive = !!collab.active
      root.collaborationProviderLabel = String(collab.providerLabel || "")
      root.collaborationClipboardReady = !!collab.clipboardReady
      root.collaborationBrowserReady = !!collab.browserReady
      root.collaborationInviteReady = !!collab.inviteReady
      root.collaborationProgramUrlReady = !!collab.programUrlReady
      root.collaborationManagedSlotsReady = !!collab.managedSlotsReady
      root.collaborationGuestControlReady = !!collab.guestControlReady
      root.collaborationSlotCount = Number(collab.slotCount || 0)
      root.collaborationGuests = Array.isArray(collab.guests) ? collab.guests : []
      root.collaborationObsSceneName = String(collab.obsSceneName || "")
      root.collaborationError = String(collab.error || "")
      if (root.collaborationSlotCount > 0 && root.selectedGuestSlot > root.collaborationSlotCount) root.selectedGuestSlot = root.collaborationSlotCount

      root.dndState = String(state.dndState || "unknown")
      if (!sceneField.activeFocus && root.currentScene !== "") sceneField.text = root.currentScene
    } catch (e) {}
  }

  function refreshStatus() { if (!statusProc.running) statusProc.running = true }

  function feedback(raw) {
    var text = String(raw || "").trim()
    if (text === "") return
    try {
      var data = JSON.parse(text)
      var action = String(data.action || "")
      if (action.indexOf("emergency.") === 0) { root.actionMessage = "Emergency safety action applied"; return }
      switch (action) {
        case "collab.create": root.actionMessage = "Collaboration room ready"; return
        case "collab.rotate": root.actionMessage = "Room rotated — old links are invalid"; return
        case "collab.reset": root.actionMessage = "Collaboration room cleared"; return
        case "collab.open-director": root.actionMessage = "Director opened in browser"; return
        case "collab.copy-invite": root.actionMessage = "Generic guest invite copied"; return
        case "collab.copy-program": root.actionMessage = "Group OBS URL copied"; return
        case "collab.copy-slot-invite": root.actionMessage = "Guest " + data.slot + " invite copied"; return
        case "collab.copy-slot-source": root.actionMessage = "Guest " + data.slot + " OBS URL copied"; return
        case "collab.slot-rotate": root.actionMessage = "Guest " + data.slot + " link rotated"; return
        case "collab.obs-add-program": root.actionMessage = "Guest group added to OBS"; return
        case "collab.obs-add-slot": root.actionMessage = "Guest " + data.slot + " added to OBS"; return
        case "collab.guest-refresh": root.actionMessage = "Guest presence refreshed"; return
        case "collab.guest-mute": root.actionMessage = "Guest " + data.slot + " microphone muted"; return
        case "collab.guest-unmute": root.actionMessage = "Guest " + data.slot + " microphone unmuted"; return
        case "collab.guest-disconnect": root.actionMessage = "Guest " + data.slot + " disconnected"; return
        case "onboarding.open": root.actionMessage = "Guide opened"; return
      }
    } catch (e) {}
    root.actionMessage = text
  }

  function runAction(name, arg) {
    if (actionProc.running) return
    var argv = ["bash", root.helperPath, "action", name]
    if (arg !== undefined && arg !== null && String(arg) !== "") argv.push(String(arg))
    root.actionMessage = "Working…"
    actionProc.command = argv
    actionProc.running = true
  }

  function setMicVolumeDelta(delta) {
    if (root.micVolumePercent === null || root.micVolumePercent === undefined) return
    root.runAction("mic.volume", Math.round(Math.max(0, Math.min(150, Number(root.micVolumePercent) + delta))))
  }

  function shiftGuest(delta) {
    if (root.collaborationSlotCount < 1) return
    var next = root.selectedGuestSlot + delta
    if (next < 1) next = root.collaborationSlotCount
    if (next > root.collaborationSlotCount) next = 1
    root.selectedGuestSlot = next
  }

  function close() { root.popupOpen = false }

  Process {
    id: statusProc
    command: ["bash", root.helperPath, "status"]
    running: false
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.applyStatus(text) }
  }

  Process {
    id: actionProc
    running: false
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.feedback(text) }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: root.feedback(text) }
    onExited: function(exitCode) {
      if (exitCode === 0 && (root.actionMessage === "" || root.actionMessage === "Working…")) root.actionMessage = "Done"
      delayedRefresh.restart()
      feedbackTimer.restart()
    }
  }

  Timer { id: delayedRefresh; interval: 500; repeat: false; onTriggered: root.refreshStatus() }
  Timer { id: feedbackTimer; interval: 3500; repeat: false; onTriggered: root.actionMessage = "" }
  Timer { interval: 3000; repeat: true; running: true; onTriggered: root.refreshStatus() }

  Row {
    id: statusRow
    anchors.centerIn: parent
    spacing: Style.space(6)
    Text {
      text: root.captureActive ? "●" : (root.active ? "●" : "○")
      color: root.captureActive || root.privacyWarning || root.micWarning || root.safetyWarning ? Color.urgent : (root.active ? Color.accent : root.bar.barForeground)
      font.family: root.bar.fontFamily
      font.pixelSize: Style.font.body
      anchors.verticalCenter: parent.verticalCenter
    }
    Text {
      visible: !root.bar.vertical
      text: root.barLabel
      color: root.captureActive ? Color.urgent : root.bar.barForeground
      font.family: root.bar.fontFamily
      font.pixelSize: Style.font.body
      font.bold: root.captureActive
      anchors.verticalCenter: parent.verticalCenter
    }
  }

  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    onClicked: function(mouse) { if (mouse.button === Qt.RightButton) root.runAction("mode.toggle"); else root.popupOpen = !root.popupOpen }
    onEntered: if (root.bar) root.bar.showTooltip(root, root.live ? "LIVE — click for stream controls" : (root.rec ? "Recording — click for controls" : "Streamer Mode · left-click controls · right-click toggle"))
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }

  PopupCard {
    id: popup
    anchorItem: root
    bar: root.bar
    owner: root
    open: root.popupOpen
    contentWidth: popup.fittedContentWidth(Style.space(440))
    contentHeight: popup.fittedContentHeight(content.implicitHeight)

    Column {
      id: content
      anchors.fill: parent
      spacing: Style.space(10)

      Text {
        width: parent.width
        text: root.live ? "Streamer Mode — LIVE" : (root.rec ? "Streamer Mode — RECORDING" : (root.active ? "Streamer Mode — ACTIVE" : "Streamer Mode — STANDBY"))
        color: root.captureActive ? Color.urgent : (root.active ? Color.accent : Color.foreground)
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.title
        font.bold: true
      }

      Text {
        width: parent.width
        text: "OBS " + (root.obsWebSocketReady ? "connected" : (root.obsRunning ? "running · WebSocket unavailable" : (root.obsInstalled ? "ready" : "missing")))
              + "  ·  PipeWire " + (root.pipewireReady ? "ready" : "not detected")
              + "\nPrivacy " + (root.privacy ? "ON" : "off") + "  ·  DND " + root.dndState
              + (root.currentScene ? "\nScene: " + root.currentScene : "")
        color: root.privacyWarning ? Color.urgent : Color.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.body
        wrapMode: Text.Wrap
      }

      Text { visible: root.privacyWarning; width: parent.width; text: "⚠ Capture is active while Streamer Privacy is OFF"; color: Color.urgent; font.family: root.bar.fontFamily; font.pixelSize: Style.font.body; font.bold: true; wrapMode: Text.Wrap }
      Text { visible: root.safetyWarning; width: parent.width; text: "⚠ Sensitive window is active while capture is running" + (root.activeWindowClass ? " · " + root.activeWindowClass : ""); color: Color.urgent; font.family: root.bar.fontFamily; font.pixelSize: Style.font.body; font.bold: true; wrapMode: Text.Wrap }

      Row {
        width: parent.width
        spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)*0.68; fontFamily: root.bar.fontFamily; label: root.active ? "Disable Streamer Mode" : "Enable Streamer Mode"; onClicked: root.runAction("mode.toggle") }
        StreamerButton { width: (parent.width-parent.spacing)*0.32; fontFamily: root.bar.fontFamily; label: "Guide"; onClicked: root.runAction("onboarding.open", "tour") }
      }

      Text { width: parent.width; text: "Emergency"; color: Color.foreground; font.family: root.bar.fontFamily; font.pixelSize: Style.font.subtitle; font.bold: true }
      Row {
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "End Live + Mute"; danger: true; emphasis: root.live; onClicked: root.runAction("emergency.end-live") }
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Stop All Capture"; danger: true; emphasis: root.captureActive || root.replaying; onClicked: root.runAction("emergency.stop-all") }
      }

      Row {
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: root.live ? "Stop Stream" : "Start Stream"; available: root.obsWebSocketReady; danger: root.live; emphasis: root.live; onClicked: root.runAction(root.live ? "stream.stop" : "stream.start") }
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: root.rec ? "Stop Recording" : "Start Recording"; available: root.obsWebSocketReady; danger: root.rec; emphasis: root.rec; onClicked: root.runAction(root.rec ? "record.stop" : "record.start") }
      }
      Row {
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: root.replaying ? "Stop Replay Buffer" : "Start Replay Buffer"; available: root.obsWebSocketReady; onClicked: root.runAction(root.replaying ? "replay.stop" : "replay.start") }
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Save Clip"; available: root.obsWebSocketReady && root.replaying; onClicked: root.runAction("clip.save") }
      }
      Row {
        width: parent.width; spacing: Style.space(8)
        QQC.TextField {
          id: sceneField
          width: parent.width - sceneButton.width - parent.spacing
          height: Style.space(36)
          placeholderText: "OBS scene name"
          selectByMouse: true
          color: Color.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.body
          enabled: root.obsWebSocketReady
          background: Rectangle { radius: Style.cornerRadius; color: Qt.rgba(Color.foreground.r,Color.foreground.g,Color.foreground.b,0.07); border.width: sceneField.activeFocus ? 1 : 0; border.color: Color.accent }
          onAccepted: if (text.trim() !== "") root.runAction("scene.set", text.trim())
        }
        StreamerButton { id: sceneButton; width: Style.space(100); fontFamily: root.bar.fontFamily; label: "Set Scene"; available: root.obsWebSocketReady && sceneField.text.trim() !== ""; onClicked: root.runAction("scene.set", sceneField.text.trim()) }
      }

      Rectangle { width: parent.width; height: Style.space(1); color: Qt.rgba(Color.foreground.r,Color.foreground.g,Color.foreground.b,0.16) }

      Text { width: parent.width; text: "Collaboration"; color: Color.foreground; font.family: root.bar.fontFamily; font.pixelSize: Style.font.subtitle; font.bold: true }
      Text {
        width: parent.width
        text: root.collaborationActive
              ? ((root.collaborationProviderLabel || "Browser guest") + " room ready · " + root.collaborationSlotCount + " managed guest slots")
              : "No guest room yet · create one when collaborators are joining"
        color: Color.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.bodySmall
        wrapMode: Text.Wrap
      }
      Row {
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: root.collaborationActive ? "Room Ready" : "Create Room"; available: root.collaborationReady && !root.collaborationActive; onClicked: root.runAction("collab.create") }
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Open Director"; available: root.collaborationActive && root.collaborationBrowserReady; onClicked: root.runAction("collab.open-director") }
      }
      Row {
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Copy General Invite"; available: root.collaborationInviteReady && root.collaborationClipboardReady; onClicked: root.runAction("collab.copy-invite") }
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Add Group to OBS"; available: root.collaborationProgramUrlReady && root.obsWebSocketReady; onClicked: root.runAction("collab.obs-add-program") }
      }
      Row {
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Copy Group OBS URL"; available: root.collaborationProgramUrlReady && root.collaborationClipboardReady; onClicked: root.runAction("collab.copy-program") }
        Text {
          width: (parent.width-parent.spacing)/2
          height: Style.space(36)
          text: root.collaborationObsSceneName ? ("OBS scene: " + root.collaborationObsSceneName) : "OBS guest scene"
          color: Color.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.caption
          verticalAlignment: Text.AlignVCenter
          horizontalAlignment: Text.AlignHCenter
        }
      }

      Text {
        visible: root.collaborationActive && root.collaborationManagedSlotsReady
        width: parent.width
        text: "Managed Guest " + root.selectedGuestSlot + " of " + root.collaborationSlotCount
        color: Color.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.body
        font.bold: true
      }
      Row {
        visible: root.collaborationActive && root.collaborationManagedSlotsReady
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: Style.space(80); fontFamily: root.bar.fontFamily; label: "← Guest"; onClicked: root.shiftGuest(-1) }
        Text { width: parent.width - Style.space(168); height: Style.space(36); text: "Guest " + root.selectedGuestSlot; color: Color.foreground; font.family: root.bar.fontFamily; font.pixelSize: Style.font.body; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter }
        StreamerButton { width: Style.space(80); fontFamily: root.bar.fontFamily; label: "Guest →"; onClicked: root.shiftGuest(1) }
      }

      Text {
        visible: root.collaborationActive && root.collaborationManagedSlotsReady
        width: parent.width
        text: root.selectedGuestState.online === true
              ? ("● ONLINE" + (root.selectedGuestState.stale ? " · STALE" : "") + (root.selectedGuestState.micEnabled === false ? " · MIC MUTED" : (root.selectedGuestState.micEnabled === true ? " · MIC ON" : "")))
              : (root.selectedGuestState.online === false ? "○ OFFLINE" : (root.selectedGuestState.error === "connection" ? "• CONTROL UNAVAILABLE" : "• STATUS UNKNOWN"))
        color: root.selectedGuestState.online === true && !root.selectedGuestState.stale ? Color.accent : (root.selectedGuestState.error ? Color.urgent : Color.foreground)
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.bodySmall
        font.bold: root.selectedGuestState.online === true
      }

      Row {
        visible: root.collaborationActive && root.collaborationManagedSlotsReady
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Refresh Guests"; available: root.collaborationGuestControlReady; onClicked: root.runAction("collab.guest-refresh") }
        StreamerButton {
          width: (parent.width-parent.spacing)/2
          fontFamily: root.bar.fontFamily
          label: root.selectedGuestState.micEnabled === false ? "Unmute Guest" : "Mute Guest"
          available: root.selectedGuestState.online === true
          danger: root.selectedGuestState.micEnabled === false
          onClicked: root.runAction(root.selectedGuestState.micEnabled === false ? "collab.guest-unmute" : "collab.guest-mute", root.selectedGuestSlot)
        }
      }
      StreamerButton {
        visible: root.collaborationActive && root.collaborationManagedSlotsReady
        width: parent.width
        fontFamily: root.bar.fontFamily
        label: "Disconnect Guest " + root.selectedGuestSlot
        available: root.selectedGuestState.online === true
        danger: true
        onClicked: root.runAction("collab.guest-disconnect", root.selectedGuestSlot)
      }

      Row {
        visible: root.collaborationActive && root.collaborationManagedSlotsReady
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Copy Guest Invite"; available: root.collaborationClipboardReady; onClicked: root.runAction("collab.copy-slot-invite", root.selectedGuestSlot) }
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Add Guest to OBS"; available: root.obsWebSocketReady; onClicked: root.runAction("collab.obs-add-slot", root.selectedGuestSlot) }
      }
      Row {
        visible: root.collaborationActive && root.collaborationManagedSlotsReady
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Copy Guest OBS URL"; available: root.collaborationClipboardReady; onClicked: root.runAction("collab.copy-slot-source", root.selectedGuestSlot) }
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Rotate Guest Link"; danger: true; onClicked: root.runAction("collab.slot-rotate", root.selectedGuestSlot) }
      }
      Row {
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Rotate Room"; available: root.collaborationActive; danger: true; onClicked: root.runAction("collab.rotate") }
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Clear Room"; available: root.collaborationActive; danger: true; onClicked: root.runAction("collab.reset") }
      }
      Text {
        visible: root.collaborationError !== "" || (root.collaborationActive && (!root.collaborationClipboardReady || !root.collaborationBrowserReady))
        width: parent.width
        text: root.collaborationError !== "" ? ("Collaboration: " + root.collaborationError) : ((!root.collaborationClipboardReady ? "wl-copy missing · link copying unavailable" : "") + (!root.collaborationClipboardReady && !root.collaborationBrowserReady ? " · " : "") + (!root.collaborationBrowserReady ? "xdg-open missing · director launch unavailable" : ""))
        color: Color.urgent
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.caption
        wrapMode: Text.Wrap
      }
      Text {
        width: parent.width
        text: "Guest presence requires a callback from that guest page and becomes stale after 30 seconds. Private room, stream and page-control IDs never appear in status."
        color: Qt.darker(Color.foreground,1.25)
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.caption
        wrapMode: Text.Wrap
      }

      Rectangle { width: parent.width; height: Style.space(1); color: Qt.rgba(Color.foreground.r,Color.foreground.g,Color.foreground.b,0.16) }

      Text { width: parent.width; text: "Stream-Safe Workspace"; color: Color.foreground; font.family: root.bar.fontFamily; font.pixelSize: Style.font.subtitle; font.bold: true }
      Text {
        width: parent.width
        text: root.safetyReady ? ("Workspace: " + (root.workspaceName || "unknown") + (root.streamSafeActive ? "  ·  STREAM-SAFE" : "") + (root.sensitiveActive ? "\n⚠ Sensitive window detected" : "\nActive window check: clear")) : ("Stream-Safe unavailable" + (root.safetyError ? ": " + root.safetyError : ""))
        color: root.sensitiveActive ? Color.urgent : Color.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.bodySmall
        wrapMode: Text.Wrap
      }
      Row {
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: root.streamSafeActive ? "Return Workspace" : "Enter Stream-Safe"; available: root.safetyReady || root.streamSafeActive; onClicked: root.runAction(root.streamSafeActive ? "workspace.exit" : "workspace.enter") }
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: "Refresh Safety"; onClicked: root.runAction("safety.refresh") }
      }
      Text { visible: root.sensitiveActive; width: parent.width; text: "Warning only: Streamer does not hide, close, or move this app automatically."; color: Color.urgent; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption; wrapMode: Text.Wrap }

      Rectangle { width: parent.width; height: Style.space(1); color: Qt.rgba(Color.foreground.r,Color.foreground.g,Color.foreground.b,0.16) }

      Text { width: parent.width; text: "Audio Desk"; color: Color.foreground; font.family: root.bar.fontFamily; font.pixelSize: Style.font.subtitle; font.bold: true }
      Text {
        width: parent.width
        text: root.selectedSourceName !== "" ? ("Mic: " + root.selectedSourceName + (root.selectedSourcePresent ? "" : "  ·  MISSING") + (root.micVolumePercent !== null ? "\nVolume " + Math.round(root.micVolumePercent) + "%" : "") + (root.micMuted === true ? "  ·  MUTED" : "")) : (root.audioReady ? "No microphone selected" : "Audio Desk unavailable")
        color: root.micWarning ? Color.urgent : Color.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.bodySmall
        wrapMode: Text.Wrap
      }
      Row {
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: root.audioSources.length > 1 ? "Next Mic" : "Select Mic"; available: root.audioSources.length > 0; onClicked: root.runAction("mic.next") }
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: root.micMuted === true ? "Unmute Mic" : "Mute Mic"; available: root.selectedSourcePresent; danger: root.micMuted === true; emphasis: root.micMuted === true; onClicked: root.runAction(root.micMuted === true ? "mic.unmute" : "mic.mute") }
      }
      Row {
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: Style.space(72); fontFamily: root.bar.fontFamily; label: "−5%"; available: root.selectedSourcePresent && root.micVolumePercent !== null; onClicked: root.setMicVolumeDelta(-5) }
        Text { width: parent.width - Style.space(152); height: Style.space(36); text: root.micVolumePercent === null ? "Volume —" : "Mic " + Math.round(root.micVolumePercent) + "%"; color: Color.foreground; font.family: root.bar.fontFamily; font.pixelSize: Style.font.bodySmall; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter }
        StreamerButton { width: Style.space(72); fontFamily: root.bar.fontFamily; label: "+5%"; available: root.selectedSourcePresent && root.micVolumePercent !== null; onClicked: root.setMicVolumeDelta(5) }
      }
      Text { visible: root.micWarning || (root.audioError !== "" && root.pipewireReady); width: parent.width; text: root.micWarning ? "⚠ Selected microphone disappeared. Choose another mic before going live." : ("Audio: " + root.audioError); color: Color.urgent; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption; wrapMode: Text.Wrap }

      Row {
        width: parent.width; spacing: Style.space(8)
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: root.obsRunning ? "OBS Running" : "Launch OBS"; available: root.obsInstalled && !root.obsRunning; onClicked: root.runAction("obs.launch") }
        StreamerButton { width: (parent.width-parent.spacing)/2; fontFamily: root.bar.fontFamily; label: root.privacy ? "Privacy ON" : "Privacy off"; danger: root.privacyWarning; onClicked: root.runAction(root.privacy ? "privacy.disable" : "privacy.enable") }
      }

      Text { visible: root.obsRunning && !root.obsWebSocketReady && root.obsWebSocketError !== ""; width: parent.width; text: "OBS control: " + root.obsWebSocketError; color: Color.urgent; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption; wrapMode: Text.Wrap }
      Text { visible: root.actionMessage !== ""; width: parent.width; text: root.actionMessage; color: root.actionMessage.indexOf("error:") === 0 ? Color.urgent : Color.foreground; font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption; wrapMode: Text.Wrap }
      Text { width: parent.width; text: "v0.8 Guest Control · callback presence · remote mic · disconnect"; color: Qt.darker(Color.foreground,1.35); font.family: root.bar.fontFamily; font.pixelSize: Style.font.caption; wrapMode: Text.Wrap }
    }
  }

  Component.onCompleted: root.refreshStatus()
}
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

  property string dndState: "unknown"
  property string statusBuffer: ""
  property string actionMessage: ""

  readonly property bool live: root.streaming === true
  readonly property bool rec: root.recording === true
  readonly property bool captureActive: root.live || root.rec
  readonly property bool privacyWarning: root.captureActive && !root.privacy
  readonly property bool micWarning: root.selectedSourceName !== "" && !root.selectedSourcePresent
  readonly property string barLabel: root.live ? "LIVE" : (root.rec ? "REC" : (root.active ? "STREAM" : "Stream"))

  implicitWidth: statusRow.implicitWidth + Style.space(14)
  implicitHeight: barSize

  function applyStatus(raw) {
    try {
      var state = JSON.parse(String(raw || "{}"))
      var obs = state.obsWebSocket || {}
      var audio = state.audio || {}
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

      root.dndState = String(state.dndState || "unknown")
      if (!sceneField.activeFocus && root.currentScene !== "") sceneField.text = root.currentScene
    } catch (e) {}
  }

  function refreshStatus() {
    if (statusProc.running) return
    root.statusBuffer = ""
    statusProc.running = true
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
    var next = Math.max(0, Math.min(150, Number(root.micVolumePercent) + delta))
    root.runAction("mic.volume", Math.round(next))
  }

  function close() { root.popupOpen = false }

  Process {
    id: statusProc
    command: ["bash", root.helperPath, "status"]
    running: false
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.applyStatus(text)
    }
  }

  Process {
    id: actionProc
    running: false
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (text.trim() !== "") root.actionMessage = text.trim()
    }
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (text.trim() !== "") root.actionMessage = text.trim()
    }
    onExited: function(exitCode) {
      if (exitCode === 0 && (root.actionMessage === "" || root.actionMessage === "Working…")) root.actionMessage = "Done"
      delayedRefresh.restart()
      feedbackTimer.restart()
    }
  }

  Timer {
    id: delayedRefresh
    interval: 500
    repeat: false
    onTriggered: root.refreshStatus()
  }

  Timer {
    id: feedbackTimer
    interval: 3500
    repeat: false
    onTriggered: root.actionMessage = ""
  }

  Timer {
    interval: 3000
    repeat: true
    running: true
    onTriggered: root.refreshStatus()
  }

  Row {
    id: statusRow
    anchors.centerIn: parent
    spacing: Style.space(6)

    Text {
      text: root.captureActive ? "●" : (root.active ? "●" : "○")
      color: root.captureActive || root.privacyWarning || root.micWarning ? Color.urgent : (root.active ? Color.accent : root.bar.barForeground)
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

    onClicked: function(mouse) {
      if (mouse.button === Qt.RightButton) root.runAction("mode.toggle")
      else root.popupOpen = !root.popupOpen
    }

    onEntered: if (root.bar) root.bar.showTooltip(root, root.live ? "LIVE — click for stream controls" : (root.rec ? "Recording — click for controls" : "Streamer Mode"))
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }

  PopupCard {
    id: popup
    anchorItem: root
    bar: root.bar
    owner: root
    open: root.popupOpen
    contentWidth: popup.fittedContentWidth(Style.space(410))
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

      Text {
        visible: root.privacyWarning
        width: parent.width
        text: "⚠ Capture is active while Streamer Privacy is OFF"
        color: Color.urgent
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.body
        font.bold: true
        wrapMode: Text.Wrap
      }

      Rectangle {
        width: parent.width
        height: Style.space(38)
        radius: Style.cornerRadius
        color: modeMouse.containsMouse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.18) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
        Text {
          anchors.centerIn: parent
          text: root.active ? "Disable Streamer Mode" : "Enable Streamer Mode"
          color: Color.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.body
        }
        MouseArea {
          id: modeMouse
          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          onClicked: root.runAction("mode.toggle")
        }
      }

      Row {
        width: parent.width
        spacing: Style.space(8)

        Rectangle {
          width: (parent.width - parent.spacing) / 2
          height: Style.space(38)
          radius: Style.cornerRadius
          color: streamMouse.containsMouse ? Qt.rgba(Color.urgent.r, Color.urgent.g, Color.urgent.b, 0.2) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
          Text {
            anchors.centerIn: parent
            text: root.live ? "Stop Stream" : "Start Stream"
            color: root.live ? Color.urgent : (root.obsWebSocketReady ? Color.foreground : Qt.darker(Color.foreground, 1.5))
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.body
            font.bold: root.live
          }
          MouseArea {
            id: streamMouse
            anchors.fill: parent
            enabled: root.obsWebSocketReady
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.runAction(root.live ? "stream.stop" : "stream.start")
          }
        }

        Rectangle {
          width: (parent.width - parent.spacing) / 2
          height: Style.space(38)
          radius: Style.cornerRadius
          color: recordMouse.containsMouse ? Qt.rgba(Color.urgent.r, Color.urgent.g, Color.urgent.b, 0.2) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
          Text {
            anchors.centerIn: parent
            text: root.rec ? "Stop Recording" : "Start Recording"
            color: root.rec ? Color.urgent : (root.obsWebSocketReady ? Color.foreground : Qt.darker(Color.foreground, 1.5))
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.body
            font.bold: root.rec
          }
          MouseArea {
            id: recordMouse
            anchors.fill: parent
            enabled: root.obsWebSocketReady
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.runAction(root.rec ? "record.stop" : "record.start")
          }
        }
      }

      Row {
        width: parent.width
        spacing: Style.space(8)

        Rectangle {
          width: (parent.width - parent.spacing) / 2
          height: Style.space(36)
          radius: Style.cornerRadius
          color: replayMouse.containsMouse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.18) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
          Text {
            anchors.centerIn: parent
            text: root.replayBuffer === true ? "Stop Replay Buffer" : "Start Replay Buffer"
            color: root.obsWebSocketReady ? Color.foreground : Qt.darker(Color.foreground, 1.5)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.bodySmall
          }
          MouseArea {
            id: replayMouse
            anchors.fill: parent
            enabled: root.obsWebSocketReady
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.runAction(root.replayBuffer === true ? "replay.stop" : "replay.start")
          }
        }

        Rectangle {
          width: (parent.width - parent.spacing) / 2
          height: Style.space(36)
          radius: Style.cornerRadius
          color: clipMouse.containsMouse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.18) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
          Text {
            anchors.centerIn: parent
            text: "Save Clip"
            color: root.replayBuffer === true ? Color.foreground : Qt.darker(Color.foreground, 1.5)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.body
          }
          MouseArea {
            id: clipMouse
            anchors.fill: parent
            enabled: root.obsWebSocketReady && root.replayBuffer === true
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.runAction("clip.save")
          }
        }
      }

      Row {
        width: parent.width
        spacing: Style.space(8)

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
          background: Rectangle {
            radius: Style.cornerRadius
            color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
            border.width: sceneField.activeFocus ? 1 : 0
            border.color: Color.accent
          }
          onAccepted: if (text.trim() !== "") root.runAction("scene.set", text.trim())
        }

        Rectangle {
          id: sceneButton
          width: Style.space(96)
          height: Style.space(36)
          radius: Style.cornerRadius
          color: sceneMouse.containsMouse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.18) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
          Text {
            anchors.centerIn: parent
            text: "Set Scene"
            color: root.obsWebSocketReady && sceneField.text.trim() !== "" ? Color.foreground : Qt.darker(Color.foreground, 1.5)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.body
          }
          MouseArea {
            id: sceneMouse
            anchors.fill: parent
            enabled: root.obsWebSocketReady && sceneField.text.trim() !== ""
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.runAction("scene.set", sceneField.text.trim())
          }
        }
      }

      Rectangle {
        width: parent.width
        height: Style.space(1)
        color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.16)
      }

      Text {
        width: parent.width
        text: "Audio Desk"
        color: Color.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.subtitle
        font.bold: true
      }

      Text {
        width: parent.width
        text: root.selectedSourceName !== ""
              ? ("Mic: " + root.selectedSourceName
                 + (root.selectedSourcePresent ? "" : "  ·  MISSING")
                 + (root.micVolumePercent !== null ? "\nVolume " + Math.round(root.micVolumePercent) + "%" : "")
                 + (root.micMuted === true ? "  ·  MUTED" : ""))
              : (root.audioReady ? "No microphone selected" : "Audio Desk unavailable")
        color: root.micWarning ? Color.urgent : Color.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.bodySmall
        wrapMode: Text.Wrap
      }

      Row {
        width: parent.width
        spacing: Style.space(8)

        Rectangle {
          width: (parent.width - parent.spacing) / 2
          height: Style.space(36)
          radius: Style.cornerRadius
          color: nextMicMouse.containsMouse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.18) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
          Text {
            anchors.centerIn: parent
            text: root.audioSources.length > 1 ? "Next Mic" : "Select Mic"
            color: root.audioSources.length > 0 ? Color.foreground : Qt.darker(Color.foreground, 1.5)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.body
          }
          MouseArea {
            id: nextMicMouse
            anchors.fill: parent
            enabled: root.audioSources.length > 0
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.runAction("mic.next")
          }
        }

        Rectangle {
          width: (parent.width - parent.spacing) / 2
          height: Style.space(36)
          radius: Style.cornerRadius
          color: muteMouse.containsMouse ? Qt.rgba(Color.urgent.r, Color.urgent.g, Color.urgent.b, 0.18) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
          Text {
            anchors.centerIn: parent
            text: root.micMuted === true ? "Unmute Mic" : "Mute Mic"
            color: root.micMuted === true ? Color.urgent : (root.selectedSourcePresent ? Color.foreground : Qt.darker(Color.foreground, 1.5))
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.body
            font.bold: root.micMuted === true
          }
          MouseArea {
            id: muteMouse
            anchors.fill: parent
            enabled: root.selectedSourcePresent
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.runAction(root.micMuted === true ? "mic.unmute" : "mic.mute")
          }
        }
      }

      Row {
        width: parent.width
        spacing: Style.space(8)

        Rectangle {
          width: Style.space(72)
          height: Style.space(34)
          radius: Style.cornerRadius
          color: volumeDownMouse.containsMouse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.18) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
          Text {
            anchors.centerIn: parent
            text: "−5%"
            color: root.selectedSourcePresent ? Color.foreground : Qt.darker(Color.foreground, 1.5)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.body
          }
          MouseArea {
            id: volumeDownMouse
            anchors.fill: parent
            enabled: root.selectedSourcePresent && root.micVolumePercent !== null
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.setMicVolumeDelta(-5)
          }
        }

        Text {
          width: parent.width - Style.space(152)
          height: Style.space(34)
          verticalAlignment: Text.AlignVCenter
          horizontalAlignment: Text.AlignHCenter
          text: root.micVolumePercent === null ? "Volume —" : "Mic " + Math.round(root.micVolumePercent) + "%"
          color: Color.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.bodySmall
        }

        Rectangle {
          width: Style.space(72)
          height: Style.space(34)
          radius: Style.cornerRadius
          color: volumeUpMouse.containsMouse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.18) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
          Text {
            anchors.centerIn: parent
            text: "+5%"
            color: root.selectedSourcePresent ? Color.foreground : Qt.darker(Color.foreground, 1.5)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.body
          }
          MouseArea {
            id: volumeUpMouse
            anchors.fill: parent
            enabled: root.selectedSourcePresent && root.micVolumePercent !== null
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.setMicVolumeDelta(5)
          }
        }
      }

      Text {
        visible: root.micWarning || (root.audioError !== "" && root.pipewireReady)
        width: parent.width
        text: root.micWarning ? "⚠ Selected microphone disappeared. Choose another mic before going live." : ("Audio: " + root.audioError)
        color: Color.urgent
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.caption
        wrapMode: Text.Wrap
      }

      Row {
        width: parent.width
        spacing: Style.space(8)

        Rectangle {
          width: (parent.width - parent.spacing) / 2
          height: Style.space(36)
          radius: Style.cornerRadius
          color: obsMouse.containsMouse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.18) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
          Text {
            anchors.centerIn: parent
            text: root.obsRunning ? "OBS Running" : "Launch OBS"
            color: root.obsInstalled ? Color.foreground : Qt.darker(Color.foreground, 1.5)
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.body
          }
          MouseArea {
            id: obsMouse
            anchors.fill: parent
            enabled: root.obsInstalled && !root.obsRunning
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: root.runAction("obs.launch")
          }
        }

        Rectangle {
          width: (parent.width - parent.spacing) / 2
          height: Style.space(36)
          radius: Style.cornerRadius
          color: privacyMouse.containsMouse ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.18) : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)
          Text {
            anchors.centerIn: parent
            text: root.privacy ? "Privacy ON" : "Privacy off"
            color: root.privacyWarning ? Color.urgent : Color.foreground
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.body
          }
          MouseArea {
            id: privacyMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.runAction(root.privacy ? "privacy.disable" : "privacy.enable")
          }
        }
      }

      Text {
        visible: root.obsRunning && !root.obsWebSocketReady && root.obsWebSocketError !== ""
        width: parent.width
        text: "OBS control: " + root.obsWebSocketError
        color: Color.urgent
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.caption
        wrapMode: Text.Wrap
      }

      Text {
        visible: root.actionMessage !== ""
        width: parent.width
        text: root.actionMessage
        color: root.actionMessage.indexOf("error:") === 0 ? Color.urgent : Color.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.caption
        wrapMode: Text.Wrap
      }

      Text {
        width: parent.width
        text: "v0.3 Audio Desk · selected mic control · no silent system-default changes"
        color: Qt.darker(Color.foreground, 1.35)
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.caption
        wrapMode: Text.Wrap
      }
    }
  }

  Component.onCompleted: root.refreshStatus()
}

import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick
import qs.Commons

Item {
  id: root

  readonly property string helperPath: Qt.resolvedUrl("bin/streamerctl").toString().replace(/^file:\/\//, "")
  readonly property int stepCount: 7

  property bool opened: false
  property bool firstRun: false
  property int step: 0
  property var preflight: ({})
  property string statusError: ""

  function open(payload) {
    var args = {}
    if (payload) {
      try { args = JSON.parse(payload) || {} } catch (e) { args = {} }
    }
    var mode = String(args.mode || "tour")
    firstRun = mode === "first-run"
    step = mode === "preflight" ? 1 : 0
    opened = true
    refreshPreflight()
    Qt.callLater(function() { keyHandler.forceActiveFocus() })
  }

  function close() { opened = false }
  function refreshPreflight() { if (!statusProc.running) statusProc.running = true }

  function finish() {
    if (firstRun) {
      if (!completeProc.running) completeProc.running = true
    } else {
      close()
    }
  }

  function skip() { if (!completeProc.running) completeProc.running = true }
  function next() { if (step < stepCount - 1) step += 1; else finish() }
  function previous() { if (step > 0) step -= 1 }

  function titleForStep() {
    var titles = [
      "Welcome to Omarchy Streamer",
      "Preflight check",
      "OBS control",
      "Audio Desk",
      "Stream-Safe & emergency controls",
      "Collaboration",
      "You're ready"
    ]
    return titles[step]
  }

  function bodyForStep() {
    var bodies = [
      "Omarchy Streamer puts OBS, microphone control, privacy, stream-safe workspace tools and browser guests behind one deliberate control surface. It does not silently install packages, ask for root, or close sensitive apps for you.",
      "This page checks the local pieces Streamer can see right now. A warning is not necessarily fatal: for example, OBS WebSocket cannot be connected until OBS itself is running.",
      "Use the main panel to start or stop streaming, recording and the replay buffer, save clips, and switch scenes. OBS remains authoritative: Streamer talks to its authenticated localhost WebSocket instead of storing your stream keys.",
      "Audio Desk remembers the microphone you selected and controls that PipeWire source directly. If the device disappears, Streamer warns you instead of silently switching to another microphone. Use the mute and volume controls before you go live.",
      "Streamer Privacy manages notification DND reversibly. Stream-Safe gives you a dedicated workspace and warns about sensitive windows without moving or killing them. End Live + Mute and Stop All Capture are the emergency buttons when something goes wrong.",
      "Create a browser collaboration room, copy a guest invite, or use one of the four managed guest slots. Managed guests can be added to the dedicated Omarchy Guests scene in OBS. Secret room, stream and control IDs stay out of normal status and IPC output.",
      "Start with OBS running, confirm your microphone, enable Streamer Mode, and glance at the privacy warnings before capture. You can reopen this tour later from the Streamer panel, and the full manual covers each workflow in detail."
    ]
    return bodies[step]
  }

  function mark(ok, unknown) {
    if (unknown) return "•"
    return ok ? "✓" : "⚠"
  }

  function preflightText() {
    var s = preflight || {}
    var obs = s.obsWebSocket || {}
    var audio = s.audio || {}
    var safety = s.safety || {}
    var collab = s.collaboration || {}
    var dndKnown = String(s.dndState || "unknown") !== "unknown"
    var micKnown = String(audio.selectedSourceName || "") !== ""
    return mark(!!s.obsInstalled, false) + " OBS Studio installed\n"
         + mark(!!obs.connected, !s.obsRunning) + " OBS WebSocket " + (obs.connected ? "connected" : (s.obsRunning ? "not connected" : "check after OBS starts")) + "\n"
         + mark(!!s.pipewireReady, false) + " PipeWire running\n"
         + mark(!!audio.selectedPresent, !micKnown) + " Microphone " + (audio.selectedPresent ? "ready" : (micKnown ? "missing" : "not selected yet")) + "\n"
         + mark(dndKnown, false) + " Omarchy notification privacy/DND available\n"
         + mark(!!safety.ready, false) + " Stream-Safe workspace controls available\n"
         + mark(!!collab.ready, false) + " Collaboration controller ready"
  }

  Process {
    id: statusProc
    command: ["bash", root.helperPath, "status"]
    running: false
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try {
          root.preflight = JSON.parse(String(text || "{}"))
          root.statusError = ""
        } catch (e) {
          root.statusError = "Could not parse Streamer status"
        }
      }
    }
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (String(text || "").trim() !== "") root.statusError = String(text).trim()
    }
  }

  Process {
    id: completeProc
    command: ["bash", root.helperPath, "action", "onboarding.complete"]
    running: false
    onExited: root.close()
  }

  PanelWindow {
    id: panel
    visible: root.opened
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    WlrLayershell.namespace: "omarchy-streamer-onboarding"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: root.opened ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
    exclusionMode: ExclusionMode.Ignore

    Rectangle { anchors.fill: parent; color: Qt.rgba(0, 0, 0, 0.72) }
    MouseArea { anchors.fill: parent; onClicked: if (!root.firstRun) root.close() }

    Rectangle {
      id: card
      width: Math.min(parent.width - Style.space(48), Style.space(760))
      height: Math.min(parent.height - Style.space(48), Style.space(620))
      anchors.centerIn: parent
      radius: Style.cornerRadius
      color: Color.background
      border.width: 1
      border.color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.18)

      MouseArea { anchors.fill: parent; onClicked: {} }

      Item {
        id: keyHandler
        anchors.fill: parent
        focus: true
        Keys.onPressed: function(event) {
          if (event.key === Qt.Key_Escape) {
            if (!root.firstRun) root.close()
            event.accepted = true
          } else if (event.key === Qt.Key_Left) {
            root.previous(); event.accepted = true
          } else if (event.key === Qt.Key_Right || event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            root.next(); event.accepted = true
          }
        }
      }

      Column {
        anchors.fill: parent
        anchors.margins: Style.space(28)
        spacing: Style.space(18)

        Row {
          width: parent.width
          spacing: Style.space(12)
          Text {
            width: parent.width - progress.width - parent.spacing
            text: root.firstRun ? "FIRST-RUN GUIDE" : "GUIDED TOUR"
            color: Color.accent
            font.pixelSize: Style.font.caption
            font.bold: true
          }
          Text {
            id: progress
            text: (root.step + 1) + " / " + root.stepCount
            color: Color.foreground
            font.pixelSize: Style.font.caption
          }
        }

        Text {
          width: parent.width
          text: root.titleForStep()
          color: Color.foreground
          font.pixelSize: Style.font.title
          font.bold: true
          wrapMode: Text.Wrap
        }

        Text {
          width: parent.width
          text: root.bodyForStep()
          color: Color.foreground
          font.pixelSize: Style.font.body
          wrapMode: Text.Wrap
          lineHeight: 1.2
        }

        Rectangle {
          visible: root.step === 1
          width: parent.width
          height: preflightColumn.implicitHeight + Style.space(28)
          radius: Style.cornerRadius
          color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.06)
          border.width: 1
          border.color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.12)

          Column {
            id: preflightColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: Style.space(14)
            spacing: Style.space(10)

            Text {
              width: parent.width
              text: root.statusError !== "" ? root.statusError : root.preflightText()
              color: root.statusError !== "" ? Color.urgent : Color.foreground
              font.pixelSize: Style.font.body
              wrapMode: Text.Wrap
              lineHeight: 1.25
            }

            StreamerButton {
              width: parent.width
              label: "Refresh Preflight"
              onClicked: root.refreshPreflight()
            }
          }
        }

        Item { width: 1; height: root.step === 1 ? Style.space(18) : Style.space(120) }

        Text {
          width: parent.width
          text: root.step === 4 ? "Emergency actions are best-effort: if one subsystem is unavailable, Streamer still attempts the remaining safety steps." : (root.step === 5 ? "Guest links never grant shell, filesystem, Streamer IPC or OBS WebSocket access." : "")
          visible: text !== ""
          color: root.step === 4 ? Color.urgent : Qt.darker(Color.foreground, 1.2)
          font.pixelSize: Style.font.caption
          wrapMode: Text.Wrap
        }

        Row {
          width: parent.width
          spacing: Style.space(8)

          StreamerButton {
            width: Style.space(100)
            label: "Manual"
            onClicked: Quickshell.execDetached(["xdg-open", "https://github.com/Drecullith/omarchy-streamer/blob/main/docs/USER_GUIDE.md"])
          }

          StreamerButton {
            width: Style.space(100)
            label: "Back"
            available: root.step > 0
            onClicked: root.previous()
          }

          Item {
            width: parent.width - (root.firstRun ? Style.space(432) : Style.space(324))
            height: 1
          }

          StreamerButton {
            visible: root.firstRun
            width: Style.space(100)
            label: "Skip"
            onClicked: root.skip()
          }

          StreamerButton {
            width: Style.space(100)
            label: root.step === root.stepCount - 1 ? "Finish" : "Next"
            emphasis: root.step === root.stepCount - 1
            onClicked: root.next()
          }
        }
      }
    }
  }
}

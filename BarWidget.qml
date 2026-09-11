import QtQuick
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
  property bool pipewireReady: false
  property string dndState: "unknown"
  property string statusBuffer: ""

  implicitWidth: statusRow.implicitWidth + Style.space(14)
  implicitHeight: barSize

  function applyStatus(raw) {
    try {
      var state = JSON.parse(String(raw || "{}"))
      root.active = !!state.active
      root.privacy = !!state.privacy
      root.obsInstalled = !!state.obsInstalled
      root.obsRunning = !!state.obsRunning
      root.pipewireReady = !!state.pipewireReady
      root.dndState = String(state.dndState || "unknown")
    } catch (e) {}
  }

  function refreshStatus() {
    if (statusProc.running) return
    root.statusBuffer = ""
    statusProc.running = true
  }

  function runAction(name) {
    if (actionProc.running) return
    actionProc.command = ["bash", root.helperPath, "action", name]
    actionProc.running = true
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
    onExited: delayedRefresh.restart()
  }

  Timer {
    id: delayedRefresh
    interval: 350
    repeat: false
    onTriggered: root.refreshStatus()
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
      text: root.active ? "●" : "○"
      color: root.active ? Color.urgent : root.bar.barForeground
      font.family: root.bar.fontFamily
      font.pixelSize: Style.font.body
      anchors.verticalCenter: parent.verticalCenter
    }

    Text {
      visible: !root.bar.vertical
      text: root.active ? "STREAM" : "Stream"
      color: root.bar.barForeground
      font.family: root.bar.fontFamily
      font.pixelSize: Style.font.body
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

    onEntered: if (root.bar) root.bar.showTooltip(root, root.active ? "Streamer Mode active" : "Streamer Mode")
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }

  PopupCard {
    id: popup
    anchorItem: root
    bar: root.bar
    owner: root
    open: root.popupOpen
    contentWidth: popup.fittedContentWidth(Style.space(340))
    contentHeight: popup.fittedContentHeight(content.implicitHeight)

    Column {
      id: content
      anchors.fill: parent
      spacing: Style.space(10)

      Text {
        width: parent.width
        text: root.active ? "Streamer Mode — ACTIVE" : "Streamer Mode — STANDBY"
        color: root.active ? Color.urgent : Color.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.title
        font.bold: true
      }

      Text {
        width: parent.width
        text: "OBS " + (root.obsRunning ? "running" : (root.obsInstalled ? "ready" : "missing"))
              + "  ·  PipeWire " + (root.pipewireReady ? "ready" : "not detected")
              + "\nPrivacy " + (root.privacy ? "ON" : "off") + "  ·  DND " + root.dndState
        color: Color.foreground
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.body
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
            color: Color.foreground
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
        width: parent.width
        text: "v0.1 baseline · stream/record/scene controls land through the same action contract next"
        color: Qt.darker(Color.foreground, 1.35)
        font.family: root.bar.fontFamily
        font.pixelSize: Style.font.caption
        wrapMode: Text.Wrap
      }
    }
  }

  Component.onCompleted: root.refreshStatus()
}

import QtQuick
import qs.Commons

Rectangle {
  id: root

  property string label: ""
  property bool available: true
  property bool danger: false
  property bool emphasis: false
  property string fontFamily: ""
  signal clicked()

  height: Style.space(36)
  radius: Style.cornerRadius
  color: mouse.containsMouse
         ? (root.danger
            ? Qt.rgba(Color.urgent.r, Color.urgent.g, Color.urgent.b, 0.22)
            : Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.18))
         : Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.07)

  Text {
    anchors.centerIn: parent
    text: root.label
    color: !root.available
           ? Qt.darker(Color.foreground, 1.5)
           : (root.danger || root.emphasis ? Color.urgent : Color.foreground)
    font.family: root.fontFamily
    font.pixelSize: Style.font.body
    font.bold: root.emphasis
  }

  MouseArea {
    id: mouse
    anchors.fill: parent
    enabled: root.available
    hoverEnabled: true
    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
    onClicked: root.clicked()
  }
}

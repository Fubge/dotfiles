// SDDM login screen. Colors, fonts and the background come from theme.conf,
// which the dotfiles generate from .chezmoidata/palette.toml.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    color: config.bg

    property int sessionIndex: sessionModel.lastIndex
    property string font: config.font
    property int rounding: parseInt(config.rounding)

    function login() {
        error.text = ""
        sddm.login(user.text, password.text, root.sessionIndex)
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            password.text = ""
            error.text = "Wrong password"
            password.forceActiveFocus()
        }
    }

    // ------------------------------------------------------------ background
    Image {
        anchors.fill: parent
        source: config.background
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
    }
    Rectangle { anchors.fill: parent; color: config.bg_dark; opacity: 0.35 }

    // ------------------------------------------------------------ clock + card
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 6

        Text {
            id: clock
            property date now: new Date()
            Layout.alignment: Qt.AlignHCenter
            text: Qt.formatTime(now, "HH:mm")
            color: config.fg
            font { family: root.font; pixelSize: 112; bold: true }
            Timer { interval: 1000; running: true; repeat: true; onTriggered: clock.now = new Date() }
        }
        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.bottomMargin: 40
            text: Qt.formatDate(clock.now, "dddd, d. MMMM")
            color: config.fg_muted
            font { family: root.font; pixelSize: 22 }
        }

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            implicitWidth: 380
            implicitHeight: form.implicitHeight + 48
            radius: root.rounding
            color: config.card
            border { color: config.accent; width: parseInt(config.border) }

            ColumnLayout {
                id: form
                anchors { fill: parent; margins: 24 }
                spacing: 12

                component Field: TextField {
                    Layout.fillWidth: true
                    implicitHeight: 46
                    color: config.fg
                    placeholderTextColor: config.comment
                    selectionColor: config.accent
                    selectedTextColor: config.bg
                    font { family: root.font; pixelSize: 16 }
                    leftPadding: 16
                    background: Rectangle {
                        radius: root.rounding - 4
                        color: config.bg_alt
                        border { width: parent.activeFocus ? 2 : 0; color: config.accent }
                    }
                }

                Field {
                    id: user
                    text: userModel.lastUser
                    placeholderText: "User"
                    KeyNavigation.tab: password
                    onAccepted: password.forceActiveFocus()
                }
                Field {
                    id: password
                    echoMode: TextInput.Password
                    passwordCharacter: "●"
                    placeholderText: "Password"
                    KeyNavigation.tab: user
                    onAccepted: root.login()
                    Component.onCompleted: forceActiveFocus()
                }
                Text {
                    id: error
                    Layout.alignment: Qt.AlignHCenter
                    visible: text !== ""
                    color: config.red
                    font { family: root.font; pixelSize: 14 }
                }
            }
        }
    }

    // ------------------------------------------------------------ session + power
    RowLayout {
        anchors { right: parent.right; bottom: parent.bottom; margins: 28 }
        spacing: 10

        ComboBox {
            id: session
            model: sessionModel
            textRole: "name"
            currentIndex: root.sessionIndex
            onActivated: root.sessionIndex = currentIndex
            implicitWidth: 220
            implicitHeight: 42
            font { family: root.font; pixelSize: 14 }
            contentItem: Text {
                leftPadding: 16
                text: session.displayText
                color: config.fg
                font: session.font
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            background: Rectangle { radius: 21; color: config.card; border { color: config.steel; width: 1 } }
            delegate: ItemDelegate {
                width: session.width
                contentItem: Text { text: model.name; color: config.fg; font: session.font }
                background: Rectangle { color: highlighted ? config.steel : config.bg_alt }
                highlighted: session.highlightedIndex === index
            }
            popup.background: Rectangle { radius: root.rounding; color: config.bg_alt }
        }

        component PowerButton: Rectangle {
            id: btn
            property string glyph
            property string tip
            signal clicked
            implicitWidth: 42; implicitHeight: 42; radius: 21
            color: area.containsMouse ? config.accent : config.card
            border { color: config.steel; width: area.containsMouse ? 0 : 1 }
            Text {
                anchors.centerIn: parent
                text: btn.glyph
                color: area.containsMouse ? config.bg : config.fg
                font { family: root.font; pixelSize: 18 }
            }
            MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; onClicked: btn.clicked() }
        }

        PowerButton { glyph: "⏾"; visible: sddm.canSuspend;  onClicked: sddm.suspend() }
        PowerButton { glyph: "↻"; visible: sddm.canReboot;   onClicked: sddm.reboot() }
        PowerButton { glyph: "⏻"; visible: sddm.canPowerOff; onClicked: sddm.powerOff() }
    }
}

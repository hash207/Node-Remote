import paho.mqtt.client as mqtt
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDIconButton, MDRaisedButton, MDFillRoundFlatButton, MDFlatButton, MDFloatingActionButton
from kivymd.uix.label import MDLabel
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList
from kivymd.uix.pickers import MDTimePicker
from kivymd.uix.dialog import MDDialog
from kivymd.uix.card import MDCard
from datetime import time

# --- CONFIGURATION ---
BROKER_IP = "broker.emqx.io"  # TODO: Replace with your actual ESP MQTT Broker IP
TOPIC = "hash/tvctl"

# --- UI TEMPLATES (KV STRING) ---
# We only define the custom reusable widgets here. The main layout is built in Python.
KV_HELPERS = '''
<DayChip>:
    size_hint_x: None
    width: "40dp"
    md_bg_color: app.theme_cls.primary_color if self.is_active else app.theme_cls.bg_dark
    text_color: "white" if self.is_active else app.theme_cls.text_color
    font_style: "Caption"

<RuleBuilderContent>:
    orientation: "vertical"
    spacing: "12dp"
    size_hint_y: None
    height: "150dp"

    MDLabel:
        text: "Active Days"
        font_style: "Caption"
        theme_text_color: "Hint"

    MDBoxLayout:
        id: day_container
        orientation: "horizontal"
        spacing: "5dp"
        
        DayChip:
            text: "Su"
        DayChip:
            text: "Mo"
        DayChip:
            text: "Tu"
        DayChip:
            text: "We"
        DayChip:
            text: "Th"
        DayChip:
            text: "Fr"
        DayChip:
            text: "Sa"

    MDTextField:
        id: payload_input
        hint_text: "Action / Payload (e.g., POWER, CH_5)"
        mode: "rectangle"

<ScheduleCard>:
    orientation: "vertical"
    padding: "16dp"
    spacing: "8dp"
    size_hint_y: None
    height: "130dp"
    elevation: 2
    md_bg_color: app.theme_cls.bg_dark
    radius: [12, 12, 12, 12]

    MDBoxLayout:
        orientation: "horizontal"
        size_hint_y: None
        height: "40dp"
        
        MDLabel:
            text: root.time_text
            font_style: "H4"
            bold: True
            
        MDSwitch:
            active: root.is_active
            pos_hint: {"center_y": .5}

    MDLabel:
        text: root.days_text
        theme_text_color: "Custom"
        text_color: app.theme_cls.primary_color
        font_style: "Subtitle2"
        bold: True
        size_hint_y: None
        height: "20dp"

    MDBoxLayout:
        orientation: "horizontal"
        spacing: "10dp"
        
        MDIcon:
            icon: "remote-tv"
            theme_text_color: "Hint"
            size_hint_x: None
            width: "24dp"
            
        MDLabel:
            text: root.action_text
            theme_text_color: "Secondary"
            font_style: "Body2"
'''

# --- CUSTOM WIDGET CLASSES ---
class DayChip(MDFlatButton):
    is_active = BooleanProperty(False)
    def on_release(self):
        self.is_active = not self.is_active

class RuleBuilderContent(MDBoxLayout):
    pass

class ScheduleCard(MDCard):
    time_text = StringProperty("")
    days_text = StringProperty("")
    action_text = StringProperty("")
    is_active = BooleanProperty(False)


# --- MAIN APPLICATION ---
class TVRemoteApp(MDApp):
    dialog = None
    temp_time = ""

    def build(self):
        # Load the custom widgets
        Builder.load_string(KV_HELPERS)

        # Configure app theme
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"
        
        # Initialize MQTT Connection
        self.setup_mqtt()

        # Create the Main Bottom Navigation Bar
        nav_bar = MDBottomNavigation(
            panel_color=self.theme_cls.bg_dark,
            selected_color_background=self.theme_cls.primary_color,
            text_color_active=self.theme_cls.text_color
        )

        # ==========================================
        # TAB 1: THE LIVE REMOTE
        # ==========================================
        tab_remote = MDBottomNavigationItem(name='tab_remote', text='Remote', icon='remote-tv')
        remote_root = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        remote_root.add_widget(MDLabel(text="G-Guard Remote", halign="center", font_style="H5", size_hint_y=None, height=dp(50)))
        
        # Top Section
        top_box = MDBoxLayout(orientation='horizontal', spacing=dp(20), size_hint_y=None, height=dp(60))
        top_box.add_widget(MDBoxLayout())
        top_box.add_widget(MDIconButton(icon="power", md_bg_color=get_color_from_hex("#E53935"), theme_icon_color="Custom", icon_color="white", on_release=lambda x: self.send_command("POWER")))
        top_box.add_widget(MDRaisedButton(text="SOURCE", on_release=lambda x: self.send_command("SOURCE"), pos_hint={"center_y": .5}))
        top_box.add_widget(MDIconButton(icon="volume-off", md_bg_color=self.theme_cls.primary_color, theme_icon_color="Custom", icon_color="white", on_release=lambda x: self.send_command("MUTE")))
        top_box.add_widget(MDBoxLayout())
        remote_root.add_widget(top_box)
        
        # Navigation
        nav_box = MDBoxLayout(orientation='horizontal', spacing=dp(20), size_hint_y=None, height=dp(60))
        nav_box.add_widget(MDBoxLayout())
        nav_box.add_widget(MDIconButton(icon="menu", on_release=lambda x: self.send_command("MENU")))
        nav_box.add_widget(MDIconButton(icon="home", on_release=lambda x: self.send_command("HOME")))
        nav_box.add_widget(MDIconButton(icon="keyboard-return", on_release=lambda x: self.send_command("BACK")))
        nav_box.add_widget(MDBoxLayout())
        remote_root.add_widget(nav_box)
        
        # D-Pad
        dpad_grid = MDGridLayout(cols=3, rows=3, spacing=dp(10), size_hint=(None, None), size=(dp(200), dp(200)), pos_hint={"center_x": .5})
        dpad_grid.add_widget(MDBoxLayout()) 
        dpad_grid.add_widget(MDIconButton(icon="chevron-up", icon_size="48sp", on_release=lambda x: self.send_command("UP")))
        dpad_grid.add_widget(MDBoxLayout()) 
        dpad_grid.add_widget(MDIconButton(icon="chevron-left", icon_size="48sp", on_release=lambda x: self.send_command("LEFT")))
        dpad_grid.add_widget(MDFillRoundFlatButton(text="OK", on_release=lambda x: self.send_command("OK")))
        dpad_grid.add_widget(MDIconButton(icon="chevron-right", icon_size="48sp", on_release=lambda x: self.send_command("RIGHT")))
        dpad_grid.add_widget(MDBoxLayout()) 
        dpad_grid.add_widget(MDIconButton(icon="chevron-down", icon_size="48sp", on_release=lambda x: self.send_command("DOWN")))
        dpad_grid.add_widget(MDBoxLayout()) 
        remote_root.add_widget(dpad_grid)
        
        # Rockers
        rocker_box = MDBoxLayout(orientation='horizontal', spacing=dp(50), size_hint_y=None, height=dp(150), pos_hint={"center_x": .5})
        rocker_box.add_widget(MDBoxLayout()) 
        vol_box = MDBoxLayout(orientation='vertical', spacing=dp(5), size_hint_x=None, width=dp(60))
        vol_box.add_widget(MDIconButton(icon="plus", on_release=lambda x: self.send_command("VOL_UP"), pos_hint={"center_x": .5}))
        vol_box.add_widget(MDLabel(text="VOL", halign="center"))
        vol_box.add_widget(MDIconButton(icon="minus", on_release=lambda x: self.send_command("VOL_DOWN"), pos_hint={"center_x": .5}))
        rocker_box.add_widget(vol_box)
        ch_box = MDBoxLayout(orientation='vertical', spacing=dp(5), size_hint_x=None, width=dp(60))
        ch_box.add_widget(MDIconButton(icon="chevron-up", on_release=lambda x: self.send_command("CH_UP"), pos_hint={"center_x": .5}))
        ch_box.add_widget(MDLabel(text="CH", halign="center"))
        ch_box.add_widget(MDIconButton(icon="chevron-down", on_release=lambda x: self.send_command("CH_DOWN"), pos_hint={"center_x": .5}))
        rocker_box.add_widget(ch_box)
        rocker_box.add_widget(MDBoxLayout()) 
        remote_root.add_widget(rocker_box)
        
        # Media
        media_box = MDBoxLayout(orientation='horizontal', spacing=dp(20), size_hint_y=None, height=dp(60))
        media_box.add_widget(MDBoxLayout()) 
        media_box.add_widget(MDIconButton(icon="rewind", on_release=lambda x: self.send_command("REWIND")))
        media_box.add_widget(MDIconButton(icon="play-pause", on_release=lambda x: self.send_command("PLAY_PAUSE")))
        media_box.add_widget(MDIconButton(icon="fast-forward", on_release=lambda x: self.send_command("FAST_FORWARD")))
        media_box.add_widget(MDBoxLayout()) 
        remote_root.add_widget(media_box)
        
        # YouTube
        youtube_box = MDBoxLayout(orientation='horizontal', padding=[dp(50), dp(10), dp(50), dp(0)], size_hint_y=None, height=dp(60), pos_hint={"center_x": .5})
        youtube_box.add_widget(MDBoxLayout())
        youtube_box.add_widget(MDRaisedButton(text="YOUTUBE", md_bg_color=get_color_from_hex("#FF0000"), theme_text_color="Custom", text_color="white", size_hint=(None, None), size=(dp(200), dp(40)), pos_hint={"center_x": .5}, on_release=lambda x: self.send_command("YOUTUBE")))
        youtube_box.add_widget(MDBoxLayout())
        remote_root.add_widget(youtube_box)
        
        remote_root.add_widget(MDBoxLayout()) 
        tab_remote.add_widget(remote_root)
        nav_bar.add_widget(tab_remote)

        # ==========================================
        # TAB 2: THE AUTOMATION HUB
        # ==========================================
        tab_schedules = MDBottomNavigationItem(name='tab_schedules', text='Schedules', icon='clock-outline')
        schedules_root = MDBoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20))
        schedules_root.add_widget(MDLabel(text="Active Automations", halign="center", font_style="H5", size_hint_y=None, height=dp(50)))
        
        # Dynamic List Container
        scroll = MDScrollView()
        self.rule_list = MDList(spacing=dp(15)) # Added spacing so cards don't touch
        scroll.add_widget(self.rule_list)
        schedules_root.add_widget(scroll)
        
        # Action Button
        fab = MDFloatingActionButton(icon="plus", pos_hint={"center_x": .5}, on_release=lambda x: self.open_time_picker())
        schedules_root.add_widget(fab)
        
        tab_schedules.add_widget(schedules_root)
        nav_bar.add_widget(tab_schedules)

        return nav_bar

    # --- MQTT LOGIC ---
    def setup_mqtt(self):
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            self.mqtt_client = mqtt.Client()

        try:
            self.mqtt_client.connect(BROKER_IP, 1883, 60)
            self.mqtt_client.loop_start() 
            print(f"MQTT Client started and connecting to {BROKER_IP}...")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")

    def send_command(self, payload):
        print(f"Button Pressed! Publishing payload: '{payload}' to topic: '{TOPIC}'")
        try:
            self.mqtt_client.publish(TOPIC, payload)
        except Exception as e:
            print(f"Failed to publish message: {e}")

    # --- AUTOMATION LOGIC ---
    def open_time_picker(self):
        time_dialog = MDTimePicker()
        time_dialog.bind(on_save=self.on_time_save)
        time_dialog.open()

    def on_time_save(self, instance, time_obj):
        self.temp_time = time_obj.strftime("%I:%M %p")
        if not self.dialog:
            self.dialog = MDDialog(
                title=f"Schedule for {self.temp_time}",
                type="custom",
                content_cls=RuleBuilderContent(),
                buttons=[
                    MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
                    MDFlatButton(text="SAVE", on_release=self.save_new_rule),
                ],
            )
        else:
            self.dialog.title = f"Schedule for {self.temp_time}"
        self.dialog.open()

    def save_new_rule(self, instance):
        content = self.dialog.content_cls
        
        # Extract selected days
        selected_days = []
        for child in reversed(content.ids.day_container.children):
            if isinstance(child, DayChip) and child.is_active:
                selected_days.append(child.text)
        days_string = " • ".join(selected_days) if selected_days else "No Days Selected"
        
        # Extract command payload
        payload = content.ids.payload_input.text or "NO_COMMAND"

        # Create and add the card
        new_card = ScheduleCard(
            time_text=self.temp_time,
            days_text=days_string,
            action_text=payload,
            is_active=True
        )
        self.rule_list.add_widget(new_card)
        
        # Reset the dialog for next time
        content.ids.payload_input.text = ""
        for child in content.ids.day_container.children:
            child.is_active = False
            
        self.dialog.dismiss()

    def on_stop(self):
        if hasattr(self, 'mqtt_client'):
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

if __name__ == '__main__':
    TVRemoteApp().run()
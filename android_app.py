import json
from datetime import time
from kivy.metrics import dp
from kivymd.app import MDApp
from kivy.lang import Builder
import paho.mqtt.client as mqtt
from kivymd.uix.card import MDCard
from kivymd.uix.list import MDList
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivy.utils import get_color_from_hex
from kivymd.uix.pickers import MDTimePicker
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivy.network.urlrequest import UrlRequest
from kivymd.uix.scrollview import MDScrollView
from kivy.properties import StringProperty, BooleanProperty
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.button import MDIconButton, MDRaisedButton, MDFillRoundFlatButton, MDFlatButton, MDFloatingActionButton

# --- CONFIGURATION ---
BROKER_IP = "broker.emqx.io"  # TODO: Replace with your actual ESP MQTT Broker IP
TOPIC = "hash/tvctl"
SERVER_IP = "https://safe-shiner-daring.ngrok-free.app"

# --- UI TEMPLATES (KV STRING) ---
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
    height: "180dp"

    MDLabel:
        text: "Active Days"
        font_style: "Caption"
        theme_text_color: "Hint"

    MDGridLayout:
        id: day_container
        cols: 4
        spacing: "10dp"
        size_hint_y: None
        height: self.minimum_height
        
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
            
        # --- REPLACED SWITCH WITH TRASH ICON ---
        MDIconButton:
            icon: "trash-can-outline"
            theme_text_color: "Error" # Makes the icon red
            pos_hint: {"center_y": .5}
            on_release: app.delete_schedule(root)

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
    rule_id = NumericProperty(-1) # -1 means it hasn't been uploaded to the server yet
    time_text = StringProperty("")
    days_text = StringProperty("")
    action_text = StringProperty("")
    # You can delete is_active = BooleanProperty(False)

# --- MAIN APPLICATION ---
class TVRemoteApp(MDApp):
    dialog = None
    temp_time = ""

    def build(self):
        Builder.load_string(KV_HELPERS)
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"
        self.setup_mqtt()

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
        tab_schedules = MDBottomNavigationItem(
            name='tab_schedules', 
            text='Schedules', 
            icon='clock-outline',
            on_tab_press=self.fetch_schedules # Triggers when tab is clicked
        )
        
        schedules_root = MDBoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20))
        schedules_root.add_widget(MDLabel(text="Active Automations", halign="center", font_style="H5", size_hint_y=None, height=dp(50)))
        
        # Dynamic List Container
        scroll = MDScrollView()
        self.rule_list = MDList(spacing=dp(15))
        scroll.add_widget(self.rule_list)
        schedules_root.add_widget(scroll)
        
        # The dual FAB (Floating Action Button) layout at the bottom
        fab_row = MDBoxLayout(
            orientation="horizontal", 
            spacing=dp(20), 
            size_hint=(None, None), 
            height=dp(56), 
            pos_hint={"center_x": .5}
        )
        
        # Button 2: Upload / Push to Server
        upload_fab = MDFloatingActionButton(
            icon="cloud-upload", 
            on_release=lambda x: self.upload_schedules()
        )
        
        # Button 1: Add New Rule
        add_fab = MDFloatingActionButton(
            icon="plus", 
            on_release=lambda x: self.open_time_picker()
        )
        
        fab_row.add_widget(upload_fab)
        fab_row.add_widget(add_fab)
        
        schedules_root.add_widget(fab_row)
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
    def fetch_schedules(self, instance_tab):
        print("Fetching saved schedules from 100.105.61.4...")
        self.rule_list.clear_widgets()
        endpoint = f"{SERVER_IP}/api/schedules"

        def on_success(req, result):
            for rule in result:
                new_card = ScheduleCard(
                    rule_id=rule.get("id", -1), # Attach the database ID!
                    time_text=rule.get("time_text", "00:00"),
                    days_text=rule.get("days_text", "No Days"),
                    action_text=rule.get("action_text", "NO_COMMAND")
                )
                self.rule_list.add_widget(new_card)

        UrlRequest(endpoint, on_success=on_success)

    def delete_schedule(self, card_widget):
        """Removes the card from the UI and tells the server to delete it."""
        # 1. Instantly remove it from the screen so the app feels fast
        self.rule_list.remove_widget(card_widget)
        
        # 2. If it exists on the server, send the DELETE request
        if card_widget.rule_id != -1:
            print(f"Telling server to delete Rule ID: {card_widget.rule_id}")
            endpoint = f"{SERVER_IP}/api/schedule/{card_widget.rule_id}"
            
            UrlRequest(
                endpoint,
                method='DELETE', # Specify we are deleting, not getting/posting
                on_success=lambda req, res: print(f"Server confirmed deletion."),
                on_failure=lambda req, res: print(f"Failed to delete on server.")
            )

    def upload_schedules(self):
        """Extracts data from the UI cards and pushes to the Ubuntu server."""
        print("Uploading active schedules to 100.105.61.4...")
        
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        endpoint = f"{SERVER_IP}/api/schedule/add"

        for card in self.rule_list.children:
            if isinstance(card, ScheduleCard) and card.rule_id == -1: # Only upload NEW cards
                payload = {
                    "time_text": card.time_text,
                    "days_text": card.days_text,
                    "action_text": card.action_text
                    # REMOVED is_active
                }
                
                def on_success(req, result):
                    print(f"Success! Server replied: {result}")
                    # Update the card's ID so it doesn't get uploaded twice
                    if "db_id" in result:
                        card.rule_id = result["db_id"]
                    
                def on_failure(req, result):
                    print(f"Failed to reach server: {result}")

                UrlRequest(
                    endpoint, 
                    req_body=json.dumps(payload), 
                    req_headers=headers,
                    on_success=on_success,
                    on_failure=on_failure,
                    on_error=on_failure
                )

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
        
        selected_days = []
        for child in reversed(content.ids.day_container.children):
            if isinstance(child, DayChip) and child.is_active:
                selected_days.append(child.text)
        days_string = " • ".join(selected_days) if selected_days else "No Days Selected"
        
        payload = content.ids.payload_input.text or "NO_COMMAND"

        # --- THE FIX IS HERE ---
        new_card = ScheduleCard(
            rule_id=-1, # -1 means it hasn't been uploaded yet
            time_text=self.temp_time,
            days_text=days_string,
            action_text=payload
            # Removed the is_active=True line!
        )
        
        self.rule_list.add_widget(new_card)
        
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
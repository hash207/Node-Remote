import paho.mqtt.client as mqtt
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFillRoundFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel

# --- CONFIGURATION ---
BROKER_IP = "192.168.1.100"  # TODO: Replace with your actual ESP MQTT Broker IP
TOPIC = "hash/tvctl"

class TVRemoteApp(MDApp):
    def build(self):
        # Configure app theme
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"
        
        # Initialize MQTT Connection
        self.setup_mqtt()

        # Root layout
        root = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # Title Label
        root.add_widget(
            MDLabel(
                text="G-Guard Remote", 
                halign="center", 
                font_style="H5", 
                size_hint_y=None, 
                height=dp(50)
            )
        )
        
        # --- Top Section (Power, Source, Mute) ---
        top_box = MDBoxLayout(orientation='horizontal', spacing=dp(20), size_hint_y=None, height=dp(60))
        top_box.add_widget(MDBoxLayout()) # Left spacer
        # Power Button
        top_box.add_widget(
            MDIconButton(
                icon="power", 
                md_bg_color=get_color_from_hex("#E53935"), # Red color for power
                theme_icon_color="Custom",
                icon_color="white",
                on_release=lambda x: self.send_command("POWER")
            )
        )
        # Source Button
        top_box.add_widget(
            MDRaisedButton(
                text="SOURCE", 
                on_release=lambda x: self.send_command("SOURCE"), 
                pos_hint={"center_y": .5}
            )
        )
        # Mute Button
        top_box.add_widget(
            MDIconButton(
                icon="volume-off", 
                md_bg_color=self.theme_cls.primary_color,
                theme_icon_color="Custom",
                icon_color="white",
                on_release=lambda x: self.send_command("MUTE")
            )
        )
        top_box.add_widget(MDBoxLayout()) # Right spacer
        root.add_widget(top_box)
        
        # --- Navigation & Menu ---
        nav_box = MDBoxLayout(orientation='horizontal', spacing=dp(20), size_hint_y=None, height=dp(60))
        nav_box.add_widget(MDBoxLayout()) # Left spacer
        nav_box.add_widget(MDIconButton(icon="menu", on_release=lambda x: self.send_command("MENU")))
        nav_box.add_widget(MDIconButton(icon="home", on_release=lambda x: self.send_command("HOME")))
        nav_box.add_widget(MDIconButton(icon="keyboard-return", on_release=lambda x: self.send_command("BACK")))
        nav_box.add_widget(MDBoxLayout()) # Right spacer
        root.add_widget(nav_box)
        
        # --- D-Pad (Directional Pad) ---
        dpad_grid = MDGridLayout(
            cols=3, 
            rows=3, 
            spacing=dp(10), 
            size_hint=(None, None), 
            size=(dp(200), dp(200)), 
            pos_hint={"center_x": .5}
        )
        
        # Row 1
        dpad_grid.add_widget(MDBoxLayout()) # Empty top-left
        dpad_grid.add_widget(
            MDIconButton(icon="chevron-up", icon_size="48sp", on_release=lambda x: self.send_command("UP"))
        )
        dpad_grid.add_widget(MDBoxLayout()) # Empty top-right
        
        # Row 2
        dpad_grid.add_widget(
            MDIconButton(icon="chevron-left", icon_size="48sp", on_release=lambda x: self.send_command("LEFT"))
        )
        dpad_grid.add_widget(
            MDFillRoundFlatButton(text="OK", on_release=lambda x: self.send_command("OK"))
        )
        dpad_grid.add_widget(
            MDIconButton(icon="chevron-right", icon_size="48sp", on_release=lambda x: self.send_command("RIGHT"))
        )
        
        # Row 3
        dpad_grid.add_widget(MDBoxLayout()) # Empty bottom-left
        dpad_grid.add_widget(
            MDIconButton(icon="chevron-down", icon_size="48sp", on_release=lambda x: self.send_command("DOWN"))
        )
        dpad_grid.add_widget(MDBoxLayout()) # Empty bottom-right
        
        root.add_widget(dpad_grid)
        
        # --- Volume & Channel Rockers ---
        rocker_box = MDBoxLayout(
            orientation='horizontal', 
            spacing=dp(50), 
            size_hint_y=None, 
            height=dp(150), 
            pos_hint={"center_x": .5}
        )
        rocker_box.add_widget(MDBoxLayout()) # Left spacer
        
        # Volume Box
        vol_box = MDBoxLayout(orientation='vertical', spacing=dp(5), size_hint_x=None, width=dp(60))
        vol_box.add_widget(MDIconButton(icon="plus", on_release=lambda x: self.send_command("VOL_UP"), pos_hint={"center_x": .5}))
        vol_box.add_widget(MDLabel(text="VOL", halign="center"))
        vol_box.add_widget(MDIconButton(icon="minus", on_release=lambda x: self.send_command("VOL_DOWN"), pos_hint={"center_x": .5}))
        rocker_box.add_widget(vol_box)
        
        # Channel Box
        ch_box = MDBoxLayout(orientation='vertical', spacing=dp(5), size_hint_x=None, width=dp(60))
        ch_box.add_widget(MDIconButton(icon="chevron-up", on_release=lambda x: self.send_command("CH_UP"), pos_hint={"center_x": .5}))
        ch_box.add_widget(MDLabel(text="CH", halign="center"))
        ch_box.add_widget(MDIconButton(icon="chevron-down", on_release=lambda x: self.send_command("CH_DOWN"), pos_hint={"center_x": .5}))
        rocker_box.add_widget(ch_box)
        
        rocker_box.add_widget(MDBoxLayout()) # Right spacer
        root.add_widget(rocker_box)
        
        # --- Media Controls (Bottom) ---
        media_box = MDBoxLayout(orientation='horizontal', spacing=dp(20), size_hint_y=None, height=dp(60))
        media_box.add_widget(MDBoxLayout()) # Left spacer
        media_box.add_widget(MDIconButton(icon="rewind", on_release=lambda x: self.send_command("REWIND")))
        media_box.add_widget(MDIconButton(icon="play-pause", on_release=lambda x: self.send_command("PLAY_PAUSE")))
        media_box.add_widget(MDIconButton(icon="fast-forward", on_release=lambda x: self.send_command("FAST_FORWARD")))
        media_box.add_widget(MDBoxLayout()) # Right spacer
        root.add_widget(media_box)
        
        # --- YouTube Button ---
        youtube_box = MDBoxLayout(
            orientation='horizontal', 
            padding=[dp(50), dp(10), dp(50), dp(0)], 
            size_hint_y=None, 
            height=dp(60),
            pos_hint={"center_x": .5}
        )
        youtube_box.add_widget(MDBoxLayout())
        youtube_box.add_widget(
            MDRaisedButton(
                text="YOUTUBE", 
                md_bg_color=get_color_from_hex("#FF0000"),
                theme_text_color="Custom",
                text_color="white",
                size_hint=(None, None),
                size=(dp(200), dp(40)),
                pos_hint={"center_x": .5},
                on_release=lambda x: self.send_command("YOUTUBE")
            )
        )
        youtube_box.add_widget(MDBoxLayout())
        root.add_widget(youtube_box)
        
        root.add_widget(MDBoxLayout()) # Bottom spacer to push everything up
        
        return root

    def setup_mqtt(self):
        """Initializes the MQTT client and connects to the broker on a background thread."""
        try:
            # Check if paho-mqtt is version 2.x which requires CallbackAPIVersion
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            # Fallback for paho-mqtt version 1.x
            self.mqtt_client = mqtt.Client()

        try:
            # Connect to broker and start the network loop in the background
            self.mqtt_client.connect(BROKER_IP, 1883, 60)
            self.mqtt_client.loop_start() 
            print(f"MQTT Client started and connecting to {BROKER_IP}...")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")

    def send_command(self, payload):
        """Universal callback function to publish string payload to the target topic."""
        print(f"Button Pressed! Publishing payload: '{payload}' to topic: '{TOPIC}'")
        try:
            self.mqtt_client.publish(TOPIC, payload)
        except Exception as e:
            print(f"Failed to publish message: {e}")

    def on_stop(self):
        """Ensure clean disconnect when the app is closed."""
        if hasattr(self, 'mqtt_client'):
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

if __name__ == '__main__':
    TVRemoteApp().run()

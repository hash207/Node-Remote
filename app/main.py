from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import paho.mqtt.client as mqtt
from app.database import init_db, save_rule, get_all_rules, delete_rule
from time import sleep

# --- CONFIGURATION ---
MQTT_BROKER = "broker.emqx.io"
MQTT_TOPIC = "hash/tvctl"

scheduler = BackgroundScheduler()

try:
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    mqtt_client = mqtt.Client()
    
# Translates your Kivy UI text into APScheduler's 'day_of_week' format
DAY_MAP = {
    "Su": "sun", "Mo": "mon", "Tu": "tue", 
    "We": "wed", "Th": "thu", "Fr": "fri", "Sa": "sat"
}

# --- IR DEFAULT COMMANDS ---
IR_CMDS = ["VOL_UP", "VOL_DOWN", "UP", "DOWN", "POWER_TOGGLE", "RIGHT", "LEFT", "OK", "MUTE", "SOURCE", "BACK", "YOUTUBE", "HOME"]
 
def parse_days(days_text: str) -> str:
    """Converts 'Su • Mo' into 'sun,mon'"""
    if "No Days" in days_text or not days_text:
        return "*" # Asterisk means "Every Day" in Cron
        
    selected_days = days_text.split(" • ")
    cron_days = [DAY_MAP[day] for day in selected_days if day in DAY_MAP]
    return ",".join(cron_days)

# --- THE JSON CONTRACT ---
class SchedulePayload(BaseModel):
    time_text: str
    days_text: str
    action_text: str

def fire_mqtt_action(payload: str):
    print(f"[ALARM TRIGGERED] Firing payload: {payload} to {MQTT_TOPIC}")
    if "," not in payload:
        try:
            mqtt_client.publish(MQTT_TOPIC, payload)
        except Exception as e:
            print(f"Failed to publish scheduled MQTT message: {e}")
    if payload == "START QURAN":
        mqtt_cmds = ["POWER", "WAIT_5", "MEDIA", "WAIT_1", "OK", "WAIT_2", "RIGHT", "RIGHT", "WAIT_1", "OK"]  # Example sequence to start Quran app
        for mqtt_cmd in mqtt_cmds:
            try:
                mqtt_client.publish(MQTT_TOPIC, mqtt_cmd)
                print(f"Published command: {mqtt_cmd}")
            except Exception as e:
                print(f"Failed to publish command '{mqtt_cmd}': {e}")
            sleep(1)  # Short delay between commands
    else:
        commands = payload.replace(" ", "").split(",")
        for cmd in commands:
            if cmd in IR_CMDS:
                try:
                    mqtt_client.publish(MQTT_TOPIC, cmd)
                    print(f"Published command: {cmd}")
                except Exception as e:
                    print(f"Failed to publish command '{cmd}': {e}")
            elif "WAIT" in cmd:
                sleep(int(cmd[cmd.find("_")+1:]) if "_" in cmd else int(cmd[cmd.find("T")+1:]))
            else:
                print(f"Unknown command in payload: {cmd}")

def load_schedules_on_startup():
    """Reads the database and loads all saved rules into the live clock."""
    print("Loading saved schedules from database into the clock...")
    rules = get_all_rules()
    
    for rule in rules:
        # 1. Parse the time string (e.g., "07:00 AM")
        time_parts = rule["time_text"].split()
        time_str = time_parts[0]
        meridiem = time_parts[1]
        hour, minute = map(int, time_str.split(":"))
        
        if meridiem == "PM" and hour != 12:
            hour += 12
        elif meridiem == "AM" and hour == 12:
            hour = 0

        # 2. Parse the Days (USING THE NEW MAPPER)
        cron_days = parse_days(rule["days_text"])

        # 3. Bind it to the MQTT execution function
        scheduler.add_job(
            fire_mqtt_action,
            'cron',
            day_of_week=cron_days,  # <--- Days explicitly mapped here
            hour=hour,
            minute=minute,
            args=[rule["action_text"]], 
            id=f"rule_{rule['id']}",
            replace_existing=True # Prevents duplicate alarms
        )
    print(f"Successfully loaded {len(rules)} active rules into the scheduler.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Database...")
    init_db()
    print("Starting up Home Automation Server Engine...")
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_start()
    
    # --- THE MISSING LINK ---
    load_schedules_on_startup() 
    
    scheduler.start()
    yield
    print("Shutting down Server Engine safely...")
    scheduler.shutdown()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

app = FastAPI(title="G-Guard Automation Hub", lifespan=lifespan)

@app.post("/api/schedule/add")
def add_schedule(rule: SchedulePayload):
    """Catches the JSON from the Kivy App, saves to DB, and starts the timer."""
    
    # 1. Save to SQLite Database (Assume all rules in DB are active by default now)
    rule_id = save_rule(rule.time_text, rule.days_text, rule.action_text, True)
    
    # 2. Parse the time
    time_parts = rule.time_text.split()
    time_str = time_parts[0]
    meridiem = time_parts[1]
    hour, minute = map(int, time_str.split(":"))
    
    if meridiem == "PM" and hour != 12:
        hour += 12
    elif meridiem == "AM" and hour == 12:
        hour = 0

    # 3. Parse the Days (USING THE NEW MAPPER)
    cron_days = parse_days(rule.days_text)

    # 4. Add to the active clock unconditionally
    scheduler.add_job(
        fire_mqtt_action,
        'cron',
        day_of_week=cron_days, # <--- Days explicitly mapped here
        hour=hour,
        minute=minute,
        args=[rule.action_text],
        id=f"rule_{rule_id}",
        replace_existing=True
    )
    
    return {"status": "success", "db_id": rule_id, "message": "Rule saved and scheduled"}

@app.get("/api/schedules")
def get_schedules():
    """Returns all saved schedules to the Kivy app."""
    try:
        rules = get_all_rules()
        return rules # FastAPI automatically converts this list of dicts to JSON!
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.delete("/api/schedule/{rule_id}")
def remove_schedule(rule_id: int):
    """Deletes the rule from the database and stops the active timer."""
    try:
        # 1. Delete from SQLite
        delete_rule(rule_id)
        
        # 2. Stop the APScheduler background job
        job_id = f"rule_{rule_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            
        return {"status": "success", "message": f"Rule {rule_id} deleted."}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

if __name__ == "__main__":
    pass
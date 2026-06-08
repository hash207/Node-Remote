from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import paho.mqtt.client as mqtt
from app.database import init_db, save_rule
from app.database import init_db, save_rule, get_all_rules
from app.database import init_db, save_rule, get_all_rules, delete_rule

# --- CONFIGURATION ---
MQTT_BROKER = "broker.emqx.io"
MQTT_TOPIC = "hash/tvctl"

scheduler = BackgroundScheduler()

try:
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    mqtt_client = mqtt.Client()

# --- THE JSON CONTRACT ---
class SchedulePayload(BaseModel):
    time_text: str
    days_text: str
    action_text: str

def fire_mqtt_action(payload: str):
    print(f"[ALARM TRIGGERED] Firing payload: {payload} to {MQTT_TOPIC}")
    try:
        mqtt_client.publish(MQTT_TOPIC, payload)
    except Exception as e:
        print(f"Failed to publish scheduled MQTT message: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Database...")
    init_db()
    print("Starting up Home Automation Server Engine...")
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_start()
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

    # 3. Add to the active clock unconditionally
    scheduler.add_job(
        fire_mqtt_action,
        'cron',
        hour=hour,
        minute=minute,
        args=[rule.action_text],
        id=f"rule_{rule_id}"
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
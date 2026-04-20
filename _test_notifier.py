import traceback
import sys
try:
    from core.notifier import SmartNotifier
    from database.db_manager import DatabaseManager
    print("1. Imports OK")
    
    db = DatabaseManager()
    db.initialize()
    print("2. DB initialized OK")
    
    n = SmartNotifier(db)
    print("3. SmartNotifier created OK")
    
    prefs = n._load_prefs()
    print("4. Prefs loaded:", prefs)
    
    # Test notification settings upsert
    db.upsert_notification_settings({
        "enabled": True,
        "cooldown_sec": 300,
        "min_severity": "MEDIUM",
        "alert_types_json": {"root_cause": True, "prediction": True, "recommendation": False, "degradation": True, "health_summary": False},
    })
    print("5. Settings upserted OK")
    
    saved = db.get_notification_settings()
    print("6. Settings read back:", saved)
    
    # Test cooldown check
    is_recent = db.notification_sent_recently("test:key", 60)
    print("7. Cooldown check OK (recent=", is_recent, ")")
    
    print("\nALL TESTS PASSED")
except Exception:
    traceback.print_exc()
    sys.exit(1)

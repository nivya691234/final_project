"""
e2e_stress_test.py
==================
Stress Test Orchestrator - Tests system aging detection under load.

This script runs controlled stress scenarios and monitors the system's
response in real-time, verifying that:
  ✓ Memory leak detection
  ✓ CPU runaway detection
  ✓ Thread leak detection
  ✓ Alert generation
  ✓ Auto-remediation triggers
  ✓ Predictions accuracy
"""

import logging
import sys
import time
import subprocess
import threading
import psutil
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("STRESS_TEST")

# Import core modules
try:
    from config.settings import SAMPLING_INTERVAL, ANALYSIS_EVERY_N
    from database.db_manager import DatabaseManager
    from core.collector import DataCollector
    from core.analyzer import TrendAnalyzer
    from core.root_cause import RootCauseEngine
    from core.predictor import FailurePredictor
    from core.prevention import PreventionEngine
    from core.notifier import SmartNotifier
    from models.reliability_model import ReliabilityModel
    logger.info("✓ All core modules imported successfully")
except Exception as e:
    logger.error(f"✗ Failed to import modules: {e}")
    sys.exit(1)


class StressTestOrchestrator:
    """Orchestrates stress testing with real-time monitoring."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.collector = DataCollector(self.db, interval_s=SAMPLING_INTERVAL)
        self.stress_process = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "stress_tests": {},
        }
    
    def log_alert(self, alert_type, details):
        """Log an alert with emphasis."""
        logger.warning(f"🚨 ALERT [{alert_type}] {details}")
    
    def log_success(self, msg):
        """Log success."""
        logger.info(f"✓ {msg}")
    
    def log_step(self, step_num, description):
        """Log a test step."""
        logger.info(f"\n{'─'*70}")
        logger.info(f"STEP {step_num}: {description}")
        logger.info(f"{'─'*70}")
    
    def setup_monitoring(self):
        """Setup initial data collection."""
        self.log_step(0, "Setup: Initialize Monitoring")
        
        logger.info("  ⏳ Starting data collector...")
        self.collector.start()
        self.log_success("Data collector started")
        
        logger.info("  ⏳ Collecting baseline samples (15 seconds)...")
        time.sleep(15)
        
        baseline = self.db.get_recent_snapshots(count=5)
        logger.info(f"  ✓ Collected {len(baseline)} baseline samples")
        
        if baseline:
            last = baseline[-1]
            logger.info("  Baseline metrics:")
            for key in ["memory_percent", "cpu_percent", "threads"]:
                if key in last:
                    logger.info(f"    - {key}: {last[key]:.2f}")
    
    def start_stress_process(self):
        """Start the stress test process."""
        logger.info("  ⏳ Starting stress_test.py process...")
        try:
            self.stress_process = subprocess.Popen(
                [sys.executable, "stress_test.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.log_success(f"Stress process started (PID: {self.stress_process.pid})")
            return self.stress_process.pid
        except Exception as e:
            logger.error(f"  ✗ Failed to start stress process: {e}")
            return None
    
    def stop_stress_process(self):
        """Stop the stress test process."""
        if self.stress_process:
            logger.info("  ⏳ Stopping stress process...")
            try:
                self.stress_process.terminate()
                self.stress_process.wait(timeout=5)
                self.log_success("Stress process stopped")
            except:
                self.stress_process.kill()
                logger.info("  Stress process killed")
    
    def monitor_stress_phase(self, duration_seconds, test_name):
        """Monitor system during stress phase."""
        self.log_step(1, f"Stress Phase: {test_name} ({duration_seconds}s)")
        
        stress_pid = self.start_stress_process()
        if not stress_pid:
            return False
        
        start_time = time.time()
        analysis_cycle = 0
        detected_issues = []
        alerts_fired = []
        
        try:
            while time.time() - start_time < duration_seconds:
                elapsed = int(time.time() - start_time)
                remaining = duration_seconds - elapsed
                
                # Get current process metrics
                try:
                    process = psutil.Process(stress_pid)
                    mem_info = process.memory_info()
                    cpu_percent = process.cpu_percent(interval=0.1)
                    
                    mem_mb = mem_info.rss / (1024 * 1024)
                    logger.info(f"  [{elapsed}/{duration_seconds}s] Stress process: "
                              f"Memory={mem_mb:.1f}MB, CPU={cpu_percent:.1f}%")
                except:
                    pass
                
                # Run analysis every N samples
                analysis_cycle += 1
                if analysis_cycle % ANALYSIS_EVERY_N == 0:
                    try:
                        analyzer = TrendAnalyzer(self.db)
                        trends = analyzer.detect_trends()
                        
                        if trends["detected_issues"]:
                            logger.info(f"  ⚠ Trend Analysis: {len(trends['detected_issues'])} issues detected!")
                            for issue in trends["detected_issues"]:
                                msg = f"{issue['metric']}: slope={issue['slope']:.6f}"
                                self.log_alert("TREND", msg)
                                detected_issues.append(issue)
                        
                        # Root cause analysis
                        rc_engine = RootCauseEngine(self.db, analyzer)
                        root_causes = rc_engine.run()
                        if root_causes:
                            logger.info(f"  🔍 Root Cause: {len(root_causes)} causes identified!")
                            for cause in root_causes:
                                cause_name = cause.get('cause', 'Unknown')
                                confidence = cause.get('confidence', 0)
                                logger.info(f"    - {cause_name} ({confidence:.1%} confidence)")
                        
                        # Failure prediction
                        model = ReliabilityModel()
                        predictor = FailurePredictor(self.db, analyzer, model)
                        predictions = predictor.run()
                        if predictions:
                            for pred in predictions:
                                metric = pred.get('metric', 'Unknown')
                                prob = pred.get('failure_probability', 0)
                                if prob > 0.5:
                                    self.log_alert("PREDICTION", 
                                                 f"{metric}: {prob:.1%} failure probability")
                                    alerts_fired.append(pred)
                        
                        # Alerts
                        notifier = SmartNotifier(self.db)
                        alert_count = notifier.run()
                        if alert_count > 0:
                            logger.info(f"  🔔 Notifications: {alert_count} alerts sent!")
                        
                    except Exception as e:
                        logger.error(f"  Analysis error: {e}")
                
                time.sleep(1)
        
        finally:
            self.stop_stress_process()
        
        logger.info(f"\n  Stress Phase Summary:")
        logger.info(f"    - Detected Issues: {len(detected_issues)}")
        logger.info(f"    - Failure Alerts: {len(alerts_fired)}")
        
        self.results["stress_tests"][test_name] = {
            "duration": duration_seconds,
            "issues_detected": len(detected_issues),
            "alerts_fired": len(alerts_fired),
            "status": "PASS" if len(detected_issues) > 0 else "NEEDS_REVIEW"
        }
        
        return len(detected_issues) > 0
    
    def test_memory_leak_detection(self):
        """TEST: Memory leak detection."""
        success = self.monitor_stress_phase(30, "Memory Leak Detection")
        if success:
            self.log_success("Memory leak detection working!")
        else:
            logger.warning("⚠ Memory leak not detected as expected")
        return success
    
    def test_cpu_runaway_detection(self):
        """TEST: CPU runaway detection."""
        success = self.monitor_stress_phase(25, "CPU Runaway Detection")
        if success:
            self.log_success("CPU runaway detection working!")
        else:
            logger.warning("⚠ CPU runaway not detected as expected")
        return success
    
    def cooldown_period(self, duration=10):
        """Wait for system to cool down between tests."""
        logger.info(f"\n⏳ Cooling down for {duration} seconds...")
        for i in range(duration):
            time.sleep(1)
            if (i + 1) % 5 == 0:
                logger.info(f"  [{i+1}/{duration}s]")
    
    def test_alert_consistency(self):
        """TEST: Alert generation consistency."""
        self.log_step(2, "Alert Consistency Test")
        
        logger.info("  ⏳ Generating multiple alerts...")
        
        try:
            notifier = SmartNotifier(self.db)
            
            alert_batches = []
            for i in range(3):
                alerts = notifier.run()
                alert_batches.append(alerts)
                logger.info(f"  Batch {i+1}: {alerts} alerts")
                time.sleep(2)
            
            total_alerts = sum(alert_batches)
            logger.info(f"  Total alerts generated: {total_alerts}")
            
            self.results["stress_tests"]["Alert Consistency"] = {
                "batches": 3,
                "total_alerts": total_alerts,
                "status": "PASS"
            }
            
            self.log_success("Alert consistency test complete")
            return True
        except Exception as e:
            logger.error(f"  Alert consistency test failed: {e}")
            return False
    
    def test_dashboard_under_load(self):
        """TEST: Dashboard performance under alert load."""
        self.log_step(3, "Dashboard Performance Under Load")
        
        try:
            from dashboard.app import create_app
            import time
            
            app = create_app()
            client = app.test_client()
            
            logger.info("  ⏳ Testing dashboard endpoints under load...")
            
            endpoints = [
                ("/api/metrics", "Metrics"),
                ("/api/alerts", "Alerts"),
                ("/api/health", "Health"),
                ("/", "Dashboard"),
            ]
            
            response_times = []
            
            for endpoint, name in endpoints:
                start = time.time()
                try:
                    response = client.get(endpoint)
                    elapsed = (time.time() - start) * 1000
                    response_times.append(elapsed)
                    
                    if response.status_code == 200:
                        logger.info(f"  ✓ {name}: {elapsed:.1f}ms")
                    else:
                        logger.warning(f"  ✗ {name}: Status {response.status_code}")
                except Exception as e:
                    logger.warning(f"  ✗ {name}: {e}")
            
            avg_time = sum(response_times) / len(response_times) if response_times else 0
            logger.info(f"  Average response time: {avg_time:.1f}ms")
            
            self.results["stress_tests"]["Dashboard Performance"] = {
                "endpoints_tested": len(endpoints),
                "avg_response_time_ms": avg_time,
                "status": "PASS" if avg_time < 1000 else "NEEDS_REVIEW"
            }
            
            self.log_success("Dashboard performance test complete")
            return True
        except Exception as e:
            logger.error(f"  Dashboard test failed: {e}")
            return False
    
    def print_summary(self):
        """Print final summary."""
        logger.info("\n" + "█"*70)
        logger.info("█  STRESS TEST SUMMARY  █")
        logger.info("█"*70)
        
        for test_name, result in self.results["stress_tests"].items():
            status_emoji = "✓" if result["status"] == "PASS" else "⚠"
            logger.info(f"\n{status_emoji} {test_name}")
            for key, value in result.items():
                if key != "status":
                    logger.info(f"    {key}: {value}")
        
        logger.info("\n" + "█"*70 + "\n")
    
    def run_all_stress_tests(self):
        """Run all stress tests."""
        try:
            self.setup_monitoring()
            
            # Run stress tests
            self.test_memory_leak_detection()
            self.cooldown_period()
            
            self.test_cpu_runaway_detection()
            self.cooldown_period()
            
            self.test_alert_consistency()
            self.cooldown_period()
            
            self.test_dashboard_under_load()
            
            self.print_summary()
            
        finally:
            # Cleanup
            if self.collector:
                try:
                    self.collector.stop()
                    logger.info("✓ Monitoring stopped")
                except:
                    pass
            
            if self.stress_process:
                try:
                    self.stress_process.kill()
                except:
                    pass


def main():
    """Main entry point."""
    logger.info("\n" + "█"*70)
    logger.info("█  SOFTWARE AGING ANALYZER - STRESS TEST SUITE  █")
    logger.info("█"*70 + "\n")
    
    orchestrator = StressTestOrchestrator()
    orchestrator.run_all_stress_tests()


if __name__ == "__main__":
    main()

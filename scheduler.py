"""
Automated scheduler for regular updates and predictions
Can be run as a cron job or scheduled task
"""

import schedule
import time
from datetime import datetime
import logging
from main import NBAPropSystem
from utils import clean_old_data, check_data_freshness

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self):
        self.system = NBAPropSystem()
    
    def daily_update_job(self):
        """Daily job to update data"""
        logger.info("=" * 60)
        logger.info("DAILY UPDATE JOB STARTED")
        logger.info("=" * 60)
        
        try:
            # Update player stats and odds
            success = self.system.update_data()
            
            if success:
                logger.info("✓ Daily update completed successfully")
            else:
                logger.error("✗ Daily update failed")
        
        except Exception as e:
            logger.error(f"Daily update job failed: {e}")
    
    def prediction_job(self):
        """Job to generate predictions"""
        logger.info("=" * 60)
        logger.info("PREDICTION JOB STARTED")
        logger.info("=" * 60)
        
        try:
            pred_df = self.system.make_predictions()
            
            if pred_df is not None and not pred_df.empty:
                logger.info(f"✓ Generated {len(pred_df)} predictions")
                self.system.display_predictions(pred_df)
            else:
                logger.info("No high-confidence predictions available")
        
        except Exception as e:
            logger.error(f"Prediction job failed: {e}")
    
    def weekly_training_job(self):
        """Weekly job to retrain model"""
        logger.info("=" * 60)
        logger.info("WEEKLY TRAINING JOB STARTED")
        logger.info("=" * 60)
        
        try:
            success = self.system.train_model()
            
            if success:
                logger.info("✓ Model retraining completed")
            else:
                logger.error("✗ Model retraining failed")
        
        except Exception as e:
            logger.error(f"Training job failed: {e}")
    
    def cleanup_job(self):
        """Weekly cleanup of old data"""
        logger.info("Running cleanup job...")
        
        try:
            clean_old_data(days_to_keep=30)
            logger.info("✓ Cleanup completed")
        
        except Exception as e:
            logger.error(f"Cleanup job failed: {e}")
    
    def health_check(self):
        """Check system health"""
        logger.info("Running health check...")
        check_data_freshness()


def run_scheduler(mode='dev'):
    """
    Run the scheduler
    
    Modes:
    - dev: Quick schedule for testing (minutes)
    - prod: Production schedule (hours/days)
    """
    scheduler = Scheduler()
    
    if mode == 'dev':
        # Development schedule - for testing
        logger.info("Running in DEVELOPMENT mode (quick schedule)")
        
        schedule.every(5).minutes.do(scheduler.daily_update_job)
        schedule.every(10).minutes.do(scheduler.prediction_job)
        schedule.every(30).minutes.do(scheduler.health_check)
    
    else:
        # Production schedule
        logger.info("Running in PRODUCTION mode")
        
        # Update data every morning at 8 AM
        schedule.every().day.at("08:00").do(scheduler.daily_update_job)
        
        # Generate predictions at 10 AM and 5 PM
        schedule.every().day.at("10:00").do(scheduler.prediction_job)
        schedule.every().day.at("17:00").do(scheduler.prediction_job)
        
        # Retrain model every Sunday at 2 AM
        schedule.every().sunday.at("02:00").do(scheduler.weekly_training_job)
        
        # Cleanup old data every Sunday at 3 AM
        schedule.every().sunday.at("03:00").do(scheduler.cleanup_job)
        
        # Health check twice daily
        schedule.every().day.at("12:00").do(scheduler.health_check)
        schedule.every().day.at("20:00").do(scheduler.health_check)
    
    logger.info("Scheduler started. Press Ctrl+C to stop.")
    logger.info("Scheduled jobs:")
    for job in schedule.get_jobs():
        logger.info(f"  - {job}")
    
    # Run indefinitely
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    except KeyboardInterrupt:
        logger.info("\nScheduler stopped by user")


if __name__ == "__main__":
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else 'prod'
    
    if mode not in ['dev', 'prod']:
        print("Usage: python scheduler.py [dev|prod]")
        print("  dev  - Quick schedule for testing")
        print("  prod - Production schedule")
        sys.exit(1)
    
    run_scheduler(mode)

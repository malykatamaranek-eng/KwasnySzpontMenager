"""Celery tasks for account processing."""
import asyncio
from typing import Dict, Any, Optional
from celery import Task
import structlog
from playwright.async_api import async_playwright
from src.task_system.celery_app import celery_app
from src.db.database import AsyncSessionLocal
from src.db import crud
from src.db.models import AccountStatus
from src.modules.proxy_manager.manager import ProductionProxyManager
from src.modules.email_discovery.detector import LiveEmailDiscovery
from src.modules.auth_validator.validator import AccountValidator
from src.modules.email_processor.imap_client import AsyncIMAPProcessor
from src.modules.facebook_automation.two_fa_handler import FacebookTwoFactorHandler
from src.modules.facebook_automation.reset_password import FacebookPasswordResetter
from src.core.security import decrypt_password
from src.core.config import settings
import redis

logger = structlog.get_logger()

# Redis client for pub/sub
redis_client = redis.from_url(settings.REDIS_URL)


class CallbackTask(Task):
    """Base task with callbacks."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Success callback."""
        logger.info("task_success", task_id=task_id, result=retval)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Failure callback."""
        logger.error("task_failure", task_id=task_id, error=str(exc))
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Retry callback."""
        logger.warning("task_retry", task_id=task_id, error=str(exc))


def publish_log(account_id: int, action: str, status: str, message: str):
    """Publish log to Redis for real-time updates."""
    try:
        log_data = {
            "account_id": account_id,
            "action": action,
            "status": status,
            "message": message
        }
        redis_client.publish(f"account:{account_id}:logs", str(log_data))
    except Exception as e:
        logger.warning("redis_publish_failed", error=str(e))


@celery_app.task(bind=True, base=CallbackTask, max_retries=3)
def process_account_task(self, account_id: int, action: str = "login") -> Dict[str, Any]:
    """
    Process account automation task.
    
    Args:
        account_id: Account ID to process
        action: Action to perform (login, reset_password, verify_2fa)
        
    Returns:
        Dict with task result
    """
    return asyncio.run(async_process_account(self, account_id, action))


async def async_process_account(task: Task, account_id: int, action: str) -> Dict[str, Any]:
    """
    Async implementation of account processing.
    
    Args:
        task: Celery task instance
        account_id: Account ID
        action: Action to perform
        
    Returns:
        Dict with result
    """
    logger.info("task_start", task_id=task.request.id, account_id=account_id, action=action)
    publish_log(account_id, action, "started", f"Starting {action}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Step 1: Get account
            account = await crud.get_account(db, account_id)
            if not account:
                error_msg = f"Account {account_id} not found"
                logger.error("account_not_found", account_id=account_id)
                return {"success": False, "error": error_msg}
            
            # Update status to processing
            await crud.update_account_status(db, account_id, AccountStatus.PROCESSING)
            await crud.create_log(db, account_id, action, "processing", f"Processing {action}")
            publish_log(account_id, action, "processing", "Account processing started")
            
            # Step 2: Assign proxy
            proxy_manager = ProductionProxyManager(db)
            proxy = await proxy_manager.assign_proxy_to_account(account_id)
            proxy_url = proxy.url if proxy else None
            
            logger.info("proxy_assigned", account_id=account_id, proxy_id=proxy.id if proxy else None)
            publish_log(account_id, action, "info", f"Proxy assigned: {proxy.host if proxy else 'none'}")
            
            # Step 3: Login to email provider
            password = decrypt_password(account.encrypted_password)
            
            async with LiveEmailDiscovery() as discovery:
                await discovery.initialize()
                
                logger.info("email_login_start", account_id=account_id)
                publish_log(account_id, action, "info", "Logging into email provider")
                
                login_result = await discovery.login_to_provider(
                    account.email,
                    password,
                    proxy_url
                )
                
                if not login_result["success"]:
                    raise Exception("Email login failed")
                
                logger.info("email_login_success", account_id=account_id)
                publish_log(account_id, action, "success", "Email login successful")
                
                # Step 4: Connect to IMAP
                imap_config = login_result["imap_config"]
                imap_client = AsyncIMAPProcessor(
                    host=imap_config["host"],
                    port=imap_config["port"],
                    email=account.email,
                    password=password,
                    use_ssl=True
                )
                
                await imap_client.connect()
                logger.info("imap_connected", account_id=account_id)
                publish_log(account_id, action, "info", "IMAP connected")
                
                # Step 5: Perform action on Facebook
                result = await perform_facebook_action(
                    action,
                    account,
                    password,
                    imap_client,
                    proxy_url,
                    db
                )
                
                await imap_client.disconnect()
                
                # Step 6: Save session
                if result.get("access_token"):
                    await crud.create_session(
                        db,
                        account_id,
                        cookies=result.get("cookies"),
                        access_token=result["access_token"]
                    )
                    logger.info("session_saved", account_id=account_id)
                    publish_log(account_id, action, "success", "Session saved")
                
                # Step 7: Update status
                if result["success"]:
                    await crud.update_account_status(db, account_id, AccountStatus.COMPLETED)
                    await crud.create_log(db, account_id, action, "completed", "Task completed successfully")
                    publish_log(account_id, action, "completed", "Task completed successfully")
                else:
                    await crud.update_account_status(db, account_id, AccountStatus.FAILED)
                    await crud.create_log(db, account_id, action, "failed", result.get("error", "Unknown error"))
                    publish_log(account_id, action, "failed", result.get("error", "Unknown error"))
                
                logger.info("task_completed", task_id=task.request.id, account_id=account_id, success=result["success"])
                return result
                
        except Exception as e:
            error_msg = f"Task failed: {str(e)}"
            logger.error("task_error", task_id=task.request.id, account_id=account_id, error=str(e))
            
            await crud.update_account_status(db, account_id, AccountStatus.ERROR)
            await crud.create_log(db, account_id, action, "error", error_msg)
            publish_log(account_id, action, "error", error_msg)
            
            # Retry with exponential backoff
            retry_countdown = 2 ** task.request.retries * 60
            raise task.retry(exc=e, countdown=retry_countdown)


async def perform_facebook_action(
    action: str,
    account,
    password: str,
    imap_client: AsyncIMAPProcessor,
    proxy_url: Optional[str],
    db
) -> Dict[str, Any]:
    """
    Perform Facebook automation action.
    
    Args:
        action: Action to perform
        account: Account object
        password: Decrypted password
        imap_client: IMAP client
        proxy_url: Proxy URL
        db: Database session
        
    Returns:
        Dict with result
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=settings.PLAYWRIGHT_HEADLESS,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context_options = {
            "user_agent": FacebookTwoFactorHandler.MOBILE_USER_AGENT,
            "viewport": {"width": 375, "height": 812},
            "locale": "pl-PL"
        }
        
        if proxy_url:
            context_options["proxy"] = {"server": proxy_url}
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        try:
            if action == "login" or action == "verify_2fa":
                # Facebook login with 2FA
                two_fa_handler = FacebookTwoFactorHandler(imap_client)
                access_token = await two_fa_handler.login_with_2fa(
                    page,
                    account.email,
                    password
                )
                
                cookies = await context.cookies()
                
                return {
                    "success": True,
                    "action": action,
                    "access_token": access_token,
                    "cookies": cookies
                }
                
            elif action == "reset_password":
                # Facebook password reset
                new_password = password  # Use same password or generate new one
                password_resetter = FacebookPasswordResetter(imap_client)
                success = await password_resetter.reset_password(
                    page,
                    account.email,
                    new_password
                )
                
                return {
                    "success": success,
                    "action": action
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            logger.error("facebook_action_failed", action=action, error=str(e))
            return {
                "success": False,
                "action": action,
                "error": str(e)
            }
        finally:
            await page.close()
            await context.close()
            await browser.close()


@celery_app.task(bind=True, base=CallbackTask)
def validate_account_task(self, account_id: int) -> Dict[str, Any]:
    """
    Validate account credentials.
    
    Args:
        account_id: Account ID to validate
        
    Returns:
        Dict with validation result
    """
    return asyncio.run(async_validate_account(account_id))


async def async_validate_account(account_id: int) -> Dict[str, Any]:
    """
    Async implementation of account validation.
    
    Args:
        account_id: Account ID
        
    Returns:
        Dict with result
    """
    async with AsyncSessionLocal() as db:
        account = await crud.get_account(db, account_id)
        if not account:
            return {"success": False, "error": "Account not found"}
        
        validator = AccountValidator(db)
        result = await validator.validate_account(account)
        return result


@celery_app.task(bind=True, base=CallbackTask)
def test_all_proxies_task(self) -> Dict[str, Any]:
    """
    Test all proxies in the database.
    
    Returns:
        Dict with test results
    """
    return asyncio.run(async_test_all_proxies())


async def async_test_all_proxies() -> Dict[str, Any]:
    """
    Async implementation of proxy testing.
    
    Returns:
        Dict with results
    """
    async with AsyncSessionLocal() as db:
        proxy_manager = ProductionProxyManager(db)
        results = await proxy_manager.test_all_proxies()
        
        return {
            "success": True,
            "tested": len(results),
            "results": results
        }


@celery_app.task(bind=True, base=CallbackTask)
def batch_process_accounts_task(self, account_ids: list[int], action: str = "login") -> Dict[str, Any]:
    """
    Process multiple accounts in batch.
    
    Args:
        account_ids: List of account IDs
        action: Action to perform
        
    Returns:
        Dict with results
    """
    results = []
    for account_id in account_ids:
        result = process_account_task.delay(account_id, action)
        results.append({
            "account_id": account_id,
            "task_id": result.id
        })
    
    return {
        "success": True,
        "tasks_started": len(results),
        "results": results
    }

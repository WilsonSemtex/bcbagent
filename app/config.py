"""
应用配置管理
支持动态切换 LLM 模型

优化:
- [#22] 配置中心：支持运行时热更新，无需重启
"""
import os
import sqlite3
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

AUTO_MODEL_ID = "auto"
AUTO_MODEL_TARGET = "deepseek-v4-flash"
AUTO_MODEL_FALLBACK_CHAIN = (
    "deepseek-v4-flash",
)
MODEL_FALLBACK_CHAINS = {
    AUTO_MODEL_ID: AUTO_MODEL_FALLBACK_CHAIN,
}

# 显式指定 .env 路径（项目根目录），避免 uvicorn 启动目录不是项目根时找不到 .env
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if not load_dotenv(_env_path):
    load_dotenv()  # 回退：尝试从 cwd 加载

# 可用的 LLM 模型列表（仅 DeepSeek V4 Flash）
AVAILABLE_MODELS = [
    {"id": "deepseek-v4-flash", "name": "Deepseek-V4-Flash", "desc": "DeepSeek V4 Flash，DeepSeek 官方 API"},
]

# 支持图片分析的视觉模型列表
VISION_MODELS = {"glm-4v-plus", "glm-4v", "glm-4v-flash", "glm-4.6v-flash"}
# 默认视觉模型（当用户上传图片时自动切换；可通过 VISION_MODEL 环境变量覆盖）
DEFAULT_VISION_MODEL = "glm-4.6v-flash"
# 视觉模型配置（env 可覆盖：VISION_MODEL / VISION_API_KEY / VISION_BASE_URL）
# 无论当前选用什么模型，视觉理解始终走智谱 AI（embedding 与视觉共用智谱 key）
VISION_MODEL: str = os.getenv("VISION_MODEL", DEFAULT_VISION_MODEL)
VISION_API_KEY: str = os.getenv("VISION_API_KEY", os.getenv("LLM_API_KEY", ""))
VISION_BASE_URL: str = os.getenv("VISION_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

# 快速模型列表（用于意图路由，加速简单问题的响应）
FAST_MODELS = {"deepseek-v4-flash"}

# 走 DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL 的模型（本版本为 DeepSeek 官方 API）
VOLCENGINE_MODELS = {
    "deepseek-v4-flash",
}

# 火山方舟标准 API 模型（本版本不使用）
ARK_STANDARD_MODELS = set()

# DeepSeek 模型列表（走 DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL）
DEEPSEEK_MODELS = {"deepseek-v4-flash"}

# 千问模型列表（本版本不使用）
QWEN_MODELS = set()

# MiMo模型列表（本版本不使用）
MIMO_MODELS = set()

# Kimi模型列表（本版本不使用）
KIMI_MODELS = set()

# GLM模型列表（本版本不使用）
GLM_MODELS = set()


class Settings:
    """应用配置（[#22] 支持运行时热更新）"""

    # LLM 默认配置（阿里云百炼平台，兼容模式代理多家模型）
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    # 新默认值为 Auto。兼容旧部署：若 .env 仍保留旧默认 DeepSeek，则自动迁移到 Auto；
    # 用户仍可在前端显式选择 DeepSeek。
    _configured_model = os.getenv("LLM_MODEL", AUTO_MODEL_ID).strip()
    if _configured_model in ("", "DeepSeek-V4-Flash", "deepseek-v4-flash"):
        _configured_model = AUTO_MODEL_ID
    _valid_model_ids = {model["id"] for model in AVAILABLE_MODELS}
    LLM_MODEL: str = _configured_model if _configured_model in _valid_model_ids else AUTO_MODEL_ID

    # LLM 备用配置（主Key失效时自动切换）
    LLM_API_KEY_BACKUP: str = os.getenv("LLM_API_KEY_BACKUP", "")
    LLM_BASE_URL_BACKUP: str = os.getenv("LLM_BASE_URL_BACKUP", "")

    # DeepSeek / 豆包 独立配置（火山引擎Ark）
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", os.getenv("LLM_API_KEY", ""))
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3")

    # 火山方舟标准 API（Doubao-Seed-2.1-Pro 等不支持 Coding Plan 的模型）
    ARK_API_KEY: str = os.getenv("ARK_API_KEY", "")
    ARK_BASE_URL: str = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

    # 千问独立配置（阿里云DashScope）
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", os.getenv("DASHSCOPE_API_KEY", ""))
    QWEN_BASE_URL: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    # MiMo独立配置（小米）
    MIMO_API_KEY: str = os.getenv("MIMO_API_KEY", "")
    MIMO_BASE_URL: str = os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1")

    # Kimi独立配置（Moonshot AI）
    MOONSHOT_API_KEY: str = os.getenv("MOONSHOT_API_KEY", "")
    MOONSHOT_BASE_URL: str = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")

    # GLM独立配置（阿里云百炼平台，走 LLM_API_KEY/LLM_BASE_URL）
    GLM_API_KEY: str = os.getenv("GLM_API_KEY", os.getenv("LLM_API_KEY", ""))
    GLM_BASE_URL: str = os.getenv("GLM_BASE_URL", os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))

    # Embedding 模型
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "embedding-3")
    # [#12] Embedding 独立 API Key（如未设置则复用 LLM_API_KEY）
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", os.getenv("LLM_API_KEY", ""))
    # Embedding API Base URL（如未设置则复用 LLM_BASE_URL）
    EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL", os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"))

    # 应用配置
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))

    # Feishu web SSO. The App Secret is used server-side only.
    FEISHU_APP_ID: str = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET: str = os.getenv("FEISHU_APP_SECRET", "")
    FEISHU_REDIRECT_URI: str = os.getenv("FEISHU_REDIRECT_URI", "")
    FEISHU_ACCOUNT_MAP_JSON: str = os.getenv("FEISHU_ACCOUNT_MAP_JSON", "")
    FEISHU_SESSION_COOKIE: str = os.getenv("FEISHU_SESSION_COOKIE", "sbagent_session")
    # Comma-separated internal usernames with upload/delete access to every
    # knowledge base, including digital-teacher knowledge bases.
    FULL_KB_ADMIN_USERNAMES: str = os.getenv(
        "FULL_KB_ADMIN_USERNAMES", "hustroboconadmin"
    )
    # Feishu organization directory synchronization. ``tenant_key`` may be
    # omitted after at least one successful SSO login because it can then be
    # discovered from the existing binding database.
    FEISHU_TENANT_KEY: str = os.getenv("FEISHU_TENANT_KEY", "")
    FEISHU_CONTACT_SYNC_ENABLED: bool = os.getenv(
        "FEISHU_CONTACT_SYNC_ENABLED", "true"
    ).strip().lower() in {"1", "true", "yes", "on"}
    FEISHU_CONTACT_FULL_SCOPE_CONFIRMED: bool = os.getenv(
        "FEISHU_CONTACT_FULL_SCOPE_CONFIRMED", "false"
    ).strip().lower() in {"1", "true", "yes", "on"}
    FEISHU_CONTACTS_DB: str = os.getenv("FEISHU_CONTACTS_DB", "")

    # SQM demonstration entry. This is intentionally a fixed shared account,
    # not per-user SSO. The entry key is independent from the account password
    # and the application's JWT signing secret, so it can be rotated safely.
    SQM_DEMO_LOGIN_ENABLED: bool = os.getenv(
        "SQM_DEMO_LOGIN_ENABLED", "false"
    ).strip().lower() in {"1", "true", "yes", "on"}
    SQM_DEMO_USERNAME: str = os.getenv("SQM_DEMO_USERNAME", "jiangxy")
    SQM_DEMO_ENTRY_KEY: str = os.getenv("SQM_DEMO_ENTRY_KEY", "")
    SQM_DEMO_RETENTION_DAYS: int = int(
        os.getenv("SQM_DEMO_RETENTION_DAYS", "7")
    )
    SQM_DEMO_SESSION_COOKIE: str = os.getenv(
        "SQM_DEMO_SESSION_COOKIE",
        os.getenv("FEISHU_SESSION_COOKIE", "sbagent_session"),
    )

    # 数据目录
    DATA_DIR: str = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
    DOCUMENTS_DIR: str = os.getenv("DOCUMENTS_DIR", os.path.join(DATA_DIR, "documents"))
    CHROMA_DIR: str = os.getenv("CHROMA_DIR", os.path.join(DATA_DIR, "chroma_db"))
    EMPLOYEES_FILE: str = os.getenv("EMPLOYEES_FILE", os.path.join(DATA_DIR, "employees.json"))

    # [#22] 配置变更回调列表
    _change_callbacks = []

    @classmethod
    def on_change(cls, callback):
        """注册配置变更回调"""
        cls._change_callbacks.append(callback)

    @classmethod
    def notify_change(cls, key: str, old_value, new_value):
        """通知配置变更"""
        for cb in cls._change_callbacks:
            try:
                cb(key, old_value, new_value)
            except Exception as e:
                logger.warning(f"配置变更回调异常: {e}")


settings = Settings()


# 模型选择按账号持久化。不能直接修改 settings.LLM_MODEL：Uvicorn 多 worker
# 环境下每个进程都有自己的内存副本，而且不同账号会互相覆盖。
_user_model_lock = threading.RLock()
_active_model: ContextVar[str | None] = ContextVar("active_model", default=None)
_USER_MODEL_DB = Path(settings.DATA_DIR) / "user_models.sqlite3"


def _open_user_model_db():
    _USER_MODEL_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_USER_MODEL_DB), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS user_models "
        "(username TEXT PRIMARY KEY, model_id TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    return conn


def get_user_model(username: str) -> str:
    """获取账号独立的模型选择；未设置时使用 Auto。"""
    if not username:
        return AUTO_MODEL_ID
    with _user_model_lock:
        conn = None
        try:
            conn = _open_user_model_db()
            row = conn.execute(
                "SELECT model_id FROM user_models WHERE username = ?", (username,)
            ).fetchone()
            model_id = row[0] if row else AUTO_MODEL_ID
        except Exception as exc:
            logger.warning(f"读取用户模型配置失败: {exc}")
            model_id = AUTO_MODEL_ID
        finally:
            if conn is not None:
                conn.close()
    valid_ids = {m["id"] for m in AVAILABLE_MODELS}
    return model_id if model_id in valid_ids else AUTO_MODEL_ID


def set_user_model(username: str, model_id: str) -> bool:
    """持久化账号独立模型选择，供所有 worker 在每次请求时读取。"""
    if not username or model_id not in {m["id"] for m in AVAILABLE_MODELS}:
        return False
    with _user_model_lock:
        conn = None
        try:
            conn = _open_user_model_db()
            conn.execute(
                "INSERT INTO user_models(username, model_id, updated_at) VALUES(?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(username) DO UPDATE SET model_id=excluded.model_id, updated_at=CURRENT_TIMESTAMP",
                (username, model_id),
            )
            conn.commit()
        except Exception as exc:
            logger.error(f"保存用户模型配置失败: {exc}")
            return False
        finally:
            if conn is not None:
                conn.close()
    logger.info(f"用户模型切换: {username} -> {model_id}")
    return True


@contextmanager
def use_model(model_id: str):
    """为当前请求绑定模型，ContextVar 可隔离同一 worker 内的并发账号。"""
    token = _active_model.set(model_id)
    try:
        yield
    finally:
        _active_model.reset(token)


def get_active_model() -> str:
    """Agent 内部使用的当前请求模型。"""
    return _active_model.get() or settings.LLM_MODEL


def resolve_model_id(model_id: str) -> str:
    """将前端选择值解析为实际调用的模型ID。"""
    return AUTO_MODEL_TARGET if model_id == AUTO_MODEL_ID else model_id


def is_model_quota_error(error) -> bool:
    """识别上游模型的额度、余额和限流错误，供 Auto 模式静默容灾。"""
    parts = [str(error), repr(error)]
    response = getattr(error, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        if status_code is not None:
            parts.append(f"http status {status_code}")
        try:
            parts.append(str(response.text))
        except Exception:
            pass
        try:
            parts.append(str(response.json()))
        except Exception:
            pass

    error_text = " ".join(parts).lower()
    markers = (
        "insufficient_quota",
        "insufficient quota",
        "quota exceeded",
        "quota_exceeded",
        "quota exhausted",
        "quota_exhausted",
        "quota not enough",
        "exceeded your current quota",
        "balance is insufficient",
        "insufficient balance",
        "insufficient funds",
        "credit balance",
        "billing hard limit",
        "resource exhausted",
        "resource_exhausted",
        "rate limit exceeded",
        "rate_limit_exceeded",
        "too many requests",
        "arrearage",
        "allocationquota.freetieronly",
        "throttling.allocationquota",
        "throttling.ratequota",
        "prepaidbilloverdue",
        "postpaidbilloverdue",
        "commoditynotpurchased",
        "allocated quota exceeded",
        "hour allocated quota exceeded",
        "week allocated quota exceeded",
        "month allocated quota exceeded",
        "usage allocated quota exceeded",
        "http status 429",
        "http 429",
        "status code 429",
        "status_code=429",
        "余额不足",
        "额度不足",
        "配额不足",
        "账户余额不足",
        "账号欠费",
        "账户欠费",
    )
    return any(marker in error_text for marker in markers)


def get_effective_model(username: str = None) -> str:
    """获取当前实际调用的模型ID（Auto 当前解析为 GLM-5.2）。"""
    selected = get_user_model(username) if username else get_active_model()
    return resolve_model_id(selected)


def set_current_model(model_id: str) -> bool:
    """动态切换当前使用的模型"""
    valid_ids = [m["id"] for m in AVAILABLE_MODELS]
    if model_id in valid_ids:
        old = settings.LLM_MODEL
        settings.LLM_MODEL = model_id
        # 重置 Agent 单例，让下次对话使用新模型
        from app.agent.core import reset_agent
        reset_agent()
        # [#22] 通知配置变更
        Settings.notify_change("LLM_MODEL", old, model_id)
        logger.info(f"模型切换: {old} → {model_id}")
        return True
    return False


def get_current_model() -> str:
    """获取当前使用的模型ID"""
    return settings.LLM_MODEL

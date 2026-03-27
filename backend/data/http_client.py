"""
统一 HTTP 客户端，支持重试、超时和并发控制
"""
import httpx
import asyncio
import logging
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)


class RetryConfig:
    """重试配置"""
    def __init__(
        self,
        max_attempts: int = 3,
        min_wait: float = 1.0,
        max_wait: float = 30.0,
        exponential_base: float = 2.0
    ):
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.exponential_base = exponential_base


class DataFetcherClient:
    """
    统一的异步 HTTP 客户端

    特性:
    - 并发控制（信号量）
    - 指数退避重试
    - 统一超时配置
    - 连接池管理
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        connect_timeout: float = 5.0,
        read_timeout: float = 15.0,
        max_connections: int = 20,
        retry_config: Optional[RetryConfig] = None
    ):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.retry_config = retry_config or RetryConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=10.0,
            pool=5.0
        )
        self._limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=10
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """懒加载客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                limits=self._limits,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
            )
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _calculate_wait_time(self, attempt: int) -> float:
        """计算重试等待时间（指数退避）"""
        wait = self.retry_config.min_wait * (self.retry_config.exponential_base ** attempt)
        return min(wait, self.retry_config.max_wait)

    def _should_retry(self, exception: Exception) -> bool:
        """判断是否应该重试"""
        return isinstance(exception, (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError
        ))

    async def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None
    ) -> httpx.Response:
        """
        GET 请求，带重试和并发控制

        Args:
            url: 请求 URL
            params: 查询参数
            headers: 额外请求头
            timeout: 单次请求超时（覆盖默认值）

        Returns:
            httpx.Response

        Raises:
            httpx.HTTPError: 请求失败（重试后仍然失败）
        """
        async with self.semaphore:
            client = await self._get_client()
            last_exception = None

            for attempt in range(self.retry_config.max_attempts):
                try:
                    kwargs: Dict[str, Any] = {}
                    if params:
                        kwargs['params'] = params
                    if headers:
                        kwargs['headers'] = headers
                    if timeout:
                        kwargs['timeout'] = timeout

                    response = await client.get(url, **kwargs)
                    response.raise_for_status()
                    return response

                except Exception as e:
                    last_exception = e

                    if not self._should_retry(e):
                        logger.warning(f"Request failed (non-retryable): {url} - {e}")
                        raise

                    if attempt < self.retry_config.max_attempts - 1:
                        wait_time = self._calculate_wait_time(attempt)
                        logger.warning(
                            f"Request failed, retrying in {wait_time:.1f}s "
                            f"(attempt {attempt + 1}/{self.retry_config.max_attempts}): {url} - {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Request failed after {self.retry_config.max_attempts} attempts: {url}")

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state: no response and no exception")

    async def get_json(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None,
        default: Any = None
    ) -> Any:
        """
        GET 请求并解析 JSON

        Args:
            default: 请求失败时的默认返回值

        Returns:
            解析后的 JSON 数据，或 default
        """
        try:
            response = await self.get(url, params, headers, timeout)
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch JSON from {url}: {e}")
            if default is not None:
                return default
            raise

    async def get_text(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None,
        default: Optional[str] = None
    ) -> str:
        """
        GET 请求并返回文本

        Args:
            default: 请求失败时的默认返回值

        Returns:
            响应文本，或 default
        """
        try:
            response = await self.get(url, params, headers, timeout)
            return response.text
        except Exception as e:
            logger.warning(f"Failed to fetch text from {url}: {e}")
            if default is not None:
                return default
            raise


# 全局客户端实例（懒加载）
_global_client: Optional[DataFetcherClient] = None


def get_http_client() -> DataFetcherClient:
    """获取全局 HTTP 客户端实例"""
    global _global_client
    if _global_client is None:
        _global_client = DataFetcherClient()
    return _global_client


async def cleanup_http_client():
    """清理全局客户端"""
    global _global_client
    if _global_client:
        await _global_client.close()
        _global_client = None

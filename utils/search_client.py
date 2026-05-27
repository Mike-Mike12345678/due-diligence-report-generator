"""Tavily 搜索 API 客户端封装"""

import httpx
from rich.console import Console

console = Console()

TAVILY_ENDPOINT = "https://api.tavily.com/search"


class SearchClient:

    def __init__(self, config: dict):
        search_cfg = config.get("search", {})
        pipeline_cfg = config.get("pipeline", {})

        self.api_key = search_cfg.get("api_key", "")
        self.default_max_results = search_cfg.get("max_results", 5)
        self.default_search_depth = search_cfg.get("search_depth", "basic")
        self.include_raw_content = search_cfg.get("include_raw_content", False)
        self.timeout = search_cfg.get("timeout", 30)
        self.max_retries = pipeline_cfg.get("retry_on_failure", 2)
        self.verbose = pipeline_cfg.get("verbose", False)

    def search(self, query: str, max_results: int = None, search_depth: str = None) -> list[dict]:
        if not self.api_key:
            console.print("[red]错误: 未配置 Tavily API Key[/red]")
            return []

        max_results = max_results or self.default_max_results
        search_depth = search_depth or self.default_search_depth

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_raw_content": self.include_raw_content,
        }

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if self.verbose:
                    console.print(f"[dim]搜索中 (第{attempt}次): {query}[/dim]")

                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(TAVILY_ENDPOINT, json=payload)
                    resp.raise_for_status()

                data = resp.json()
                results = []
                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "raw_content": item.get("raw_content", ""),
                    })

                if self.verbose:
                    console.print(f"[green]搜索完成，获取 {len(results)} 条结果[/green]")

                return results

            except httpx.TimeoutException:
                last_error = f"请求超时 ({self.timeout}s)"
                console.print(f"[yellow]搜索超时，正在重试 ({attempt}/{self.max_retries})...[/yellow]")
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                console.print(f"[red]搜索请求失败: {last_error}[/red]")
                break
            except httpx.RequestError as e:
                last_error = str(e)
                console.print(f"[yellow]网络错误，正在重试 ({attempt}/{self.max_retries})...[/yellow]")
            except Exception as e:
                last_error = str(e)
                console.print(f"[red]未知错误: {last_error}[/red]")
                break

        console.print(f"[red]搜索失败: {last_error}[/red]")
        return []

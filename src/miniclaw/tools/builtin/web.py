"""
MiniClaw - 网络工具

web_search: DuckDuckGo 搜索（免费无需 API Key）
http_request: 通用 HTTP 请求

对应 PRD：F3 工具系统
"""

import httpx

from miniclaw.tools.registry import tool


@tool(
    description="使用搜索引擎搜索信息。返回搜索结果的标题、链接和摘要。",
    risk_level="low",
)
async def web_search(query: str) -> str:
    """搜索网页信息"""
    try:
        # 使用 DuckDuckGo HTML 搜索（免费，无需 API Key）
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "MiniClaw/0.1.0"},
            )
            response.raise_for_status()

            # 简单解析搜索结果（从 HTML 提取）
            text = response.text
            results: list[str] = []

            # 提取结果块
            import re

            # 匹配搜索结果链接和标题
            links = re.findall(
                r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                text,
            )
            snippets = re.findall(
                r'class="result__snippet"[^>]*>(.*?)</span>',
                text,
                re.DOTALL,
            )

            for i, (url, title) in enumerate(links[:5]):
                # 清理 HTML 标签
                clean_title = re.sub(r"<[^>]+>", "", title).strip()
                clean_snippet = ""
                if i < len(snippets):
                    clean_snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip()
                results.append(f"{i + 1}. [{clean_title}]({url})\n   {clean_snippet}")

            if results:
                return "\n\n".join(results)
            return f"未找到关于 '{query}' 的搜索结果"

    except Exception as e:
        return f"搜索失败: {e}"


@tool(
    description="发送 HTTP 请求并返回响应。支持 GET 和 POST 方法。",
    risk_level="low",
)
async def http_request(url: str, method: str = "GET") -> str:
    """发送 HTTP 请求"""
    try:
        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True
        ) as client:
            if method.upper() == "POST":
                response = await client.post(url)
            else:
                response = await client.get(url)
            response.raise_for_status()
            # 截断过长的响应
            text = response.text
            if len(text) > 5000:
                text = text[:5000] + f"\n\n... (内容已截断，共 {len(response.text)} 字符)"
            return text
    except Exception as e:
        return f"HTTP 请求失败: {e}"

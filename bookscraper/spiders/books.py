import os
import time
import logging
import requests

import scrapy
from urllib.parse import urljoin

from bookscraper.items import BookscraperItem


class BooksSpider(scrapy.Spider):
    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.perf_counter()

        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    def _notify_slack(self, message):
        """Slackへ通知する"""

        if not self.slack_webhook_url:
            self.logger.warning(
                "SLACK_WEBHOOK_URLが設定されていないため、"
                "Slack通知をスキップします。"
            )
            return
        
        try:
            response = requests.post(
                self.slack_webhook_url,
                json={"text": message},
                timeout=10,
            )
            response.raise_for_status()

        except requests.RequestException as e:
            self.logger.error(
                f"Slack通知に失敗しました: {e}"
            )

    def notify_error(self, message):
        """エラーをログに出力し、同じ内容をSlackへ通知する"""

        self.logger.error(message)
        self._notify_slack(message)


    def parse(self, response):
        try:
        # 一覧ページから詳細ページへのリンクを取得
            for book in response.css("article.product_pod"):
                detail_url = book.css("h3 a::attr(href)").get()

                if detail_url:
                    detail_url = urljoin(
                        response.url,
                        detail_url
                    )

                    yield scrapy.Request(
                        detail_url,
                        callback=self.parse_detail
                    )

            # 次の一覧ページ
            next_page = response.css(
                "li.next a::attr(href)"
            ).get()

            if next_page:
                next_url = urljoin(
                    response.url,
                    next_page
                )

                yield scrapy.Request(
                    next_url,
                    callback=self.parse
                )

        except Exception as e:
            self.notify_error(
                f"一覧ページの処理中にエラーが発生しました: {e}"
            )

    def parse_detail(self, response):
        try:
            item = BookscraperItem()

            # タイトル
            item["title"] = response.css(
                "div.product_main h1::text"
            ).get()

            # 価格
            item["price"] = response.css(
                "div.product_main .price_color::text"
            ).get()

            # 在庫
            item["availability"] = response.css(
                "div.product_main .availability"
            ).xpath("string(.)").get()

            # 評価
            rating_class = response.css(
                "div.product_main p.star-rating::attr(class)"
            ).get()

            rating_map = {
                "One": 1,
                "Two": 2,
                "Three": 3,
                "Four": 4,
                "Five": 5,
            }

            if rating_class:
                rating_name = rating_class.replace(
                    "star-rating",
                    ""
                ).strip()

                item["rating"] = rating_map.get(
                    rating_name
                )
            else:
                item["rating"] = None

            # 詳細ページURL
            item["url"] = response.url

            yield item

        except Exception as e:
            self.notify_error(
                f"詳細ページの処理中にエラーが発生しました: "
                f"{response.url} / {e}"
            )

    def closed(self, reason):
        elapsed = time.perf_counter() - self.start_time

        item_count = self.crawler.stats.get_value(
            "item_scraped_count",
            0
        )

        summary = (
            f"{time.strftime('%-m月%-d日')} "
            f"取得完了: {item_count}件 "
            f"(所要時間: {elapsed:.2f}秒)"
        )

        self.logger.info(summary)
        self._notify_slack(summary)
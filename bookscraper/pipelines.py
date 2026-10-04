# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class BookscraperPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # タイトル
        if adapter.get("title"):
            adapter["title"] = adapter["title"].strip()

        # 価格
        if adapter.get("price"):
            adapter["price"] = adapter["price"].strip()

        # 在庫
        if adapter.get("availability"):
            adapter["availability"] = " ".join(
                adapter["availability"].split()
            )

        # URL
        if adapter.get("url"):
            adapter["url"] = adapter["url"].strip()

        return item


class DuplicatesPipeline:
    def __init__(self):
        self.seen_urls = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        url = adapter.get("url")

        if not url:
            raise DropItem("URLがないItemを削除しました")

        if url in self.seen_urls:
            raise DropItem(
                f"重複データを削除しました: {url}"
            )

        self.seen_urls.add(url)

        return item
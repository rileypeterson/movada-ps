import scrapy
from scrapy_playwright.page import PageCoroutine
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import os
import traceback
import json
import zmq
import asyncio


class MovadaPubSpider(scrapy.Spider):
    name = "movada_pub"

    custom_settings = {
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": False},
        "PLAYWRIGHT_ABORT_REQUEST": lambda req: req.resource_type in {"image"}
        or req.url.endswith(".gif"),
    }

    def __init__(self, *args, url=None, port=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url or "https://www.bovada.lv/sports/baseball"
        assert self.url.startswith(
            "https://www.bovada.lv"
        ), "Url doesn't look like a Bovada url"
        self.port = port or 5556

    def start_requests(self):
        start_url = self.url
        wait_for_first_coupon_box = PageCoroutine(
            "wait_for_selector",
            "sp-next-events",
        )
        scroll_to_bottom = PageCoroutine(
            "evaluate", "window.scrollBy(0, document.body.scrollHeight)"
        )
        yield scrapy.Request(
            start_url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_coroutines": [
                    wait_for_first_coupon_box,
                    scroll_to_bottom,
                ],
            },
        )

    async def parse_sp_multi_market(self, l):
        competitors = await l.locator(".competitors").all_inner_texts()
        competitors = competitors[0].splitlines()

        # Spread
        spread = await l.locator(".market-type").nth(0).all_inner_texts()
        spread = spread[0].splitlines()

        # ML
        ml = await l.locator(".market-type").nth(1).all_inner_texts()
        ml = ml[0].splitlines()

        # Total
        total = await l.locator(".market-type").nth(2).all_inner_texts()
        total = total[0].splitlines()
        d = {"competitors": competitors, "spread": spread, "ml": ml, "total": total}
        return d

    async def open_show_more(self, page):
        # Open show more button
        # Sometimes this doesn't actually do anything
        for _ in range(10):
            try:
                await page.click("#showMore", timeout=1000)
            except Exception:
                # print(traceback.format_exc())
                break

    async def open_plus_boxes(self, page):
        # Open all plus boxes
        for _ in range(100):
            try:
                await page.click(
                    "i.icon.header-collapsible__icon.icon-plus", timeout=1000
                )
            except Exception:
                # print(traceback.format_exc())
                break

    async def read_data(self, page):
        urls = await page.eval_on_selector_all(
            "sp-multi-markets a.game-view-cta",
            "elements => elements.map(element => element.href)",
        )
        data = dict()
        for url in urls:
            u = url.replace("https://www.bovada.lv", "")
            l = page.locator(f"sp-multi-markets:has(a[href='{u}'])")
            data[url] = await self.parse_sp_multi_market(l)
        return data

    async def parse(self, response):
        page = response.meta["playwright_page"]

        await self.open_show_more(page)
        await self.open_plus_boxes(page)

        data = await self.read_data(page)

        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.bind(f"tcp://*:{self.port}")
        i = 0
        while True:
            print(i)
            try:
                data_new = await self.read_data(page)
            except IndexError:
                traceback.print_exc()
                await asyncio.sleep(0.01)
                continue
            for k_new, v_new in data_new.items():
                if k_new not in data or v_new != data[k_new]:
                    socket.send_multipart(
                        [k_new.encode(), json.dumps(data_new[k_new]).encode()]
                    )
            data = data_new
            await asyncio.sleep(0.01)
            i += 1

        # Other stuff
        # await elm.get_attribute("class")

        # await (await (await page.locator("sp-multi-markets").nth(3).element_handle()).wait_for_selector(
        #     "* > .price-increased", timeout=5000)).inner_text()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=False)
    parser.add_argument("--url", type=str, required=False)
    kwargs = parser.parse_args()

    process = CrawlerProcess(get_project_settings())
    process.crawl(MovadaPubSpider, **vars(kwargs))
    process.start()

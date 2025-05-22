import time
import scrapy
from moegirl.items import CategoryItem, ArticleItem
from urllib.parse import urlparse, parse_qs

class MoegirlSpider(scrapy.Spider):
    name = 'moegirl'
    allowed_domains = ['moegirl.icu']
    start_urls = ['https://moegirl.icu/index.php?title=Category:作品']

    custom_settings = {
        # 使用 scrapy-playwright 进行渲染，绕过 Cloudflare
        'DOWNLOAD_HANDLERS': {
            'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
            'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
        },
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',  # 可选 'firefox' 或 'webkit'
        'PLAYWRIGHT_LAUNCH_OPTIONS': {'headless': True},
        'CONCURRENT_REQUESTS': 5,
    }

    def start_requests(self):
        self.logger.info("🔔 延迟 60 秒后再开始爬取…")
        time.sleep(60)
        # 所有请求都启用 Playwright
        for url in self.start_urls:
            yield scrapy.Request(url, meta={'playwright': True}, callback=self.parse)

    def parse(self, response):
        # 从根分类开始解析
        yield from self.parse_category(response, parent=None)

    def parse_category(self, response, parent):
        title = response.css('title::text').get().split(' - ')[0]
        category = CategoryItem(
            name=title,
            parent_categories=[parent] if parent else [],
            subcategories=[]
        )

        # 解析子分类
        for a in response.css('#mw-subcategories .mw-content-ltr a'):
            name = a.css('::text').get()
            url = response.urljoin(a.attrib['href'])
            category['subcategories'].append(name)
            yield scrapy.Request(url,
                                  meta={'playwright': True},
                                  callback=self.parse_category,
                                  cb_kwargs={'parent': title})

        # 解析词条列表
        for a in response.css('#mw-pages .mw-content-ltr a'):
            href = a.attrib['href']
            raw_url = response.urljoin(href) + '&action=raw'
            yield scrapy.Request(raw_url,
                                  meta={'playwright': True},
                                  callback=self.parse_article,
                                  cb_kwargs={'categories': [title]})

        # 翻页：子分类
        next_sub = response.xpath("//div[@id='mw-subcategories']//a[text()='下一页']/@href").get()
        if next_sub:
            yield response.follow(next_sub,
                                  meta={'playwright': True},
                                  callback=self.parse_category,
                                  cb_kwargs={'parent': parent})
        # 翻页：词条列表
        next_page = response.xpath("//div[@id='mw-pages']//a[text()='下一页']/@href").get()
        if next_page:
            yield response.follow(next_page,
                                  meta={'playwright': True},
                                  callback=self.parse_category,
                                  cb_kwargs={'parent': parent})

        yield category

    def parse_article(self, response, categories):
        qs = urlparse(response.url).query
        title = parse_qs(qs).get('title', [''])[0]
        yield ArticleItem(
            title=title,
            content=response.text,
            categories=categories
        )
import scrapy
from moegirl.items import CategoryItem, ArticleItem
from urllib.parse import urlparse, parse_qs

class MoegirlSpider(scrapy.Spider):
    name = 'moegirl'
    allowed_domains = ['moegirl.icu']
    start_urls = ['https://moegirl.icu/index.php?title=Category:作品']

    def parse(self, response):
        # 从根分类开始解析
        yield from self.parse_category(response, parent=None)

    def parse_category(self, response, parent):
        # 提取当前分类名称
        title = response.css('title::text').get().split(' - ')[0]
        category = CategoryItem(
            name=title,
            parent_categories=[parent] if parent else [],
            subcategories=[]
        )

        # 解析并调度子分类
        subcat_links = response.css('#mw-subcategories .mw-content-ltr a')
        subcats = []
        for a in subcat_links:
            name = a.css('::text').get()
            url = response.urljoin(a.attrib['href'])
            subcats.append(name)
            yield scrapy.Request(url, callback=self.parse_category, cb_kwargs={'parent': title})
        category['subcategories'] = subcats

        # 解析词条列表并调度获取原始内容
        page_links = response.css('#mw-pages .mw-content-ltr a')
        for a in page_links:
            href = a.attrib['href']
            raw_url = response.urljoin(href) + '&action=raw'
            yield scrapy.Request(raw_url, callback=self.parse_article, cb_kwargs={'categories': [title]})

        # 翻页：子分类
        next_sub = response.xpath("//div[@id='mw-subcategories']//a[text()='下一页']/@href").get()
        if next_sub:
            yield response.follow(next_sub, callback=self.parse_category, cb_kwargs={'parent': parent})

        # 翻页：词条列表
        next_page = response.xpath("//div[@id='mw-pages']//a[text()='下一页']/@href").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_category, cb_kwargs={'parent': parent})

        yield category

    def parse_article(self, response, categories):
        # 从 URL 参数中提取词条标题
        qs = urlparse(response.url).query
        title = parse_qs(qs).get('title', [''])[0]
        item = ArticleItem(
            title=title,
            content=response.text,
            categories=categories
        )
        yield item
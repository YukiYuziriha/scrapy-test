import scrapy


class AlkotekaSpider(scrapy.Spider):
    name = "alkoteka"
    allowed_domains = ["alkoteka.com"]

    def start_requests(self):
        # TODO: load category URLs from file or constants
        pass

    def parse(self, response):
        # TODO: extract product links and pagination
        pass

    def parse_product(self, response):
        # TODO: parse product details into ProductItem
        pass

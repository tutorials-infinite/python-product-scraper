import random as rand
import time
from typing import List
import bs4
import requests as req
from data import Product, Website
import urllib3

# disable the insecure certificates warning on the console
urllib3.disable_warnings()


class UrlDownloader:
    __WINDOWS_BROWSER_REQUEST_PROPERTY = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.95 Safari/537.11'
    __LINUX_BROWSER_REQUEST_PROPERTY = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.84 Safari/537.36'
    __MAC_BROWSER_REQUEST_PROPERTY = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
    __AMAZON_WEBSITE_NAME: str = 'Amazon'
    __ALDI_UK_WEBSITE_NAME: str = 'Aldi-UK'
    __TESCO_WEBSITE_NAME: str = 'Tesco'

    # free proxy list website url --> https://spys.one/ only get http proxies
    __proxies = [
        'http://84.17.35.129:3128',
        'http://45.32.109.170:8080',
        'http://84.54.217.19:8080'
    ]
    __session_proxies = {
        'http': rand.choice(__proxies)
    }
    __website_name_session_param = {
        __AMAZON_WEBSITE_NAME: req.Session(),
        __ALDI_UK_WEBSITE_NAME: req.Session(),
        __TESCO_WEBSITE_NAME: req.Session()
    }

    __validBrowserAgents = [__WINDOWS_BROWSER_REQUEST_PROPERTY, __LINUX_BROWSER_REQUEST_PROPERTY,
                            __MAC_BROWSER_REQUEST_PROPERTY]

    def scrap_items(self, website: Website, products: List) -> Website:
        website_name_product_html_lambda_switcher = {
            self.__ALDI_UK_WEBSITE_NAME: self.__retreive_aldi_uk_products_from_html,
            self.__AMAZON_WEBSITE_NAME: self.__retreive_amazon_products_from_html,
            self.__TESCO_WEBSITE_NAME: self.__retreive_tesco_products_from_html
        }

        aggregated_products = []

        for product in products:
            try:
                product_html = self.__fetch_product_html(product, website.search_query_url, website.name,
                                                         website.search_query_param)
                scrap_products_lambda = website_name_product_html_lambda_switcher.get(website.name, None)
                if scrap_products_lambda is None:
                    website.products = []
                    return website
                scrap_products = scrap_products_lambda(product_html, website.home_url)
                aggregated_products.extend(scrap_products)
            except Exception as exp:
                print(
                    f'Error occurred for website --> {website.name}, for product --> {product}, and the exception --> {exp}')
                continue

        temp_website = Website(website.name, website.home_url, website.search_query_url, website.search_query_param,
                               aggregated_products)
        self.__website_name_session_param[temp_website.name].close()
        return temp_website

    def __fetch_product_html(self, product_name: str, website_search_base_url: str, website_name: str,
                             website_query_param: str) -> str:
        header_agent = {'User-Agent': rand.choice(self.__validBrowserAgents), 'Accept-Language': 'en-US, en;q=0.5'}
        session = self.__website_name_session_param[website_name]
        query_param = {website_query_param: product_name}
        if len(session.proxies) == 0:
            session.proxies.update(self.__session_proxies)
        product_response = session.get(website_search_base_url, params=query_param, headers=header_agent,
                                       timeout=20, verify=False)
        random_request_delay = rand.randint(2, 3)
        time.sleep(random_request_delay)
        return product_response.text if product_response is not None else ''

    @staticmethod
    def __retreive_tesco_products_from_html(product_html: str, website_home_url: str) -> List:
        soup = bs4.BeautifulSoup(product_html, 'lxml')
        all_product_divs = soup.find_all('li', attrs={'class': 'product-list--list-item'})
        products = list()

        for single_product_div in all_product_divs:

            if single_product_div is None:
                continue

            # extracting the product title and and image base-64 string
            product_image_container_div: bs4.Tag = single_product_div.find('div',
                                                                           attrs={'class': 'product-image__container'})
            product_image_tag: bs4.Tag = product_image_container_div.find(
                'img') if product_image_container_div is not None else None
            product_title: str = product_image_tag.get('alt') if product_image_tag is not None else None
            if product_title is None or product_title == '':
                continue
            product_image_single_source_base64: str = product_image_tag.get(
                'src') if product_image_tag is not None else None

            # extracting the product detail link
            product_detail_content_div: bs4.Tag = single_product_div.find('div',
                                                                          attrs={'class': 'product-details--content'})
            product_detail_content_tag: bs4.Tag = product_detail_content_div.find(
                attrs={'data-auto': 'product-tile--title'}) if product_detail_content_div is not None else None
            product_detail_link: str = product_detail_content_tag.get(
                'href') if product_detail_content_tag is not None else None

            # extracting the product price details
            product_detail_wrapper_div: bs4.Tag = single_product_div.find('div',
                                                                          attrs={'class': 'price-details--wrapper'})
            product_currency_tag_span: bs4.Tag = product_detail_wrapper_div.find(
                attrs={'class': 'currency'}) if product_detail_wrapper_div is not None else None
            product_currency: str = product_currency_tag_span.text if product_currency_tag_span is not None else None
            product_price_tag_span: bs4.Tag = product_detail_wrapper_div.find(
                attrs={'data-auto': 'price-value'}) if product_detail_wrapper_div is not None else None
            product_price: str = product_price_tag_span.text if product_price_tag_span is not None else None
            whole_product_price = f'{product_currency}{product_price}' if product_currency is not None and product_price is not None else None
            price_unit = UrlDownloader.__retreive_product_unit_from_price(
                whole_product_price) if whole_product_price is not None else None
            product_price = UrlDownloader.__remove_product_unit_from_price(
                whole_product_price) if whole_product_price is not None else None

            # extracting the ounce pound text
            price_per_quantity_weight_div: bs4.Tag = single_product_div.find('div', attrs={
                'class': 'price-per-quantity-weight'})
            quantity_price_symbol_span: bs4.Tag = price_per_quantity_weight_div.find(
                attrs={'class': 'currency'}) if price_per_quantity_weight_div is not None else None
            quantity_price_symbol: str = quantity_price_symbol_span.text if quantity_price_symbol_span is not None else None
            quantity_price_span: bs4.Tag = price_per_quantity_weight_div.find(
                attrs={'data-auto': 'price-value'}) if price_per_quantity_weight_div is not None else None
            quantity_price: str = quantity_price_span.text if quantity_price_span is not None else None
            quantity_per_price_span: bs4.Tag = price_per_quantity_weight_div.find(
                attrs={'class': 'weight'}) if price_per_quantity_weight_div is not None else None
            quantity_per_price: str = quantity_per_price_span.text if quantity_per_price_span is not None else None
            ounce_pound_text = f'{quantity_price_symbol}{quantity_price}{quantity_per_price}' \
                if quantity_price_symbol is not None and quantity_price is not None and quantity_per_price is not None else None

            if product_image_single_source_base64 is None or product_detail_link is None or product_price is None or product_price == '':
                continue

            product = Product(product_title, product_image_single_source_base64, '',
                              product_detail_link if product_detail_link.startswith(
                                  'http') else website_home_url + product_detail_link, list(), ounce_pound_text,
                              product_price, '', price_unit)
            products.append(product)
        return products

    @staticmethod
    def __retreive_aldi_uk_products_from_html(product_html: str, website_home_url: str) -> List:
        soup = bs4.BeautifulSoup(product_html, 'lxml')
        all_product_divs = soup.select('div.category-item,div.js-category-item')
        products = list()
        for single_product_div in all_product_divs:

            if single_product_div is None:
                continue

            # extracting the product detail url
            a_link_class: bs4.Tag = single_product_div.find('a',
                                                            attrs={'class': 'category-item__link js-category-link'})
            product_detail_link: str = a_link_class.get('href') if a_link_class is not None else None
            if product_detail_link is None or product_detail_link == '':
                continue

            # extracting the product single image source and multiple image sources
            outer_picture_class: bs4.Tag = single_product_div.find('picture', attrs={
                'class': 'category-item__image js-category-image'})
            all_source_media_tags: bs4.ResultSet = outer_picture_class.find_all(
                'source') if outer_picture_class is not None else None
            product_image_source_set: List = []
            if all_source_media_tags is not None:
                for single_source_media_tag in all_source_media_tags:
                    comma_separated_source_set_attribute: str = single_source_media_tag.get('srcset')
                    try:
                        single_media_tag: str = comma_separated_source_set_attribute.split(',')[
                            1] if comma_separated_source_set_attribute is not None else None

                        # remove the 2x,3x,2.5x from featured images if we found the featured image

                        space_removal_single_media_tag: str = single_media_tag.strip() if single_media_tag is not None else None
                        if space_removal_single_media_tag is not None and ' ' in space_removal_single_media_tag:
                            product_image_source_set.append(space_removal_single_media_tag.split(' ')[0].strip())
                        elif space_removal_single_media_tag is not None:
                            product_image_source_set.append(space_removal_single_media_tag)
                    except ValueError as e:
                        print(e)
            product_image_single_source_tag = outer_picture_class.find(
                'img') if outer_picture_class is not None else None
            product_image_single_source_attribute_value: str = product_image_single_source_tag.get(
                'srcset') if product_image_single_source_tag is not None else None
            try:
                product_image_single_source = product_image_single_source_attribute_value.split(',')[
                    1] if product_image_single_source_attribute_value is not None else ''
            except ValueError:
                product_image_single_source = product_image_single_source_tag.get(
                    'src') if product_image_single_source_tag is not None else ''

            # extracting the product title
            product_title_class: bs4.Tag = single_product_div.find(attrs={'class': 'category-item__title'})
            product_title = product_title_class.find('a').text if product_title_class is not None else None

            # extracting the product price
            product_price_class: bs4.Tag = single_product_div.find(attrs={'class': 'category-item__price'})
            whole_product_price: str = product_price_class.text if product_price_class is not None else None
            product_price_point_index = whole_product_price.find('.') if whole_product_price is not None else -1
            try:
                temp_product_price = whole_product_price[0:product_price_point_index + 3].strip()
            except ValueError:
                temp_product_price = None
            price_unit = UrlDownloader.__retreive_product_unit_from_price(
                temp_product_price) if temp_product_price is not None else None
            product_price = UrlDownloader.__remove_product_unit_from_price(
                temp_product_price) if temp_product_price is not None else None

            # extracting the ounce pound text for the product
            ounce_pound_text_class: bs4.Tag = single_product_div.find(attrs={'class': 'category-item__pricePerUnit'})
            if ounce_pound_text_class is not None and not ounce_pound_text_class.text.isspace():
                ounce_pound_text = ounce_pound_text_class.text
            else:
                ounce_pound_text = None

            # extracting the product rating stars
            stars_clippath_tag: bs4.Tag = single_product_div.find('clippath', attrs={'class': 'js-stars-clippath'})
            filled_stars_attribute_value: str = stars_clippath_tag.get('id') if stars_clippath_tag is not None else None
            if filled_stars_attribute_value is not None and filled_stars_attribute_value.startswith('filled-stars-'):
                filled_stars_floating_point_value: float = float(
                    filled_stars_attribute_value.split('filled-stars-')[1]) + 0.2
                product_rating = "{:.2f}".format(filled_stars_floating_point_value * 5)
            elif filled_stars_attribute_value is not None:
                filled_stars_floating_point_value: float = float(filled_stars_attribute_value.split('.')[-1]) + 0.2
                product_rating = "{:.2f}".format(filled_stars_floating_point_value * 5)
            else:
                product_rating = ''

            # extracting the product rating count
            product_rating_count = None
            if product_rating is not None and product_rating != '':
                product_span_rating_count: bs4.Tag = single_product_div.find('span', attrs={'class': 'count'})
                product_rating_count = product_span_rating_count.text.lstrip('(').rstrip(
                    ')') if product_span_rating_count is not None else None

            if product_title is None or product_image_single_source is None or product_price is None or product_price == '':
                continue

            product = Product(product_title, product_image_single_source.strip(), product_rating,
                              product_detail_link if product_detail_link.startswith(
                                  'http') else website_home_url + product_detail_link, product_image_source_set,
                              ounce_pound_text, product_price, product_rating_count, price_unit)
            products.append(product)

        return products

    @staticmethod
    def __retreive_amazon_products_from_html(product_html: str, website_home_url: str) -> List:
        soup = bs4.BeautifulSoup(product_html, 'lxml')
        all_product_divs = soup.find_all('div', attrs={'data-component-type': 's-search-result'})
        products = list()
        for single_product_div in all_product_divs:

            if single_product_div is None:
                continue

            # extracting the ounce pound text for the product
            ounce_pound_text_outer_div: bs4.Tag = single_product_div.find('div', attrs={
                "class": "a-row a-size-base a-color-secondary"})
            ounce_pound_text_inner_span: bs4.Tag = ounce_pound_text_outer_div.find(
                'span',
                attrs={"class": "a-color-information a-text-bold"}) if ounce_pound_text_outer_div is not None else None

            ounce_pound_text = ounce_pound_text_inner_span.text if ounce_pound_text_inner_span is not None else None

            # extracting the product single featured images, other source images, and product detail url
            image_outer_span: bs4.Tag = single_product_div.find('span', attrs={'class': 'rush-component',
                                                                               'data-component-type': 's-product-image'})
            a_link_class: bs4.Tag = image_outer_span.find('a', attrs={
                'class': 'a-link-normal'}) if image_outer_span is not None else None
            temp_navigation_url: str = a_link_class.get('href') if a_link_class is not None else None

            image_span: bs4.Tag = image_outer_span.find('img', attrs={
                'class': 's-image'}) if image_outer_span is not None else None

            product_title: str = image_span.get('alt') if image_span is not None else None
            product_image_single_source = image_span.get('src') if image_span is not None else None
            product_image_source_set: str = image_span.get('srcset') if image_span is not None else None
            product_image_source_sets = product_image_source_set.split(
                ',') if product_image_source_set is not None else []

            # remove the 2x,3x,2.5 from featured images if we found the featured images
            updated_product_image_source_set = list()
            for single_product_image_set in product_image_source_sets:
                space_removal_product_image_set: str = single_product_image_set.strip()
                if ' ' in space_removal_product_image_set:
                    updated_product_image_source_set.append(space_removal_product_image_set.split(' ')[0])

            # extracting the product price related details
            a_price_outer_span: bs4.Tag = single_product_div.find('span', attrs={'class': 'a-price'})
            a_price_symbol_span: bs4.Tag = a_price_outer_span.find('span', attrs={
                'class': 'a-price-symbol'}) if a_price_outer_span is not None else None
            a_price_whole_span: bs4.Tag = a_price_outer_span.find('span', attrs={
                'class': 'a-price-whole'}) if a_price_outer_span is not None else None
            a_price_fraction_span: bs4.Tag = a_price_outer_span.find('span', attrs={
                'class': 'a-price-fraction'}) if a_price_outer_span is not None else None
            temp_price = a_price_symbol_span.text + a_price_whole_span.text + a_price_fraction_span.text \
                if a_price_fraction_span is not None and a_price_whole_span is not None else None
            price_unit = UrlDownloader.__retreive_product_unit_from_price(
                temp_price) if temp_price is not None else None
            price = UrlDownloader.__remove_product_unit_from_price(temp_price) if temp_price is not None else None

            # extracting the product rating and number of people rate
            a_rating_outer_div: bs4.Tag = single_product_div.find('i', attrs={
                'class': 'a-icon-star-small'
            })
            a_rating_inner_span: bs4.Tag = a_rating_outer_div.find('span', attrs={
                'class': 'a-icon-alt'}) if a_rating_outer_div is not None else None

            a_customer_reviews_outer_class: bs4.Tag = single_product_div.find('a', attrs={
                'href': temp_navigation_url + '#customerReviews'
            }) if temp_navigation_url is not None else None
            a_customer_review_inner_span = a_customer_reviews_outer_class.find(
                'span') if a_customer_reviews_outer_class is not None else None
            customer_reviews: str = a_customer_review_inner_span.text if a_customer_review_inner_span is not None else '0'

            if temp_navigation_url is None or product_image_single_source is None or product_title is None or product_title.startswith(
                    'Sponsored Ad') or price is None or price == '':
                continue

            # remove the ref number from the url. We need to remove that because we're checking on the basis of url
            # for previous products. Amazon include the 'ref' parameter in the path for current query.
            product_detail_url: str = temp_navigation_url
            if '/ref' in temp_navigation_url:
                product_detail_url = temp_navigation_url.split('/ref')[0]

            product = Product(product_title, product_image_single_source,
                              a_rating_inner_span.text if a_rating_inner_span is not None else None,
                              product_detail_url if product_detail_url.startswith(
                                  'http') else website_home_url + product_detail_url, updated_product_image_source_set,
                              ounce_pound_text, price, customer_reviews, price_unit)
            products.append(product)

        return products

    @staticmethod
    def __remove_product_unit_from_price(product_price: str) -> str:
        temp_product_price: str = ''
        if '$' in product_price:
            temp_product_price = product_price.split('$')[1].lstrip(' ').rstrip(' ')
        elif '£' in product_price:
            temp_product_price = product_price.split('£')[1].lstrip(' ').rstrip(' ')
        return temp_product_price

    @staticmethod
    def __retreive_product_unit_from_price(product_price: str) -> str:
        product_unit = '£'
        if '$' in product_price:
            product_unit = '$'
        elif '£' in product_price:
            product_unit = '£'
        return product_unit

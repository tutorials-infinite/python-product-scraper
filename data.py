from typing import NamedTuple, List


class Website(NamedTuple):
    name: str
    home_url: str
    search_query_url: str
    search_query_param: str
    products: List = list()


class Product(NamedTuple):
    title: str
    featured_image: str
    rating: str
    detail_url: str
    featured_images: List
    ounce_pound_text: str
    price: str
    review_count: str
    unit: str

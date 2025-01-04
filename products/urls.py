from django.urls import path
from . import views

from .views import (
    BannerList, ProductListView, ProductReviewListView, ProductSearchView, CategoryListView,
    NewProductsView, FilterProductsByPriceView, ProductsByCategoryView, ProductDetail, RecommendProductsView, RelatedProductsView, ReviewCreateAPIView, TopSalesRealTimeAPIView
)

urlpatterns = [
    path('products/', ProductListView.as_view(), name='product-list'),
    path('product/<str:product_id>/', ProductDetail.as_view(), name='product-detail'),
    path('products/search/', ProductSearchView.as_view(), name='product-search'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('products/new/', NewProductsView.as_view(), name='new-products'),
    path('products/filter-by-price/', FilterProductsByPriceView.as_view(), name='filter-products-by-price'),
    path('products/by-category/<str:category_id>/', ProductsByCategoryView.as_view(), name='products-by-category'),
    path('reviews/product/<str:product_id>/', ProductReviewListView.as_view(), name='product-reviews'),
    path('reviews/', ReviewCreateAPIView.as_view(), name='review-create'),
    path('banners/', BannerList.as_view(), name='banner-list'),
    path('top-sales-realtime/', TopSalesRealTimeAPIView.as_view(), name='top-sales-realtime'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('related_products/<str:product_id>/', RelatedProductsView.as_view(), name='related-products'),
    path('recommend/<str:user_id>/', RecommendProductsView.as_view(), name='recommend_products'),

     # API để tạo thanh toán VNPAY
    path('create_payment/', views.create_payment, name='create_payment'),

]

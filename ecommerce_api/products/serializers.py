from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Product, Category, Review, ProductImage

User = get_user_model()

class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'is_active', 'products_count']

    def get_products_count(self, obj):
        return obj.products.filter(is_active=True).count()
    
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary']

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'user_id', 'rating', 'title', 'comment', 
                 'is_verified_purchase', 'created_at', 'updated_at']
        read_only_fields = ['user', 'is_verified_purchase', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
class ProductListSerializer(serializers.ModelSerializer):

    category = serializers.StringRelatedField()
    average_rating = serializers.ReadOnlyField()
    reviews_count = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'price', 'category', 'stock_status', 
                 'is_featured', 'average_rating', 'reviews_count', 'primary_image']

    def get_reviews_count(self, obj):
        return obj.reviews.count()

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_image.image.url)
        return None   

class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'price', 'category', 'category_id',
                 'stock_quantity', 'stock_status', 'sku', 'weight', 'dimensions',
                 'is_active', 'is_featured', 'images', 'reviews', 'average_rating',
                 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'price', 'category',
                 'stock_quantity', 'stock_status', 'sku', 'weight', 'dimensions',
                 'is_active', 'is_featured', 'images', 'uploaded_images']

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        product = Product.objects.create(**validated_data)
        
        for i, image in enumerate(uploaded_images):
            ProductImage.objects.create(
                product=product, 
                image=image,
                is_primary=(i == 0)  # First image is primary
            )
        
        return product
    
    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if uploaded_images:
            # Delete existing images and add new ones
            instance.images.all().delete()
            for i, image in enumerate(uploaded_images):
                ProductImage.objects.create(
                    product=instance,
                    image=image,
                    is_primary=(i == 0)
                )

        return instance
    

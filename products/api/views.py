"""
Products API Views - Master Data Sync Endpoints
HO → Edge: Products, Categories, Modifiers, Tables
"""
from rest_framework import viewsets, permissions, status, authentication
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Prefetch
from products.models import (
    Category, Product, ProductPhoto, Modifier, ModifierOption,
    ProductModifier, TableArea, Tables, KitchenStation, PrinterConfig
)
from .serializers import (
    CategorySerializer, ProductSerializer, ModifierSerializer,
    TableAreaSerializer, TableSerializer, KitchenStationSerializer,
    PrinterConfigSerializer
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Category master data - Edge pulls categories"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def sync(self, request):
        """
        Sync categories for Edge (Food Court architecture)
        
        Query params:
        - company_id (required): Company ID for the edge location
        - store_id (optional): Store ID (for reference)
        - brand_id (optional): Filter by specific brand
        - last_sync (optional): ISO datetime for incremental sync
        
        Categories are brand-scoped, so Edge gets all categories from all brands in the company
        """
        company_id = request.query_params.get('company_id')
        store_id = request.query_params.get('store_id')
        brand_id = request.query_params.get('brand_id')
        last_sync = request.query_params.get('last_sync')
        
        if not company_id:
            return Response(
                {'error': 'company_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter by company through brand relationship
        queryset = self.get_queryset().filter(brand__company_id=company_id)
        
        # Optional: Filter by specific brand
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        
        # Incremental sync
        if last_sync:
            queryset = queryset.filter(updated_at__gt=last_sync)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'last_sync': timezone.now().isoformat(),
            'company_id': company_id,
            'store_id': store_id,
            'data': serializer.data
        })


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Product master data - Edge pulls products with photos & modifiers"""
    queryset = Product.objects.select_related('category', 'brand').prefetch_related(
        'photos',
        Prefetch('product_modifiers', queryset=ProductModifier.objects.select_related('modifier'))
    ).filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def sync(self, request):
        """
        Sync products for Edge (Food Court architecture)
        
        Query params:
        - company_id (required): Company ID for the edge location
        - store_id (optional): Store ID for store-specific filtering
        - brand_id (optional): Filter by specific brand (for single-brand sync)
        - last_sync (optional): ISO datetime for incremental sync
        - category_id (optional): Filter by category
        
        Food Court: Edge has 1 company + 1 store + multiple brands
        Edge sends company_id + store_id to get all products from all brands in that store
        """
        company_id = request.query_params.get('company_id')
        store_id = request.query_params.get('store_id')
        brand_id = request.query_params.get('brand_id')
        last_sync = request.query_params.get('last_sync')
        category_id = request.query_params.get('category_id')
        
        if not company_id:
            return Response(
                {'error': 'company_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter by company first (multi-tenant isolation)
        queryset = self.get_queryset().filter(company_id=company_id)
        
        # Optional: Filter by specific brand (for single-brand stores)
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        else:
            # For food court: get all brands in the company
            # Edge will receive products from all brands
            pass
        
        # Optional: Filter by category
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Incremental sync
        if last_sync:
            queryset = queryset.filter(updated_at__gt=last_sync)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'last_sync': timezone.now().isoformat(),
            'company_id': company_id,
            'store_id': store_id,
            'data': serializer.data
        })


class ModifierViewSet(viewsets.ReadOnlyModelViewSet):
    """Modifier master data - Edge pulls modifiers with options and product mappings"""
    queryset = Modifier.objects.prefetch_related('options').filter(is_active=True)
    serializer_class = ModifierSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get', 'post'])
    def sync(self, request):
        """
        Sync modifiers for Edge (Food Court architecture)
        
        Supports both GET and POST methods
        
        Query params (GET) or Body (POST):
        - company_id (required): Company ID for the edge location
        - store_id (optional): Store ID (for reference)
        - brand_id (optional): Filter by specific brand
        - last_sync (optional): ISO datetime for incremental sync
        
        Returns:
        - modifiers: List of modifier groups with their options
        - product_modifiers: M2M mapping of products to modifiers
        - total: Count of modifiers
        - total_mappings: Count of product-modifier mappings
        - sync_timestamp: Current server timestamp
        """
        # Support both POST (preferred) and GET (legacy)
        if request.method == 'POST':
            company_id = request.data.get('company_id')
            store_id = request.data.get('store_id')
            brand_id = request.data.get('brand_id')
            last_sync = request.data.get('last_sync') or request.data.get('updated_since')
        else:  # GET
            company_id = request.query_params.get('company_id')
            store_id = request.query_params.get('store_id')
            brand_id = request.query_params.get('brand_id')
            last_sync = request.query_params.get('last_sync') or request.query_params.get('updated_since')
        
        if not company_id:
            return Response(
                {'error': 'company_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter by company through brand relationship
        queryset = self.get_queryset().filter(brand__company_id=company_id)
        
        # Optional: Filter by specific brand
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        
        # Incremental sync
        if last_sync:
            queryset = queryset.filter(updated_at__gt=last_sync)
        
        # Serialize modifiers with nested options
        serializer = self.get_serializer(queryset, many=True)
        
        # Get product-modifier mappings
        modifier_ids = [modifier.id for modifier in queryset]
        product_modifiers = ProductModifier.objects.filter(
            modifier_id__in=modifier_ids
        ).select_related('product', 'modifier').order_by('product', 'sort_order')
        
        product_modifier_list = []
        for pm in product_modifiers:
            product_modifier_list.append({
                'id': str(pm.id),
                'product_id': str(pm.product_id),
                'product_name': pm.product.name,
                'modifier_id': str(pm.modifier_id),
                'modifier_name': pm.modifier.name,
                'sort_order': pm.sort_order,
            })
        
        return Response({
            'modifiers': serializer.data,
            'product_modifiers': product_modifier_list,
            'total': queryset.count(),
            'total_mappings': len(product_modifier_list),
            'sync_timestamp': timezone.now().isoformat(),
            'company_id': company_id,
            'store_id': store_id,
            'brand_id': brand_id,
        })


class TableAreaViewSet(viewsets.ReadOnlyModelViewSet):
    """Table area master data"""
    queryset = TableArea.objects.filter(is_active=True)
    serializer_class = TableAreaSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def sync(self, request):
        """
        Sync table areas for Edge (Food Court architecture)
        
        Query params:
        - company_id (required): Company ID for the edge location
        - store_id (required): Store ID - Table areas are store-specific
        - brand_id (optional): Filter by specific brand (for multi-brand food court)
        
        Table areas can be:
        - Store-specific (most common for food courts)
        - Brand-specific within a store
        """
        company_id = request.query_params.get('company_id')
        store_id = request.query_params.get('store_id')
        brand_id = request.query_params.get('brand_id')
        
        if not company_id:
            return Response(
                {'error': 'company_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not store_id:
            return Response(
                {'error': 'store_id parameter required - table areas are store-specific'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter by company and store
        queryset = self.get_queryset().filter(
            company_id=company_id,
            store_id=store_id
        )
        
        # Optional: Filter by specific brand (for brand-specific areas)
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'count': queryset.count(),
            'last_sync': timezone.now().isoformat(),
            'company_id': company_id,
            'store_id': store_id,
            'data': serializer.data
        })


class TableViewSet(viewsets.ReadOnlyModelViewSet):
    """Table master data (template only, status managed by Edge)"""
    queryset = Tables.objects.select_related('area')
    serializer_class = TableSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.SessionAuthentication, authentication.TokenAuthentication]
    
    @action(detail=False, methods=['get'])
    def sync(self, request):
        """
        Sync tables for Edge (Food Court architecture)
        
        Query params:
        - company_id (required): Company ID for the edge location
        - store_id (required): Store ID - Tables are linked to table areas (store-specific)
        - brand_id (optional): Filter by specific brand
        
        Tables belong to table areas, which are store-specific
        """
        company_id = request.query_params.get('company_id')
        store_id = request.query_params.get('store_id')
        brand_id = request.query_params.get('brand_id')
        
        if not company_id:
            return Response(
                {'error': 'company_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not store_id:
            return Response(
                {'error': 'store_id parameter required - tables are store-specific'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter by company and store through area relationship
        queryset = self.get_queryset().filter(
            area__company_id=company_id,
            area__store_id=store_id
        )
        
        # Optional: Filter by specific brand
        if brand_id:
            queryset = queryset.filter(area__brand_id=brand_id)
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'count': queryset.count(),
            'last_sync': timezone.now().isoformat(),
            'company_id': company_id,
            'store_id': store_id,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def update_position(self, request, pk=None):
        """
        Update table position on floor plan
        
        POST body:
        {
            "pos_x": 100,
            "pos_y": 150
        }
        """
        table = self.get_object()
        
        pos_x = request.data.get('pos_x')
        pos_y = request.data.get('pos_y')
        
        if pos_x is None or pos_y is None:
            return Response(
                {'error': 'pos_x and pos_y are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            table.pos_x = int(pos_x)
            table.pos_y = int(pos_y)
            table.save()
            
            return Response({
                'success': True,
                'message': f'Table {table.id} position updated',
                'pos_x': table.pos_x,
                'pos_y': table.pos_y
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class KitchenStationViewSet(viewsets.ReadOnlyModelViewSet):
    """Kitchen station master data"""
    queryset = KitchenStation.objects.filter(is_active=True)
    serializer_class = KitchenStationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def sync(self, request):
        """
        Sync kitchen stations for Edge (STORE-SPECIFIC)
        
        Query params:
        - company_id (required): Company ID for the edge location
        - store_id (required): Store ID - Kitchen stations are store-specific
        
        Kitchen stations are ALWAYS store-specific (not company-wide or brand-wide)
        Each store has its own kitchen configuration
        """
        company_id = request.query_params.get('company_id')
        store_id = request.query_params.get('store_id')
        
        if not company_id:
            return Response(
                {'error': 'company_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not store_id:
            return Response(
                {'error': 'store_id parameter required - kitchen stations are store-specific'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter by company and store (kitchen stations are store-specific)
        queryset = self.get_queryset().filter(
            company_id=company_id,
            store_id=store_id
        )
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'count': queryset.count(),
            'last_sync': timezone.now().isoformat(),
            'company_id': company_id,
            'store_id': store_id,
            'data': serializer.data
        })


class PrinterConfigViewSet(viewsets.ReadOnlyModelViewSet):
    """Printer config master data"""
    queryset = PrinterConfig.objects.select_related('station').filter(is_active=True)
    serializer_class = PrinterConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def sync(self, request):
        """Sync printer configs"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'count': queryset.count(),
            'last_sync': timezone.now().isoformat(),
            'data': serializer.data
        })

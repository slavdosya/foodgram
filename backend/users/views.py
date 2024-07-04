from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import SetPasswordSerializer
from djoser.views import UserViewSet
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from users.models import Subscribe
from users.serializers import (AvatarSerializer, CustomUserCreateSerializer,
                               CustomUserReadSerializer, SubscribeSerializer)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    serializer_class = CustomUserCreateSerializer
    pagination_class = LimitOffsetPagination

    def get_serializer_class(self):
        print(self.action)
        if self.action in ('list', 'retrieve'):
            return CustomUserReadSerializer
        if self.action == 'set_password':
            return SetPasswordSerializer
        if self.action == 'me':
            return CustomUserReadSerializer
        if self.action == 'create':
            return CustomUserCreateSerializer
        if self.action == 'subscribe':
            return SubscribeSerializer

    def get_permissions(self):
        if self.action in ('list', 'create', 'retrieve'):
            self.permission_classes = [AllowAny, ]
        return super().get_permissions()

    @action(methods=['post', 'delete'], detail=True)
    def subscribe(self, request, **kwargs):
        user = request.user
        author = get_object_or_404(User, id=self.kwargs['id'])
        if request.method == 'POST':
            if Subscribe.objects.filter(user=user, author=author).exists():
                raise serializers.ValidationError(
                    'Вы уже подписаны на этого автора', code=400
                )
            if user == author:
                raise serializers.ValidationError(
                    'Нельзя подписаться на самого себя', code=400
                )
            serializer = SubscribeSerializer(
                author,
                context={"request": request, }
            )
            Subscribe.objects.create(user=user, author=author)
            return Response(serializer.data, status=201)
        if request.method == 'DELETE':
            try:
                subscribe = Subscribe.objects.get(user=user, author=author)
                subscribe.delete()
            except Subscribe.DoesNotExist:
                raise serializers.ValidationError('Not Found', code=400)
            return Response(status=204)

    @action(methods=['get', ], detail=False,)
    def subscriptions(self, request, **kwargs):
        user = request.user
        queryset = User.objects.filter(subscribed__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeSerializer(
            pages, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(methods=['put', 'delete'], detail=True)
    def avatar(self, request, **kwargs):
        user = get_object_or_404(User, username=request.user)
        if request.method == 'PUT':
            serializers = AvatarSerializer(user, data=request.data)
            if serializers.is_valid():
                serializers.save()
                return Response(serializers.data, status=200)
            return Response(serializers.errors, status=400)
        if request.method == 'DELETE':
            user.avatar = None
            user.save()
            return Response(status=204)

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

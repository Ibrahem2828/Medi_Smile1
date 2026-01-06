# apps/community/serializers.py
import logging
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Content, ContentComment

logger = logging.getLogger(__name__)


# ============================================================
# Content Read
# ============================================================

class ContentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    university_name = serializers.CharField(source="university.name", read_only=True)
    approved_by_name = serializers.SerializerMethodField()

    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Content
        fields = [
            "id",
            "title",
            "description",
            "content_type",
            "category",
            "file",
            "url",
            "tags",
            "author",
            "author_name",
            "university",
            "university_name",
            "status",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "rejection_reason",
            "is_public",
            "is_featured",
            "view_count",
            "likes_count",
            "comments_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def get_approved_by_name(self, obj):
        if not obj.approved_by:
            return None
        return obj.approved_by.get_full_name() or obj.approved_by.username


# ============================================================
# Content Create
# ============================================================

class ContentCreateSerializer(serializers.ModelSerializer):
    content_type = serializers.CharField()
    category = serializers.CharField()

    class Meta:
        model = Content
        fields = [
            "title",
            "description",
            "content_type",
            "category",
            "file",
            "url",
            "tags",
            "is_public",
            "is_featured",
        ]

    def validate(self, attrs):
        ctype = (attrs.get("content_type") or "").strip().lower()
        category = (attrs.get("category") or "").strip().lower()

        # normalize content_type/category to valid choices; fall back to sensible defaults
        ctype_choices = dict(Content.ContentType.choices)
        if ctype not in ctype_choices:
            ctype = Content.ContentType.ARTICLE
        attrs["content_type"] = ctype

        category_choices = dict(Content.Category.choices)
        if category not in category_choices:
            category = Content.Category.GENERAL
        attrs["category"] = category

        if ctype == Content.ContentType.LINK and not attrs.get("url"):
            raise serializers.ValidationError({"url": _("URL is required for link content.")})

        if ctype != Content.ContentType.LINK and not attrs.get("file"):
            raise serializers.ValidationError({"file": _("File is required for this content type.")})

        return attrs


# ============================================================
# Moderation
# ============================================================

class ContentRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=2000)


# ============================================================
# Comments
# ============================================================

class ContentCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ContentComment
        fields = [
            "id",
            "content",
            "user",
            "user_name",
            "text",
            "is_approved",
            "created_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class ContentCommentCreateSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=1, max_length=5000)


# ============================================================
# ⭐ Student Rating
# ============================================================

class StudentPublicRatingSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    average_score = serializers.FloatField(allow_null=True)
    stars = serializers.IntegerField(min_value=0, max_value=5)
    total_evaluations = serializers.IntegerField()


class ToggleLikeResponseSerializer(serializers.Serializer):
    liked = serializers.BooleanField()

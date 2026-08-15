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
    content = serializers.CharField(source="description", read_only=True)
    author_name = serializers.SerializerMethodField()
    university_name = serializers.CharField(source="university.name", read_only=True)
    approved_by_name = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()

    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Content
        fields = [
            "id",
            "title",
            "content",
            "description",
            "content_type",
            "category",
            "file",
            "image_urls",
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
            "is_deleted",
            "deleted_at",
            "deleted_by",
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

    def get_image_urls(self, obj):
        request = self.context.get("request")

        def _build_url(file_field):
            if not file_field:
                return None
            url = getattr(file_field, "url", None)
            if not url:
                return None
            return request.build_absolute_uri(url) if request else url

        return {
            "original": _build_url(obj.file),
            "large": _build_url(obj.image_large),
            "medium": _build_url(obj.image_medium),
            "thumb": _build_url(obj.image_thumb),
        }


# ============================================================
# Content Create
# ============================================================

class ContentCreateSerializer(serializers.ModelSerializer):
    content = serializers.CharField(required=False, allow_blank=True)
    content_type = serializers.CharField()
    category = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Content
        fields = [
            "title",
            "content",
            "description",
            "content_type",
            "category",
            "file",
            "url",
            "tags",
            "is_public",
            "is_featured",
        ]
        extra_kwargs = {"description": {"required": False}}

    def validate(self, attrs):
        content_value = attrs.pop("content", None)
        if content_value is not None:
            attrs["description"] = content_value

        ctype = (attrs.get("content_type") or "").strip().lower()
        category = (attrs.get("category") or "").strip().lower()

        # normalize content_type/category to valid choices; fall back to sensible defaults
        ctype_choices = dict(Content.ContentType.choices)
        if ctype not in ctype_choices:
            raise serializers.ValidationError({"content_type": _("Invalid content type.")})
        attrs["content_type"] = ctype

        category_choices = dict(Content.Category.choices)
        if category:
            if category not in category_choices:
                category = Content.Category.GENERAL
            attrs["category"] = category
        else:
            attrs["category"] = Content.Category.GENERAL

        content_text = (attrs.get("description") or "").strip()

        if ctype == Content.ContentType.TEXT and not content_text:
            raise serializers.ValidationError({"content": _("Text content cannot be empty.")})
        if ctype == Content.ContentType.IMAGE and not attrs.get("file"):
            raise serializers.ValidationError({"file": _("Image file is required.")})
        if ctype == Content.ContentType.VIDEO and not (attrs.get("file") or attrs.get("url")):
            raise serializers.ValidationError({"file": _("Video requires a file or a URL.")})
        if ctype == Content.ContentType.CASE and not content_text:
            raise serializers.ValidationError({"content": _("Case description is required.")})

        return attrs


class ContentUpdateSerializer(serializers.ModelSerializer):
    content = serializers.CharField(required=False, allow_blank=True)
    content_type = serializers.CharField(required=False)
    category = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Content
        fields = [
            "title",
            "content",
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
        content_value = attrs.pop("content", None)
        if content_value is not None:
            attrs["description"] = content_value

        if "content_type" in attrs:
            ctype = (attrs.get("content_type") or "").strip().lower()
            ctype_choices = dict(Content.ContentType.choices)
            if ctype not in ctype_choices:
                raise serializers.ValidationError({"content_type": _("Invalid content type.")})
            attrs["content_type"] = ctype

        if "category" in attrs:
            category = (attrs.get("category") or "").strip().lower()
            category_choices = dict(Content.Category.choices)
            if not category:
                category = Content.Category.GENERAL
            elif category not in category_choices:
                category = Content.Category.GENERAL
            attrs["category"] = category

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


class CommunityApprovalLogSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    post_id = serializers.UUIDField(source="post.id")
    author_id = serializers.UUIDField(source="author.id", allow_null=True)
    author_name = serializers.SerializerMethodField()
    approving_supervisor_id = serializers.UUIDField(source="approving_supervisor.id", allow_null=True)
    approving_supervisor_name = serializers.SerializerMethodField()
    decision = serializers.CharField()
    reason = serializers.CharField(allow_null=True)
    university_id = serializers.UUIDField(source="university.id", allow_null=True)
    created_at = serializers.DateTimeField()

    def get_author_name(self, obj):
        if not obj.author:
            return None
        return obj.author.get_full_name() or obj.author.username

    def get_approving_supervisor_name(self, obj):
        if not obj.approving_supervisor:
            return None
        return obj.approving_supervisor.get_full_name() or obj.approving_supervisor.username


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

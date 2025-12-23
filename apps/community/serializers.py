from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Content, ContentLike, ContentComment
from apps.accounts.serializers import UserSerializer
from apps.universities.serializers import UniversitySerializer
from medismile.utils.auth import resolve_request_user


# ============================================================
# Content Comment (Read)
# ============================================================

class ContentCommentSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for content comments.
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = ContentComment
        fields = [
            "id",
            "user",
            "text",
            "is_approved",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


# ============================================================
# Content Comment (Create)
# ============================================================

class ContentCommentCreateSerializer(serializers.ModelSerializer):
    """
    Create comment on content.

    Rules:
    - Patient: ❌ not allowed
    - Student / Supervisor: ✅
    """

    class Meta:
        model = ContentComment
        fields = [
            "content",
            "text",
            "parent",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = resolve_request_user(request)

        if not user:
            raise serializers.ValidationError(_("Authentication required."))

        if user.role == "patient":
            raise serializers.ValidationError(_("Patients are not allowed to comment."))

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = resolve_request_user(request)
        validated_data["user"] = user
        return super().create(validated_data)


# ============================================================
# Content Like
# ============================================================

class ContentLikeSerializer(serializers.ModelSerializer):
    """
    Serializer for content likes.
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = ContentLike
        fields = [
            "id",
            "user",
            "created_at",
        ]
        read_only_fields = fields


# ============================================================
# Content (Read)
# ============================================================

class ContentSerializer(serializers.ModelSerializer):
    """
    Main read serializer for community content.
    """

    author = UserSerializer(read_only=True)
    university = UniversitySerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)

    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

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
            "author",
            "university",
            "tags",
            "is_public",
            "is_featured",
            "status",
            "approved_by",
            "rejection_reason",
            "approved_at",
            "view_count",
            "created_at",
            "updated_at",
            "likes_count",
            "comments_count",
            "is_liked",
        ]
        read_only_fields = fields

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.filter(is_approved=True).count()

    def get_is_liked(self, obj):
        request = self.context.get("request")
        user = resolve_request_user(request)
        if not user:
            return False
        return obj.likes.filter(user=user).exists()


# ============================================================
# Content (Create)
# ============================================================

class ContentCreateSerializer(serializers.ModelSerializer):
    """
    Create new community content.

    Rules:
    - Student: status = pending
    - Supervisor / Admin / Tech: auto-approved
    """

    class Meta:
        model = Content
        fields = [
            "title",
            "description",
            "content_type",
            "category",
            "file",
            "url",
            "university",
            "tags",
            "is_public",
        ]

    def validate(self, attrs):
        # Either file or URL must exist
        if not attrs.get("file") and not attrs.get("url"):
            raise serializers.ValidationError(
                _("Either file or URL must be provided.")
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = resolve_request_user(request)

        if not user:
            raise serializers.ValidationError(_("Authentication required."))

        validated_data["author"] = user

        # Student content requires approval
        if user.role == "student":
            validated_data["status"] = Content.Status.PENDING
        else:
            validated_data["status"] = Content.Status.APPROVED

        return super().create(validated_data)


# ============================================================
# Content (Update)
# ============================================================

class ContentUpdateSerializer(serializers.ModelSerializer):
    """
    Update content.

    Rules:
    - Author can edit ONLY if content is not approved yet
    - Supervisor / Admin can edit anytime
    """

    class Meta:
        model = Content
        fields = [
            "title",
            "description",
            "content_type",
            "category",
            "file",
            "url",
            "university",
            "tags",
            "is_public",
            "is_featured",
        ]

    def validate(self, attrs):
        instance = self.instance
        request = self.context.get("request")
        user = resolve_request_user(request)

        if not user:
            raise serializers.ValidationError(_("Authentication required."))

        # Author restrictions
        if user == instance.author and instance.status == Content.Status.APPROVED:
            raise serializers.ValidationError(
                _("Approved content cannot be modified by the author.")
            )

        # File / URL rule
        if not attrs.get("file") and not attrs.get("url"):
            raise serializers.ValidationError(
                _("Either file or URL must be provided.")
            )

        return attrs

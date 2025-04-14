from django.contrib import admin
from django.utils.translation import (
    gettext_lazy as _,
)  # For internationalization if needed
from scheduler.models import Season, Level, Team, Game  # Use full path import
from django.db.models import (
    Count,
)  # Import Count for distinct value optimization if needed


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at", "updated_at")
    list_editable = ("is_active",)  # Allows editing is_active directly in the list
    search_fields = ("name",)
    list_filter = ("is_active",)  # Keep filter here for Seasons themselves

    # Ensure save method logic runs when editing via list_editable
    def save_model(self, request, obj, form, change):
        # The overridden save method on the model handles the uniqueness logic
        super().save_model(request, obj, form, change)


# Custom filter for distinct Level names
class LevelNameListFilter(admin.SimpleListFilter):
    title = _("level name")  # Title shown above the filter options
    parameter_name = "level_name"  # URL parameter

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples (value, verbose_name) for the filter options.
        """
        # Get distinct level names ordered alphabetically
        level_names = (
            Level.objects.values_list("name", flat=True).distinct().order_by("name")
        )
        return [(name, name) for name in level_names]

    def queryset(self, request, queryset):
        """
        Filters the queryset based on the selected level name.
        `self.value()` will be the selected level name string.
        """
        if self.value():  # If a level name was selected in the filter
            # Filter the queryset (Teams or Games) by the name of their associated Level
            return queryset.filter(level__name=self.value())
        # Otherwise, return the original queryset (no filter applied)
        return queryset


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("name", "season")
    list_filter = ("season",)
    search_fields = ("name", "season__name")
    ordering = ("-season__is_active", "season__name", "name")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "get_season")
    list_filter = ("level__season", LevelNameListFilter)
    search_fields = ("name", "level__name", "level__season__name")
    ordering = (
        "-level__season__is_active",
        "level__season__name",
        "level__name",
        "name",
    )

    @admin.display(description="Season", ordering="level__season")
    def get_season(self, obj):
        return obj.level.season


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "level",
        "week",
        "date_time",
        "court",
        "get_season",
    )
    list_filter = ("level__season", LevelNameListFilter, "week", "court")
    search_fields = (
        "team1__name",
        "team2__name",
        "referee_team__name",
        "level__name",
        "level__season__name",
        "court",
    )
    ordering = (
        "-level__season__is_active",
        "level__season__name",
        "week",
        "date_time",
        "level__name",
    )
    list_select_related = (
        "level",
        "level__season",
        "team1",
        "team2",
        "referee_team",
    )

    fields = (
        "level",
        "week",
        "team1",
        "team2",
        "referee_team",
        "date_time",
        "court",
        "team1_score",
        "team2_score",
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Season", ordering="level__season")
    def get_season(self, obj):
        return obj.level.season

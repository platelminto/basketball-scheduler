from django.contrib import admin
from django.utils.translation import (
    gettext_lazy as _,
)  # For internationalization if needed
from scheduler.models import (
    Season,
    Level,
    TeamOrganization,
    SeasonTeam,
    Game,
    Week,
    OffWeek,
)
from django.db.models import (
    Count,
)  # Import Count for distinct value optimization if needed


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "is_deleted", "created_at", "updated_at")
    list_editable = ("is_active",)  # Allows editing is_active directly in the list
    search_fields = ("name",)
    list_filter = ("is_active", "is_deleted")  # Show both active and deleted filters
    actions = ["restore_deleted_seasons", "soft_delete_seasons", "hard_delete_seasons"]
    
    # Use all_objects to show both deleted and non-deleted seasons
    def get_queryset(self, request):
        return Season.all_objects.get_queryset()

    # Ensure save method logic runs when editing via list_editable
    def save_model(self, request, obj, form, change):
        # The overridden save method on the model handles the uniqueness logic
        super().save_model(request, obj, form, change)
    
    def has_delete_permission(self, request, obj=None):
        # Disable the default delete action
        return False
    
    @admin.action(description="Restore selected deleted seasons")
    def restore_deleted_seasons(self, request, queryset):
        """Restore soft-deleted seasons by removing DELETED_ prefix and setting is_deleted=False"""
        restored_seasons = 0
        restored_teams = 0
        
        for season in queryset.filter(is_deleted=True):
            if season.name.startswith("DELETED_"):
                original_name = season.name[8:]  # Remove "DELETED_" prefix
                season.name = original_name
                season.is_deleted = False
                season.save()
                restored_seasons += 1
                
                # Restore all deleted teams referenced by this season
                season_teams = SeasonTeam.objects.filter(season=season).select_related('team')
                for season_team in season_teams:
                    team = season_team.team
                    if team.is_deleted and team.name.startswith("DELETED_"):
                        team_original_name = team.name[8:]  # Remove "DELETED_" prefix
                        team.name = team_original_name
                        team.is_deleted = False
                        team.save()
                        restored_teams += 1
        
        messages = []
        if restored_seasons > 0:
            messages.append(f"Successfully restored {restored_seasons} season(s)")
        if restored_teams > 0:
            messages.append(f"and {restored_teams} associated team(s)")
        if not restored_seasons:
            messages.append("No deleted seasons were selected or found")
        
        message_level = "info" if restored_seasons > 0 else "warning"
        self.message_user(request, ". ".join(messages) + ".", level=message_level)
    
    @admin.action(description="Soft delete selected seasons")
    def soft_delete_seasons(self, request, queryset):
        """Soft delete seasons by adding DELETED_ prefix and setting is_deleted=True"""
        deleted_count = 0
        for season in queryset.filter(is_deleted=False):
            original_name = season.name
            season.is_deleted = True
            season.name = f"DELETED_{original_name}"
            season.is_active = False  # Deactivate when deleting
            season.save()
            deleted_count += 1
        
        if deleted_count > 0:
            self.message_user(request, f"Successfully soft-deleted {deleted_count} season(s).")
        else:
            self.message_user(request, "No active seasons were selected.", level="warning")
    
    @admin.action(description="⚠️ PERMANENTLY delete selected seasons")
    def hard_delete_seasons(self, request, queryset):
        """Permanently delete seasons and all related data - USE WITH EXTREME CAUTION"""
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can perform hard deletes.", level="error")
            return
        
        deleted_count = 0
        skipped_count = 0
        season_names = []
        skipped_names = []
        
        for season in queryset:
            # Only allow hard deletion if season is already soft deleted
            if not season.is_deleted:
                skipped_count += 1
                skipped_names.append(season.name)
                continue
            
            season_names.append(season.name)
            # This will cascade delete all related Level, Week, OffWeek, SeasonTeam, Game objects
            season.delete()
            deleted_count += 1
        
        messages = []
        if deleted_count > 0:
            names_str = ", ".join(season_names)
            messages.append(f"⚠️ PERMANENTLY deleted {deleted_count} season(s) and ALL related data: {names_str}")
        if skipped_count > 0:
            skipped_str = ", ".join(skipped_names)
            messages.append(f"Skipped {skipped_count} season(s) that must be soft-deleted first: {skipped_str}")
        if not deleted_count and not skipped_count:
            messages.append("No seasons were deleted")
        
        message_level = "warning" if deleted_count > 0 else "error" if skipped_count > 0 else "info"
        self.message_user(request, ". ".join(messages), level=message_level)


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


# Custom filter for week numbers
class WeekNumberListFilter(admin.SimpleListFilter):
    title = _("week number")  # Title shown above the filter options
    parameter_name = "week_number"  # URL parameter

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples (value, verbose_name) for the filter options.
        """
        # Get distinct week numbers ordered numerically
        week_numbers = (
            Week.objects.values_list("week_number", flat=True)
            .distinct()
            .order_by("week_number")
        )
        return [(str(num), f"Week {num}") for num in week_numbers]

    def queryset(self, request, queryset):
        """
        Filters the queryset based on the selected week number.
        `self.value()` will be the selected week number as a string.
        """
        if self.value():  # If a week number was selected in the filter
            # Convert string back to int and filter the queryset by the week number
            try:
                week_num = int(self.value())
                return queryset.filter(week__week_number=week_num)
            except (ValueError, TypeError):
                return queryset
        # Otherwise, return the original queryset (no filter applied)
        return queryset


# Custom filter for SeasonTeam seasons
class SeasonTeamSeasonFilter(admin.SimpleListFilter):
    title = _("season")
    parameter_name = "season"

    def lookups(self, request, model_admin):
        seasons = Season.objects.all().order_by("-is_active", "name")
        return [(season.id, season.name) for season in seasons]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(season__id=self.value())
        return queryset


# Custom filter for SeasonTeam levels
class SeasonTeamLevelFilter(admin.SimpleListFilter):
    title = _("level")
    parameter_name = "level"

    def lookups(self, request, model_admin):
        levels = Level.objects.select_related("season").order_by("-season__is_active", "season__name", "name")
        return [(level.id, f"{level.name} ({level.season.name})") for level in levels]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(level__id=self.value())
        return queryset


# Custom filter for SeasonTeam teams
class SeasonTeamTeamFilter(admin.SimpleListFilter):
    title = _("team")
    parameter_name = "team"

    def lookups(self, request, model_admin):
        teams = TeamOrganization.objects.filter(is_deleted=False).order_by("name")
        return [(team.id, team.name) for team in teams]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(team__id=self.value())
        return queryset


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("name", "season")
    list_filter = ("season",)
    search_fields = ("name", "season__name")
    ordering = ("-season__is_active", "season__name", "name")


@admin.register(Week)
class WeekAdmin(admin.ModelAdmin):
    list_display = ("week_number", "monday_date", "season")
    list_filter = ("season",)
    search_fields = ("week_number", "season__name")
    ordering = ("-season__is_active", "season__name", "week_number")


@admin.register(OffWeek)
class OffWeekAdmin(admin.ModelAdmin):
    list_display = ("title", "monday_date", "description", "has_basketball", "season")
    list_filter = ("season", "has_basketball")
    search_fields = ("title", "description", "monday_date", "season__name")
    ordering = ("-season__is_active", "season__name", "monday_date")
    list_editable = ("has_basketball",)


@admin.register(TeamOrganization)
class TeamOrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "is_archived", "is_deleted", "created_at")
    list_filter = ("is_archived", "is_deleted")
    search_fields = ("name",)
    ordering = ("name",)
    list_editable = ("is_archived",)
    actions = ["restore_deleted_teams", "soft_delete_teams", "hard_delete_teams"]
    
    # Use all_objects to show both deleted and non-deleted teams
    def get_queryset(self, request):
        return TeamOrganization.all_objects.get_queryset()
    
    def has_delete_permission(self, request, obj=None):
        # Disable the default delete action
        return False
    
    @admin.action(description="Restore selected deleted teams")
    def restore_deleted_teams(self, request, queryset):
        """Restore soft-deleted teams by removing DELETED_ prefix and setting is_deleted=False"""
        restored_count = 0
        for team in queryset.filter(is_deleted=True):
            if team.name.startswith("DELETED_"):
                original_name = team.name[8:]  # Remove "DELETED_" prefix
                team.name = original_name
                team.is_deleted = False
                team.save()
                restored_count += 1
        
        if restored_count > 0:
            self.message_user(request, f"Successfully restored {restored_count} team(s).")
        else:
            self.message_user(request, "No deleted teams were selected or found.", level="warning")
    
    @admin.action(description="Soft delete selected teams")
    def soft_delete_teams(self, request, queryset):
        """Soft delete teams by adding DELETED_ prefix and setting is_deleted=True"""
        deleted_count = 0
        skipped_teams = []
        
        for team in queryset.filter(is_deleted=False):
            # Check if team is in any non-deleted seasons
            active_seasons = team.season_participations.filter(season__is_deleted=False)
            if active_seasons.exists():
                season_names = ", ".join([sp.season.name for sp in active_seasons])
                skipped_teams.append(f"{team.name} (in seasons: {season_names})")
                continue
            
            original_name = team.name
            team.is_deleted = True
            team.name = f"DELETED_{original_name}"
            team.save()
            deleted_count += 1
        
        messages = []
        if deleted_count > 0:
            messages.append(f"Successfully soft-deleted {deleted_count} team(s)")
        if skipped_teams:
            messages.append(f"Skipped {len(skipped_teams)} team(s) still in active seasons: {'; '.join(skipped_teams)}")
        if not deleted_count and not skipped_teams:
            messages.append("No active teams were selected")
        
        message_level = "warning" if skipped_teams and not deleted_count else "info"
        self.message_user(request, ". ".join(messages) + ".", level=message_level)
    
    @admin.action(description="⚠️ PERMANENTLY delete selected teams")
    def hard_delete_teams(self, request, queryset):
        """Permanently delete teams - USE WITH EXTREME CAUTION"""
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can perform hard deletes.", level="error")
            return
        
        deleted_count = 0
        skipped_teams = []
        team_names = []
        
        for team in queryset:
            # Check if team has any season participations (even in deleted seasons)
            if team.season_participations.exists():
                skipped_teams.append(f"{team.name} (has season history)")
                continue
            
            team_names.append(team.name)
            team.delete()
            deleted_count += 1
        
        messages = []
        if deleted_count > 0:
            names_str = ", ".join(team_names)
            messages.append(f"⚠️ PERMANENTLY deleted {deleted_count} team(s): {names_str}")
        if skipped_teams:
            messages.append(f"Skipped {len(skipped_teams)} team(s) with season history: {'; '.join(skipped_teams)}")
        if not deleted_count and not skipped_teams:
            messages.append("No teams were deleted")
        
        message_level = "warning" if deleted_count > 0 else "info"
        self.message_user(request, ". ".join(messages), level=message_level)


@admin.register(SeasonTeam)
class SeasonTeamAdmin(admin.ModelAdmin):
    list_display = ("team", "level", "season")
    list_filter = (SeasonTeamSeasonFilter, SeasonTeamLevelFilter, SeasonTeamTeamFilter)
    search_fields = ("team__name", "level__name", "season__name")
    ordering = ("-season__is_active", "season__name", "level__name", "team__name")
    
    @admin.display(description="Team", ordering="team__name")
    def get_team_name(self, obj):
        return obj.team.name


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
    list_filter = ("level__season", LevelNameListFilter, WeekNumberListFilter, "court")
    search_fields = (
        "season_team1__team__name",
        "season_team2__team__name",
        "referee_season_team__team__name",
        "referee_name",
        "level__name",
        "level__season__name",
        "court",
    )
    ordering = (
        "-level__season__is_active",
        "level__season__name",
        "week",
        "day_of_week",
        "time",
        "level__name",
    )
    list_select_related = (
        "level",
        "level__season",
        "season_team1__team",
        "season_team2__team",
        "referee_season_team__team",
    )

    fields = (
        "level",
        "week",
        "season_team1",
        "season_team2",
        "referee_season_team",
        "referee_name",
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

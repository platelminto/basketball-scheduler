from django import template

register = template.Library()


@register.filter
def lookup(dictionary, key):
    """Allows dictionary lookup using a variable key in templates."""
    return dictionary.get(key)

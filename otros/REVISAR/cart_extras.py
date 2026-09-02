from django import template

register = template.Library()

@register.filter
def get_dynamic_image(obj, key):
    return getattr(obj, f'imagen{key}', None)

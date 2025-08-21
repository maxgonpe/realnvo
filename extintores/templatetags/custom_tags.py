# myapp/templatetags/custom_tags.py
from django import template

register = template.Library()

@register.filter
def getattr_value(obj, attr_name):
    return getattr(obj, attr_name, None)

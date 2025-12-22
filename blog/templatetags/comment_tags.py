from django import template

register = template.Library()


@register.inclusion_tag('blog/comment_thread.html', takes_context=True)
def render_comment(context, comment, depth=0):
    """
    Render a single comment with all its replies recursively

    Args:
        comment: Comment object
        depth: Current nesting depth (0 = root)
    """
    return {
        'comment': comment,
        'depth': depth,
        'post': context.get('post'),
        'request': context.get('request'),
    }